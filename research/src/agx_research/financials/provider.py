"""FinancialStatementProvider: source of reported financial-statement line
items, mirroring `universe.UniverseProvider`'s "small, dedicated interface"
shape rather than growing `data.provider.DataProvider`'s existing abstract
method set -- `DataProvider` is a completed, tested interface with every
existing implementation (`MockDataProvider`, any future real vendor)
depending on its exact method set; adding an unrelated abstract method to
it would force every implementation to change, which is a redesign, not an
extension.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from agx_research.financials.schema import FinancialStatementLineItem


class FinancialStatementProvider(ABC):
    @abstractmethod
    def get_line_items(
        self, ticker: str, start: date, end: date, *, statement_type: str | None = None
    ) -> list[FinancialStatementLineItem]:
        """Return line items for `ticker` whose `period_end_date` falls in
        [start, end], optionally filtered to one `statement_type`. Never
        fabricated: no items collected means an empty list, not a guess.
        """
