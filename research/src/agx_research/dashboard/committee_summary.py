"""Investment Committee Summary: the CIO Desk's "who agrees, who
disagrees, and how much does it matter" view.

Reuses `investment_proof.committee_validation.CommitteeValidationEngine`
(Macro/Sector/Quality/Value/Catalyst/Technical -- real attribution +
counterfactual agreement/decisiveness rates over the day's model
portfolio) rather than re-deriving anything, and adds two committees that
engine doesn't cover because they aren't return-contributing evidence
categories: a Risk Committee (from `investment_proof.portfolio_validation`'s
concentration/downside numbers) and a Portfolio Committee (from that same
result's weight-reconciliation/decision-conflict checks). The final
"Chief Investment Officer" row is a mechanical tally of how many
committees are aligned -- never an independently-invented verdict.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from agx_research.investment_proof.committee_validation import CommitteeValidationEngine
from agx_research.investment_proof.portfolio_validation import PortfolioValidationResult
from agx_research.knowledge.schema import KnowledgeObject

#: A committee needs at least this many tickers with an opinion before its
#: agreement rate is meaningful enough to label anything but "no_data" --
#: same declared-not-calibrated posture as every other threshold in this
#: codebase (see docs/TECHNICAL_DEBT.md).
MIN_TICKERS_FOR_STANCE = 1
_ALIGNED_THRESHOLD = 0.6
_DIVERGING_THRESHOLD = 0.4


class CommitteeOpinion(BaseModel):
    committee: str
    stance: str
    agreement_rate: float | None = None
    decisive_rate: float | None = None
    tickers_present: int = 0
    note: str


class CommitteeSummaryReport(BaseModel):
    as_of: date
    tickers_evaluated: int
    opinions: list[CommitteeOpinion] = Field(default_factory=list)


def _return_committee_stance(agreement_rate: float | None, tickers_present: int) -> str:
    if tickers_present < MIN_TICKERS_FOR_STANCE or agreement_rate is None:
        return "no_data"
    if agreement_rate >= _ALIGNED_THRESHOLD:
        return "aligned"
    if agreement_rate <= _DIVERGING_THRESHOLD:
        return "diverging"
    return "mixed"


def build_committee_summary(
    as_of: date,
    tickers: list[str],
    knowledge_by_ticker: dict[str, list[KnowledgeObject]],
    *,
    latest_prices: dict[str, float] | None = None,
    portfolio_validation: PortfolioValidationResult | None = None,
) -> CommitteeSummaryReport:
    result = CommitteeValidationEngine().validate(tickers, as_of, knowledge_by_ticker, latest_prices=latest_prices)

    opinions: list[CommitteeOpinion] = []
    for stats in result.committees:
        stance = _return_committee_stance(stats.agreement_rate, stats.tickers_present)
        opinions.append(
            CommitteeOpinion(
                committee=stats.category.value,
                stance=stance,
                agreement_rate=stats.agreement_rate,
                decisive_rate=stats.decisive_rate,
                tickers_present=stats.tickers_present,
                note=(
                    f"Present in {stats.tickers_present} ticker(s); agrees with the final direction "
                    f"{stats.agreement_rate:.0%} of the time, decisive in {stats.decisive_rate:.0%}."
                    if stats.tickers_present
                    else "No knowledge from this category in today's model portfolio."
                ),
            )
        )

    if portfolio_validation is not None:
        risk_elevated = portfolio_validation.concentration.status == "concentrated" or bool(
            portfolio_validation.liquidity_violations
        )
        opinions.append(
            CommitteeOpinion(
                committee="risk",
                stance="elevated" if risk_elevated else "normal",
                note=(
                    f"Herfindahl {portfolio_validation.concentration.herfindahl_index:.3f} "
                    f"({portfolio_validation.concentration.status}); "
                    f"{len(portfolio_validation.liquidity_violations)} liquidity violation(s); "
                    f"expected downside proxy "
                    f"{portfolio_validation.expected_downside_proxy:.2%}."
                    if portfolio_validation.expected_downside_proxy is not None
                    else f"Herfindahl {portfolio_validation.concentration.herfindahl_index:.3f} "
                    f"({portfolio_validation.concentration.status})."
                ),
            )
        )
        portfolio_conflicted = not portfolio_validation.weights_reconcile or bool(
            portfolio_validation.decision_conflicts
        )
        opinions.append(
            CommitteeOpinion(
                committee="portfolio",
                stance="conflicted" if portfolio_conflicted else "consistent",
                note=(
                    f"weights_reconcile={portfolio_validation.weights_reconcile}, "
                    f"{len(portfolio_validation.decision_conflicts)} decision conflict(s)."
                ),
            )
        )

    aligned = sum(1 for o in opinions if o.stance in ("aligned", "normal", "consistent"))
    diverging = sum(1 for o in opinions if o.stance in ("diverging", "elevated", "conflicted"))
    with_data = sum(1 for o in opinions if o.stance != "no_data")
    if with_data == 0:
        cio_stance = "no_data"
    elif diverging == 0:
        cio_stance = "aligned"
    elif aligned > diverging:
        cio_stance = "mixed"
    else:
        cio_stance = "diverging"
    opinions.append(
        CommitteeOpinion(
            committee="chief_investment_officer",
            stance=cio_stance,
            note=f"{aligned}/{with_data} committee(s) aligned, {diverging}/{with_data} diverging.",
        )
    )

    return CommitteeSummaryReport(as_of=as_of, tickers_evaluated=result.tickers_evaluated, opinions=opinions)


__all__ = ["CommitteeOpinion", "CommitteeSummaryReport", "build_committee_summary"]
