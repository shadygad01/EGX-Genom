from __future__ import annotations

import csv
import json
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter

ROOT = Path(__file__).resolve().parent / "raw"


def parse_date(value: str):
    value = (value or "").strip()
    if not value:
        return None
    candidates = [value, value.split(" ")[0]]
    for candidate in candidates:
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%m/%d/%Y"):
            try:
                return datetime.strptime(candidate, fmt).date().isoformat()
            except ValueError:
                pass
    return None


def inspect_csv(path: Path) -> dict:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        rows = list(reader)
    date_field = next((f for f in fields if f.lower() in {"date", "timestamp", "datetime"}), None)
    parsed_dates = []
    raw_dates = []
    if date_field:
        for row in rows:
            value = (row.get(date_field) or "").strip()
            if value:
                raw_dates.append(value)
                parsed = parse_date(value)
                if parsed:
                    parsed_dates.append(parsed)
    return {
        "file": str(path.relative_to(ROOT)),
        "rows": len(rows),
        "fields": fields,
        "date_field": date_field,
        "min_date": min(parsed_dates) if parsed_dates else None,
        "max_date": max(parsed_dates) if parsed_dates else None,
        "unparsed_date_count": len(raw_dates) - len(parsed_dates),
        "duplicate_date_count": len(parsed_dates) - len(set(parsed_dates)),
    }


def dataset_summary(name: str, directory: Path) -> dict:
    files = sorted(directory.rglob("*.csv"))
    inspected = [inspect_csv(path) for path in files]
    security_files = []
    stock_files = []
    for item in inspected:
        fields = set(item["fields"])
        if {"Open", "High", "Low"}.issubset(fields) or {"Price", "Open", "High", "Low"}.issubset(fields):
            stock_files.append(item)
        else:
            security_files.append(item)
    stock_dates = [item["min_date"] for item in stock_files if item["min_date"]] + [item["max_date"] for item in stock_files if item["max_date"]]
    return {
        "name": name,
        "csv_count": len(files),
        "stock_file_count": len(stock_files),
        "metadata_file_count": len(security_files),
        "total_rows": sum(item["rows"] for item in stock_files),
        "date_min": min(stock_dates) if stock_dates else None,
        "date_max": max(stock_dates) if stock_dates else None,
        "unparsed_date_cells": sum(item["unparsed_date_count"] for item in stock_files),
        "duplicate_dates": sum(item["duplicate_date_count"] for item in stock_files),
        "files": inspected,
    }


result = {
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "sources": [
        dataset_summary("shaban", ROOT / "shaban"),
        dataset_summary("al_refaey", ROOT / "al_refaey"),
    ],
}

out = Path(__file__).resolve().parent / "source_inventory.json"
out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({
    "generated": str(out),
    "sources": [
        {"name": source["name"], "csv_count": source["csv_count"], "total_rows": source["total_rows"]}
        for source in result["sources"]
    ],
}, ensure_ascii=False, indent=2))
