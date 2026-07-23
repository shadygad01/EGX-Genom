"""Shared header-text column matching for collectors that parse a
long-format CSV export whose column order isn't known in advance
(`IndexConstituentCollector`, `FinancialStatementCollector`) -- a real,
generic heuristic (find the column whose header contains one of a
declared set of hint substrings), not a guess at any specific source's
wire format. Extracted after the same helper turned up verbatim in both
collectors.
"""

from __future__ import annotations


def find_column(header: list[str], hints: tuple[str, ...]) -> int | None:
    for position, column in enumerate(header):
        normalized = column.strip().lower()
        if any(hint in normalized for hint in hints):
            return position
    return None
