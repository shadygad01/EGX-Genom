"""Memory profiling harness for `EgxCompositePriceCollector` /
`CollectionService` (the EGX price collection path).

Read-only instrumentation: imports and calls the real collector/service
code exactly as `production.pipeline.ProductionPipeline` does, but never
edits either module. No network calls are made -- a `MappingFetcher`
(same pattern `tests/test_egx_composite_price_collector.py` already uses)
serves synthetic, wire-format-correct Yahoo/StockAnalysis payloads sized
by CLI flags, so results are reproducible without depending on live site
availability or payload sizes this sandbox cannot verify. Where a real
Yahoo/StockAnalysis payload size is unverified, this script says so
rather than presenting a guess as measured fact (see
`docs/TRUTH_PRESERVATION_POLICY.md`'s spirit -- this is engineering
diagnostics, not investment data, but the same "never dress up a guess
as a measurement" discipline applies).

Two scenarios:

  single   One realistic collection run (fetch -> parse -> materialize)
           against a configurable universe size and history depth.
           Reports tracemalloc peak, an after-fetch/before-parse
           checkpoint (via a non-invasive wrapper around
           `collector.fetch`, not a source edit), top allocation sites,
           and process RSS. This measures the *in-run* peak -- answers
           "how big is one run's batching footprint."

  growth   The same collector run repeated for N simulated days, reusing
           the *same* `RawDocumentRepository`/`ProvenanceIndexRepository`
           instances across iterations -- exactly what happens in
           production, where `ProductionPipeline._stage_collector_execution`
           reloads these from an ever-growing on-disk JSON file on every
           run (see `storage.repository.JsonFileRepository._load`). Each
           simulated day re-fetches "full history + one more day", the
           same shape a real `range=max` Yahoo request returns daily.
           This measures cross-run accumulation -- answers "does memory
           return to baseline between runs, or does it grow without
           bound."

Usage (from `research/`):

    uv run python scripts/profile_egx_collector_memory.py single \\
        --universe-size 101 --history-days 5500 --sa-days 300

    uv run python scripts/profile_egx_collector_memory.py growth \\
        --universe-size 101 --history-days 500 --days 10

Each invocation prints one JSON object to stdout and exits -- a driver
script or shell loop is expected to fan out multiple invocations as
separate processes for RSS isolation (this is why `single` is one
process per scenario rather than a sweep in-process: `resource`'s
peak-RSS counters are monotonic for the life of the process, so mixing
scenarios in one process would contaminate later readings with earlier
peaks).
"""

from __future__ import annotations

import argparse
import json
import sys
import tracemalloc
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "research" / "src"))

from agx_research.collectors.egx_prices import EgxCompositePriceCollector  # noqa: E402
from agx_research.collectors.provenance_index import ProvenanceIndexRepository  # noqa: E402
from agx_research.collectors.raw import RawDocumentRepository  # noqa: E402
from agx_research.collectors.service import CollectionService  # noqa: E402
from agx_research.sources.catalog import seed_sources  # noqa: E402
from agx_research.sources.health import HealthMonitor  # noqa: E402
from agx_research.sources.reputation import SourceMetricsRepository  # noqa: E402

CAIRO = ZoneInfo("Africa/Cairo")


def price_spec():
    return next(s for s in seed_sources() if s.id == "egx_price_composite")


def real_universe_tickers() -> list[str]:
    """EGX30 + EGX70 tickers as already collected in this repo's own
    universe snapshot (`data/universe/*.csv`) -- real tickers, not
    invented ones, even though the price *history* behind them below is
    synthetic.
    """
    tickers: list[str] = []
    seen = set()
    for name in ("EGX30.csv", "EGX70.csv"):
        path = REPO_ROOT / "research" / "data" / "universe" / name
        lines = path.read_text(encoding="utf-8").splitlines()[1:]
        for line in lines:
            ticker = line.split(",", 1)[0].strip()
            if ticker and ticker not in seen:
                seen.add(ticker)
                tickers.append(ticker)
    return tickers


def _deterministic_walk(ticker: str, salt: str, num_days: int, base: float) -> list[float]:
    price = base
    values = []
    for i in range(num_days):
        step = (hash((ticker, salt, i)) % 21 - 10) / 2000  # +/-0.5% deterministic daily drift
        price *= 1 + step
        values.append(round(price, 2))
    return values


def build_yahoo_payload(ticker: str, num_days: int, end: date) -> str:
    """A `range=max` Yahoo v8 chart payload shaped like the real one this
    collector parses (`egx_prices.py::_parse_yahoo`): `meta` block,
    parallel OHLCV arrays, an `adjclose` leg (present on the real
    endpoint; unused by the parser but still part of what
    `RawDocument.content_text` holds in memory), and a sparse dividend
    calendar. Day count is the caller's stress-test parameter -- this
    script does not claim to know real EGX tickers' actual Yahoo history
    depth (unverified without a live fetch); see the report this script
    feeds for that caveat.
    """
    dates = [end - timedelta(days=num_days - 1 - i) for i in range(num_days)]
    timestamps = [int(datetime(d.year, d.month, d.day, 12, tzinfo=UTC).timestamp()) for d in dates]
    base = 20.0 + (hash(ticker) % 300)
    closes = _deterministic_walk(ticker, "close", num_days, base)
    opens = [round(c * 0.995, 2) for c in closes]
    highs = [round(c * 1.012, 2) for c in closes]
    lows = [round(c * 0.988, 2) for c in closes]
    volumes = [50_000 + (hash((ticker, i, "vol")) % 950_000) for i in range(num_days)]
    dividends = {
        str(timestamps[i]): {"amount": 1.0, "date": timestamps[i]}
        for i in range(0, num_days, 250)
    }
    payload = {
        "chart": {
            "result": [
                {
                    "meta": {
                        "currency": "EGP",
                        "symbol": f"{ticker}.CA",
                        "exchangeName": "CAI",
                        "instrumentType": "EQUITY",
                        "firstTradeDate": timestamps[0],
                        "regularMarketTime": timestamps[-1],
                        "gmtoffset": 7200,
                        "timezone": "EET",
                        "exchangeTimezoneName": "Africa/Cairo",
                        "regularMarketPrice": closes[-1],
                        "chartPreviousClose": closes[-2] if num_days > 1 else closes[-1],
                        "priceHint": 2,
                        "dataGranularity": "1d",
                        "range": "max",
                        "validRanges": [
                            "1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max",
                        ],
                    },
                    "timestamp": timestamps,
                    "indicators": {
                        "quote": [
                            {"open": opens, "high": highs, "low": lows, "close": closes, "volume": volumes}
                        ],
                        "adjclose": [{"adjclose": closes}],
                    },
                    "events": {"dividends": dividends, "splits": {}},
                }
            ],
            "error": None,
        }
    }
    return json.dumps(payload)


def build_stockanalysis_payload(ticker: str, num_days: int, end: date, boilerplate_kb: int) -> str:
    """The embedded-JS-array shape `egx_prices.py::_SA_ROW` regex-parses,
    padded with `boilerplate_kb` of surrounding page markup. Real
    stockanalysis.com history pages carry substantial nav/CSS/script
    chrome around the data array; this script does not know that real
    figure (unmeasured without a live fetch) so it defaults to 0 and
    reports the consequence explicitly rather than presenting a guess --
    pass `--sa-boilerplate-kb` to stress-test a specific assumption.
    """
    price = 20.0 + (hash(ticker) % 300)
    rows = []
    for i in range(num_days):
        d = end - timedelta(days=num_days - 1 - i)
        step = (hash((ticker, "sa", i)) % 21 - 10) / 2000
        price *= 1 + step
        vol = 50_000 + (hash((ticker, i, "savol")) % 950_000)
        rows.append(
            f'{{a:{price * 0.999:.2f},c:{price:.2f},h:{price * 1.012:.2f},'
            f'l:{price * 0.988:.2f},o:{price * 0.995:.2f},t:"{d.isoformat()}",'
            f"v:{vol},ch:0.1}}"
        )
    data_block = f"<script>data:[{','.join(rows)}],created_at:'now'</script>"
    if boilerplate_kb <= 0:
        return data_block
    filler = ("<!-- page-chrome-placeholder -->" * (boilerplate_kb * 32 + 1))
    return filler[: boilerplate_kb * 1024] + data_block


class MappingFetcher:
    def __init__(self, content: dict[str, str]):
        self.content = content
        self.calls: list[str] = []

    def fetch_text(self, url: str, spec) -> str:
        self.calls.append(url)
        return self.content[url]


def _current_rss_kb() -> int | None:
    try:
        with open("/proc/self/status", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1])
    except OSError:
        return None
    return None


def build_universe(size: int) -> list[str]:
    tickers = real_universe_tickers()
    if size > len(tickers):
        raise ValueError(f"universe-size {size} exceeds real universe of {len(tickers)} tickers")
    return tickers[:size]


def build_content_for_day(
    symbols: list[str], *, history_days: int, sa_days: int, sa_boilerplate_kb: int, end: date
) -> dict[str, str]:
    content: dict[str, str] = {}
    for ticker in symbols:
        content[EgxCompositePriceCollector.yahoo_url(ticker)] = build_yahoo_payload(
            ticker, history_days, end
        )
        stock_url = EgxCompositePriceCollector.stockanalysis_urls(ticker)[0]
        content[stock_url] = build_stockanalysis_payload(ticker, sa_days, end, sa_boilerplate_kb)
    return content


def top_allocations(snapshot_before, snapshot_after, limit: int) -> list[dict]:
    diff = snapshot_after.compare_to(snapshot_before, "lineno")
    out = []
    for stat in diff[:limit]:
        frame = stat.traceback[0]
        out.append(
            {
                "file": frame.filename.replace(str(REPO_ROOT) + "/", ""),
                "line": frame.lineno,
                "size_delta_kb": round(stat.size_diff / 1024, 1),
                "size_total_kb": round(stat.size / 1024, 1),
                "count_delta": stat.count_diff,
                "count_total": stat.count,
            }
        )
    return out


def run_single(args: argparse.Namespace) -> dict:
    symbols = build_universe(args.universe_size)
    end = date(2026, 8, 6)
    content = build_content_for_day(
        symbols,
        history_days=args.history_days,
        sa_days=args.sa_days,
        sa_boilerplate_kb=args.sa_boilerplate_kb,
        end=end,
    )
    fetcher = MappingFetcher(content)
    collector = EgxCompositePriceCollector(
        price_spec(), symbols, fetcher=fetcher, now=lambda: datetime(2026, 8, 6, 11, tzinfo=CAIRO)
    )

    tracemalloc.start(10)
    snap_start = tracemalloc.take_snapshot()

    checkpoint: dict = {}
    real_fetch = collector.fetch

    def instrumented_fetch():
        docs = real_fetch()
        current, _peak_so_far = tracemalloc.get_traced_memory()
        checkpoint["after_fetch_traced_current_kb"] = round(current / 1024, 1)
        checkpoint["after_fetch_rss_kb"] = _current_rss_kb()
        checkpoint["documents_fetched"] = len(docs)
        checkpoint["raw_content_text_bytes"] = sum(len(d.content_text.encode()) for d in docs)
        checkpoint["snapshot_after_fetch"] = tracemalloc.take_snapshot()
        return docs

    collector.fetch = instrumented_fetch  # instrumentation wrapper, not a source edit

    with __import__("tempfile").TemporaryDirectory() as tmp:
        data_dir = Path(tmp)
        service = CollectionService(
            data_dir,
            raw_documents=RawDocumentRepository(),
            provenance_index=ProvenanceIndexRepository(),
            metrics=SourceMetricsRepository(),
            health_monitor=HealthMonitor(),
            min_confidence=0.5,
        )
        result = service.run(collector, expected_records=100)
        raw_doc_revisions = sum(len(v) for v in service.raw_documents._revisions.values())
        raw_doc_bytes = sum(
            len(rev.content_text.encode())
            for revs in service.raw_documents._revisions.values()
            for rev in revs
        )
        provenance_records = sum(len(v) for v in service.provenance_index._revisions.values())

    current, peak = tracemalloc.get_traced_memory()
    snap_end = tracemalloc.take_snapshot()
    allocations = top_allocations(snap_start, snap_end, args.top)
    tracemalloc.stop()

    return {
        "scenario": "single",
        "universe_size": len(symbols),
        "history_days": args.history_days,
        "sa_days": args.sa_days,
        "sa_boilerplate_kb": args.sa_boilerplate_kb,
        "checkpoint_after_fetch": {
            k: v for k, v in checkpoint.items() if k != "snapshot_after_fetch"
        },
        "final": {
            "documents_fetched": result.documents_fetched,
            "batches_materialized": result.batches_materialized,
            "batches_withheld": result.batches_withheld,
            "price_bars_written": result.price_bars_written,
            "raw_document_revisions_in_memory": raw_doc_revisions,
            "raw_document_content_text_bytes": raw_doc_bytes,
            "provenance_records_in_memory": provenance_records,
            "tracemalloc_current_kb": round(current / 1024, 1),
            "tracemalloc_peak_kb": round(peak / 1024, 1),
            "rss_kb": _current_rss_kb(),
        },
        "top_allocations_by_site": allocations,
    }


def run_growth(args: argparse.Namespace) -> dict:
    symbols = build_universe(args.universe_size)
    end = date(2026, 8, 6)

    with __import__("tempfile").TemporaryDirectory() as tmp:
        data_dir = Path(tmp)
        raw_documents = RawDocumentRepository()
        provenance_index = ProvenanceIndexRepository()
        service = CollectionService(
            data_dir,
            raw_documents=raw_documents,
            provenance_index=provenance_index,
            metrics=SourceMetricsRepository(),
            health_monitor=HealthMonitor(),
            min_confidence=0.5,
        )

        days: list[dict] = []
        for day_offset in range(args.days):
            day_end = end + timedelta(days=day_offset)
            # A real `range=max` Yahoo fetch returns the full series again,
            # one trading day longer -- not just the new day's bar. This
            # mirrors that shape exactly rather than only appending one row.
            content = build_content_for_day(
                symbols,
                history_days=args.history_days + day_offset,
                sa_days=args.sa_days,
                sa_boilerplate_kb=args.sa_boilerplate_kb,
                end=day_end,
            )
            fetcher = MappingFetcher(content)
            collector = EgxCompositePriceCollector(
                price_spec(),
                symbols,
                fetcher=fetcher,
                now=lambda de=day_end: datetime(de.year, de.month, de.day, 11, tzinfo=CAIRO),
            )
            service.run(collector, expected_records=100)

            raw_doc_revisions = sum(len(v) for v in raw_documents._revisions.values())
            raw_doc_bytes = sum(
                len(rev.content_text.encode())
                for revs in raw_documents._revisions.values()
                for rev in revs
            )
            provenance_records = sum(len(v) for v in provenance_index._revisions.values())
            days.append(
                {
                    "day": day_offset,
                    "raw_document_revisions_in_memory": raw_doc_revisions,
                    "raw_document_content_text_bytes": raw_doc_bytes,
                    "provenance_records_in_memory": provenance_records,
                    "rss_kb": _current_rss_kb(),
                }
            )

    return {
        "scenario": "growth",
        "universe_size": len(symbols),
        "history_days_start": args.history_days,
        "simulated_days": args.days,
        "days": days,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="scenario", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--universe-size", type=int, default=101)
    common.add_argument("--history-days", type=int, default=5500)
    common.add_argument("--sa-days", type=int, default=300)
    common.add_argument("--sa-boilerplate-kb", type=int, default=0)

    single = sub.add_parser("single", parents=[common])
    single.add_argument("--top", type=int, default=15)

    growth = sub.add_parser("growth", parents=[common])
    growth.add_argument("--days", type=int, default=10)

    args = parser.parse_args()
    if args.scenario == "single":
        result = run_single(args)
    else:
        result = run_growth(args)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
