"""Ingest the reviewed community price seed into the runtime data directory.

Mirrors `universe.bootstrap.materialize_universe_seed()`'s exact posture:
the checked-in seed under `research/data/community_prices_seed/normalized/`
is an input, not a second live provider — it is idempotently merged into
`<data_dir>/{prices,sectors}` and `<data_dir>/corporate_events.csv` before
use, so `LocalCsvDataProvider`/`CollectedSectorProvider` remain the only
things any pipeline stage actually reads. See `research/scripts/
ingest_egx_community_dataset.py` for how the seed itself was produced from
its real, third-party, MIT-licensed source, and `docs/
EGX30_DATA_SOURCE_QUALIFICATION.md` for the full qualification evidence.

This is explicitly *not* presented as an official/licensed EGX vendor feed
— every consumer of this data (CLI output, reports) must carry that
disclosure forward, per `docs/PATTERN_DISCOVERY_DATA_AUDIT.md`'s existing
"never treat placeholder/third-party data as vendor-grade truth" posture.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

REQUIRED_PRICE_COLUMNS = ("date", "open", "high", "low", "close", "volume")


def _read_price_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or list(reader.fieldnames) != list(REQUIRED_PRICE_COLUMNS):
            raise ValueError(f"{path}: expected columns {REQUIRED_PRICE_COLUMNS}, got {reader.fieldnames}")
        return list(reader)


def materialize_community_price_seed(seed_dir: Path | str, data_dir: Path | str) -> dict[str, int]:
    """Idempotently merge the reviewed community price seed into `data_dir`.

    Returns a small summary dict (tickers/events/sectors written) for
    logging — mirrors `materialize_universe_seed()`'s "return count
    written" shape.
    """
    source = Path(seed_dir) / "normalized"
    if not source.is_dir():
        raise FileNotFoundError(f"Community price seed directory does not exist: {source}")

    prices_target = Path(data_dir) / "prices"
    prices_target.mkdir(parents=True, exist_ok=True)
    tickers_written = 0
    for seed_path in sorted((source / "prices").glob("*.csv")):
        rows = _read_price_rows(seed_path)
        target_path = prices_target / seed_path.name
        existing = {r["date"]: r for r in _read_price_rows(target_path)} if target_path.exists() else {}
        for row in rows:
            existing[row["date"]] = row
        with target_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=REQUIRED_PRICE_COLUMNS)
            writer.writeheader()
            for trade_date in sorted(existing):
                writer.writerow(existing[trade_date])
        tickers_written += 1

    events_seed = source / "corporate_events.csv"
    events_written = 0
    if events_seed.exists():
        with events_seed.open(newline="", encoding="utf-8") as handle:
            seed_events = list(csv.DictReader(handle))
        events_target = Path(data_dir) / "corporate_events.csv"
        existing_events: dict[tuple[str, str, str], dict[str, str]] = {}
        if events_target.exists():
            with events_target.open(newline="", encoding="utf-8") as handle:
                for row in csv.DictReader(handle):
                    key = (row["ticker"], row["date"], row["event_type"])
                    existing_events[key] = row
        for row in seed_events:
            key = (row["ticker"], row["date"], row["event_type"])
            existing_events[key] = row
        with events_target.open("w", newline="", encoding="utf-8") as handle:
            fieldnames = ["ticker", "date", "event_type", "description", "details_json"]
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for key in sorted(existing_events):
                writer.writerow(existing_events[key])
        events_written = len(seed_events)

    sectors_seed = source / "sector_membership.csv"
    sectors_written = 0
    if sectors_seed.exists():
        with sectors_seed.open(newline="", encoding="utf-8") as handle:
            seed_sectors = list(csv.DictReader(handle))
        sectors_target_dir = Path(data_dir) / "sectors"
        sectors_target_dir.mkdir(parents=True, exist_ok=True)
        sectors_target = sectors_target_dir / "sector_membership.csv"
        existing_sectors: dict[str, str] = {}
        if sectors_target.exists():
            with sectors_target.open(newline="", encoding="utf-8") as handle:
                for row in csv.DictReader(handle):
                    existing_sectors[row["ticker"]] = row["sector"]
        for row in seed_sectors:
            existing_sectors[row["ticker"]] = row["sector"]
        with sectors_target.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["ticker", "sector"])
            for ticker in sorted(existing_sectors):
                writer.writerow([ticker, existing_sectors[ticker]])
        sectors_written = len(seed_sectors)

    manifest_path = Path(seed_dir) / "PROVENANCE.json"
    if manifest_path.exists():
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        (Path(data_dir) / "community_price_seed_provenance.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    return {
        "tickers_written": tickers_written,
        "corporate_events_written": events_written,
        "sectors_written": sectors_written,
    }


__all__ = ["materialize_community_price_seed"]
