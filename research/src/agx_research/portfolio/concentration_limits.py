"""Portfolio concentration-limit constants shared by
`investment_proof.portfolio_validation` (post-hoc validation of an
already-built portfolio) and `decision_service.concentration` (the
pre-emptive hard override applied while `DecisionService.decide_portfolio()`
computes target weights, AD-66).

Pulled out to this dependency-free leaf module specifically so neither of
those two packages needs to import the other just to share one number --
`portfolio_validation` importing `decision_service.service.PositionAwareDecision`
while `decision_service.concentration` imported `portfolio_validation`
back would be a circular import, and duplicating the constant in both
places would risk the exact kind of silent doctrine drift
`docs/PORTFOLIO_STANDARDS.md` forbids.
"""

from __future__ import annotations

#: Declared, uncalibrated -- see docs/TECHNICAL_DEBT.md. No real
#: multi-year EGX portfolio history exists yet to test whether these are
#: the thresholds that actually separate healthy diversification from a
#: real concentration risk.
HERFINDAHL_CONCENTRATED_THRESHOLD = 0.25
MAX_SECTOR_CONCENTRATION = 0.40

__all__ = ["HERFINDAHL_CONCENTRATED_THRESHOLD", "MAX_SECTOR_CONCENTRATION"]
