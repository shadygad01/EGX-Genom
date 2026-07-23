"""The AGX command-line entry point: `python -m agx_research.cli ...`.

Transport/operations only — every research decision lives in the modules
this invokes. Uses the mock data provider and placeholder universe until a
real vendor is licensed (a business decision); the `--data-dir` stores
persist every repository so runs accumulate and are replayable.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from agx_research.agents.corporate_events import CorporateEventsAgent
from agx_research.agents.liquidity import LiquidityAgent
from agx_research.agents.macro import MacroAgent
from agx_research.agents.market_structure import MarketStructureAgent
from agx_research.agents.technical_structure import TechnicalStructureAgent
from agx_research.data.mock_provider import MockDataProvider
from agx_research.genome.service import AlphaGenome
from agx_research.hypotheses.repository import HypothesisRepository
from agx_research.infrastructure.backup import create_backup, restore_backup, verify_backup
from agx_research.knowledge.store import KnowledgeStore
from agx_research.market_memory.memory import MarketMemory
from agx_research.orchestration.pipeline import DailyResearchPipeline
from agx_research.papers.repository import PaperRepository
from agx_research.runtime.engine import RunRecordRepository, RuntimeEngine
from agx_research.universe.sector import StaticSectorProvider
from agx_research.universe.static import EGX30_UNIVERSE_PLACEHOLDER, StaticUniverseProvider

_DEFAULT_MOCK_DATA = Path(__file__).resolve().parents[2] / "data" / "mock"


def build_engine(data_dir: Path, mock_data: Path) -> RuntimeEngine:
    tickers = sorted(EGX30_UNIVERSE_PLACEHOLDER)
    memory = MarketMemory(
        MockDataProvider(mock_data),
        StaticUniverseProvider(),
        StaticSectorProvider(),
        tickers=tickers,
        macro_series_ids=["BRENT_USD", "EGP_USD"],
        lookback_days=30,
    )
    agents = [
        MarketStructureAgent(
            ticker_pairs=[(a, b) for i, a in enumerate(tickers) for b in tickers[i + 1 :]]
        ),
        MacroAgent(),
        CorporateEventsAgent(),
        LiquidityAgent(),
        TechnicalStructureAgent(),
    ]
    pipeline = DailyResearchPipeline(
        memory,
        agents,
        hypothesis_repository=HypothesisRepository(data_dir / "hypotheses.json"),
        knowledge_store=KnowledgeStore(data_dir / "knowledge.json"),
        genome=AlphaGenome(data_dir / "genes.json"),
        paper_repository=PaperRepository(data_dir / "papers.json"),
    )
    return RuntimeEngine(pipeline, run_records=RunRecordRepository(data_dir / "runs.json"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="agx", description="AGX research platform runtime")
    parser.add_argument("--data-dir", type=Path, default=Path("agx_data"))
    parser.add_argument("--mock-data", type=Path, default=_DEFAULT_MOCK_DATA)
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="Run the daily research pipeline")
    run_parser.add_argument("--date", required=True, help="ISO date, e.g. 2026-06-14")
    run_parser.add_argument("--end-date", help="Optional ISO end date for a range")

    sub.add_parser("status", help="Show run ledger and knowledge summary")

    backup_parser = sub.add_parser("backup", help="Create an integrity-checked backup")
    backup_parser.add_argument("--output", type=Path, required=True)

    verify_parser = sub.add_parser("verify-backup", help="Verify a backup's integrity")
    verify_parser.add_argument("--input", type=Path, required=True)

    restore_parser = sub.add_parser("restore", help="Restore a verified backup")
    restore_parser.add_argument("--input", type=Path, required=True)
    restore_parser.add_argument("--target", type=Path, required=True)

    args = parser.parse_args(argv)

    if args.command == "run":
        args.data_dir.mkdir(parents=True, exist_ok=True)
        engine = build_engine(args.data_dir, args.mock_data)
        start = date.fromisoformat(args.date)
        end = date.fromisoformat(args.end_date) if args.end_date else start
        records = engine.run_range(start, end)
        for record in records:
            print(
                f"{record.run_date} {record.status.value}: "
                f"{record.hypotheses} hypotheses, {record.promoted} promoted"
                + (f" ({record.error})" if record.error else "")
            )
        return 0

    if args.command == "status":
        runs = RunRecordRepository(args.data_dir / "runs.json").all_latest()
        knowledge = KnowledgeStore(args.data_dir / "knowledge.json").all_latest()
        print(json.dumps(
            {
                "runs": len(runs),
                "succeeded": sum(1 for r in runs if r.status.value == "succeeded"),
                "failed": sum(1 for r in runs if r.status.value == "failed"),
                "knowledge_objects": len(knowledge),
                "by_status": {
                    status: sum(1 for k in knowledge if k.status.value == status)
                    for status in {k.status.value for k in knowledge}
                },
            },
            indent=2,
        ))
        return 0

    if args.command == "backup":
        manifest = create_backup(args.data_dir, args.output)
        print(f"Backed up {len(manifest['files'])} store(s) to {args.output}")
        return 0

    if args.command == "verify-backup":
        manifest = verify_backup(args.input)
        print(f"OK: {len(manifest['files'])} file(s) verified")
        return 0

    if args.command == "restore":
        manifest = restore_backup(args.input, args.target)
        print(f"Restored {len(manifest['files'])} store(s) to {args.target}")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
