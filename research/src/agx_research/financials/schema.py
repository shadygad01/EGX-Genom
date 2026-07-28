"""FinancialStatementLineItem: one reported line-item value from a company's
financial statements -- the raw material `agents.financial_performance.
FinancialPerformanceAgent` has been an honest `NotImplementedError` stub
for, waiting explicitly on "a financial statement data source" (see
`docs/PHASE_STATUS.md` System 08). This module is that data source's
canonical shape; the agent's actual fundamental-factor logic is a separate,
later step (Scientist Framework work, not Data Platform work).

`line_item` uses `STANDARD_LINE_ITEMS` where possible -- well-established
IFRS/GAAP terminology (revenue, net_income, total_assets, ...), the same
"reuse a well-known, universal vocabulary" precedent as
`events.adapters._CORPORATE_SUBTYPES` -- but isn't hard-validated against
it: an unrecognized `line_item` string is preserved verbatim (like
`CorporateEvent.event_type`), never coerced or dropped, so a source
reporting a less common line item isn't silently lost.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel

# A deliberately small, universal starting vocabulary -- the decision-
# relevant items for relating fundamentals to forward returns (margins,
# growth, leverage, profitability). Not exhaustive by design: a real filing
# reports many more line items, and inventing a complete IFRS taxonomy
# ahead of any real filing to map against would be speculative engineering,
# not data acquisition.
STANDARD_LINE_ITEMS: tuple[str, ...] = (
    "revenue",
    "cost_of_revenue",
    "gross_profit",
    "operating_income",
    "net_income",
    "eps_basic",
    "eps_diluted",
    "total_assets",
    "total_liabilities",
    "total_equity",
    "cash_and_equivalents",
    "total_debt",
    "operating_cash_flow",
    "free_cash_flow",
    "ebitda",
    "revenue_growth_yoy",
    "ebitda_growth_yoy",
    "net_margin",
    "net_debt_to_ebitda",
)


class FinancialStatementLineItem(BaseModel):
    ticker: str
    period_end_date: date
    period_type: str  # "ANNUAL" | "QUARTERLY"
    statement_type: str  # "INCOME_STATEMENT" | "BALANCE_SHEET" | "CASH_FLOW"
    line_item: str  # prefer STANDARD_LINE_ITEMS; any string is preserved as-is
    value: float
    currency: str = "EGP"
