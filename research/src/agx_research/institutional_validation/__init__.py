"""Institutional Investment Validation.

Deliberately a separate package from `validation/` (MASTER_PROMPT.md
System 11, the Validation Framework), which statistically validates one
*hypothesis* before promotion (significance, backtest, stress test). This
package validates the *decision engine's* aggregate behavior once
hypotheses have already become knowledge -- whether it ranks the full
universe, rejects appropriately, holds cash, builds a coherent portfolio,
compares against a benchmark, detects thesis failure, explains itself, and
traces every decision back to evidence. The two never overlap: this
package imports `research/`'s decision-facing modules (`meta/`,
`decision_service/`, `portfolio/`, `learning/`) and exercises them through
real, repeatable scenarios -- it adds no new statistical test of its own.

Every check here is graded PASS / PARTIAL / BLOCKED / FAIL
(`report.CheckVerdict`) rather than a bare boolean: BLOCKED means the
mechanism is real and correct but current data coverage can't yet
demonstrate it end-to-end (an honest gap, matching this codebase's
no-fabrication discipline elsewhere) -- it is not the same as FAIL, which
means the property was checked and does not hold.
"""
