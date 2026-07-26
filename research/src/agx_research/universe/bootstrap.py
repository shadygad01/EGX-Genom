"""Ingest reviewed universe snapshots into the runtime universe directory.

Checked-in snapshots are inputs, not a second provider. They are merged into
``<data_dir>/universe`` before use; ``CollectedUniverseProvider`` remains the
only membership source read by the pipeline.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

_CORE_FIELDS = ("ticker", "company_name", "as_of_date")
_OPTIONAL_FIELDS = ("isin", "reuters_code", "weight_percent", "source_url")


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing CSV header")
        missing = [field for field in _CORE_FIELDS if field not in reader.fieldnames]
        if missing:
            raise ValueError(f"{path}: missing required column(s): {', '.join(missing)}")
        return list(reader)


def materialize_universe_seed(seed_dir: Path | str, data_dir: Path | str) -> int:
    """Idempotently merge reviewed seed rows into the provider's data root."""

    source = Path(seed_dir)
    if not source.is_dir():
        raise FileNotFoundError(f"Universe seed directory does not exist: {source}")

    target = Path(data_dir) / "universe"
    target.mkdir(parents=True, exist_ok=True)
    written = 0

    for seed_path in sorted(source.glob("*.csv")):
        target_path = target / seed_path.name
        existing_rows = _read_rows(target_path) if target_path.exists() else []
        seed_rows = _read_rows(seed_path)
        combined = {
            (row["ticker"].strip().upper(), row["as_of_date"].strip()): row
            for row in existing_rows
        }
        for row in seed_rows:
            normalized = {key: (value or "").strip() for key, value in row.items()}
            normalized["ticker"] = normalized["ticker"].upper()
            combined[(normalized["ticker"], normalized["as_of_date"])] = normalized

        discovered = {
            field for row in combined.values() for field in row if field not in _CORE_FIELDS
        }
        fields = [*_CORE_FIELDS, *[f for f in _OPTIONAL_FIELDS if f in discovered]]
        fields.extend(sorted(discovered - set(_OPTIONAL_FIELDS)))
        with target_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            for key in sorted(combined, key=lambda item: (item[1], item[0])):
                writer.writerow(combined[key])
        written += len(seed_rows)

    manifest = source / "source_manifest.json"
    if manifest.exists():
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        (target / "source_manifest.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return written
