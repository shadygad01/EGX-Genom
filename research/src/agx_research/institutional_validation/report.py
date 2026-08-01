"""The report shape every check produces, and the aggregate report the
runner assembles. Deliberately a pydantic model set, following the same
"one schema, JSON-exportable, model_dump(mode='json')" pattern every other
persisted/exported entity in this codebase already uses -- not a bespoke
dict shape.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class CheckVerdict(str, Enum):
    #: The property was exercised against real code and holds.
    PASS = "pass"
    #: The property holds in some scenarios but not all; the gap is named.
    PARTIAL = "partial"
    #: The mechanism is real and structurally correct, but current data
    #: coverage (mock/synthetic) can't yet demonstrate it end-to-end --
    #: an honest gap, never a defect.
    BLOCKED = "blocked"
    #: The property was exercised and does not hold -- a genuine defect.
    FAIL = "fail"


# Ranks worst-to-best for computing an overall verdict -- FAIL always
# dominates (a real defect anywhere fails the whole report); BLOCKED
# dominates PARTIAL/PASS only in the sense that it's reported, never hidden.
_SEVERITY = {CheckVerdict.FAIL: 3, CheckVerdict.PARTIAL: 2, CheckVerdict.BLOCKED: 1, CheckVerdict.PASS: 0}


class CheckResult(BaseModel):
    question_number: int
    question: str
    verdict: CheckVerdict
    #: Concrete, numbered evidence -- real counts and outcomes from running
    #: the actual scenario, never a restatement of the question as an answer.
    evidence: list[str] = Field(default_factory=list)
    #: Named, specific gaps or defects this check found -- empty only when
    #: nothing was found, never omitted to make a PASS look cleaner.
    findings: list[str] = Field(default_factory=list)
    scenario_ids: list[str] = Field(default_factory=list)


class ValidationReport(BaseModel):
    generated_at: datetime
    #: Which repeatable scenarios were actually run to produce this report.
    scenarios_run: list[str]
    results: list[CheckResult]
    overall_verdict: CheckVerdict

    @classmethod
    def build(cls, scenarios_run: list[str], results: list[CheckResult]) -> "ValidationReport":
        overall = max((r.verdict for r in results), key=lambda v: _SEVERITY[v], default=CheckVerdict.PASS)
        return cls(
            generated_at=datetime.now(),
            scenarios_run=scenarios_run,
            results=sorted(results, key=lambda r: r.question_number),
            overall_verdict=overall,
        )

    def to_markdown(self) -> str:
        lines = [
            "# Institutional Investment Validation Report",
            "",
            f"Generated: {self.generated_at.isoformat()}",
            f"Overall verdict: **{self.overall_verdict.value.upper()}**",
            f"Scenarios run: {', '.join(self.scenarios_run)}",
            "",
        ]
        for result in self.results:
            lines.append(f"## {result.question_number}. {result.question}")
            lines.append(f"**Verdict: {result.verdict.value.upper()}**")
            lines.append("")
            if result.evidence:
                lines.append("Evidence:")
                lines.extend(f"- {e}" for e in result.evidence)
            if result.findings:
                lines.append("")
                lines.append("Findings:")
                lines.extend(f"- {f}" for f in result.findings)
            lines.append("")
        return "\n".join(lines)


__all__ = ["CheckResult", "CheckVerdict", "ValidationReport"]
