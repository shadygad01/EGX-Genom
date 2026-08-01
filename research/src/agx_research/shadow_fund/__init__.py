"""Shadow Fund: the canonical, persistent state of a continuously managed
virtual institutional portfolio that owns the evolving result of following
this platform's own autonomous INVESTMENT-horizon recommendations, day
over day, since inception. See `models.py`'s module docstring for how this
relates to `meta.decision_ledger.DecisionLedger`, `investment_cases`, and
`investment_proof` -- each stays the canonical source of its own thing;
the Shadow Fund does not duplicate or replace any of them."""

from agx_research.shadow_fund.engine import INCEPTION_NAV, REBALANCE_THRESHOLD_PCT, advance
from agx_research.shadow_fund.models import ShadowFundSnapshot
from agx_research.shadow_fund.repository import ShadowFundLedger

__all__ = [
    "INCEPTION_NAV",
    "REBALANCE_THRESHOLD_PCT",
    "ShadowFundLedger",
    "ShadowFundSnapshot",
    "advance",
]
