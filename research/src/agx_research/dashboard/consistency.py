"""Cross-artifact publication consistency (AD-65, see
docs/ARCHITECTURE_DECISIONS.md).

Schema/shape validity (`dashboard.validate.validate_dashboard_artifacts`)
and provenance (`dashboard.manifest.is_canonical_production`) each check
one dimension of "can this bundle be trusted." This module checks a
third, distinct one: do the artifacts *agree with each other* about which
execution produced them -- the same `as_of`, the same pipeline mode, a
generation timestamp within the same run -- rather than some file being a
stale leftover a partial/failed run never overwrote.

`source_data_as_of` vs. `execution_report.json`'s `run_dates` is checked
as a one-sided bound (`source_data_as_of` may never be *later* than the
run's own requested range), not exact membership -- a real production
incident (2026-08-07, a run requested for a Friday, an EGX non-trading
day) proved exact membership was wrong: `production.pipeline
.ProductionPipeline._latest_successful_as_of()` deliberately falls back
to the newest *successful trading* run when the requested date is a
weekend/holiday, so `source_data_as_of` legitimately lags `run_dates` on
those days -- an honest data lag, not a staleness bug, and rejecting it
made every weekend/holiday rebuild fail publication outright. What this
check still catches -- `git_commit`/`workflow_run_id` equality and the
`generated_at`/`completed_at` skew bound, both still exact -- already
proves the bundle came from this one execution; the individual-artifact
`as_of` cross-checks below still catch every artifact disagreeing with
`source_data_as_of` regardless of this change.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

from agx_research.dashboard.manifest import ArtifactPublicationManifest

# Two files written by the same run() call are typically milliseconds
# apart; minutes would suggest a stale leftover from a different execution.
MAX_GENERATION_SKEW_SECONDS = 600

# filename -> the field on that artifact that must equal
# manifest.source_data_as_of. Absence of one of these files is not itself
# a problem here -- validate_dashboard_artifacts() is what enforces which
# artifacts must exist; this only checks agreement where both exist.
_AS_OF_FIELDS = {
    "investment_cases.json": "as_of",
    "portfolio_summary.json": "as_of",
    "committee_summary.json": "as_of",
    "warnings.json": "as_of",
    "shadow_fund.json": "date",
}


def _load_json(path: Path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def validate_bundle_consistency(bundle_dir: Path) -> list[str]:
    """Returns a list of problems; empty means every artifact checked
    agrees with manifest.json about as_of, pipeline mode, generation
    time, commit, and workflow run id."""
    problems: list[str] = []
    manifest_raw = _load_json(bundle_dir / "manifest.json")
    if manifest_raw is None:
        return ["manifest.json is missing -- cannot verify cross-artifact consistency"]
    try:
        manifest = ArtifactPublicationManifest.model_validate(manifest_raw)
    except Exception as exc:  # this function's own contract is "return problems, never raise"
        return [f"manifest.json failed to parse as ArtifactPublicationManifest: {exc}"]

    execution_report = _load_json(bundle_dir / "execution_report.json")
    if execution_report is None:
        problems.append("execution_report.json is missing")
    else:
        if execution_report.get("execution_mode") != manifest.pipeline_mode:
            problems.append(
                f"execution_report.json execution_mode={execution_report.get('execution_mode')!r} "
                f"!= manifest.json pipeline_mode={manifest.pipeline_mode!r}"
            )

        if manifest.source_data_as_of is not None:
            run_dates = execution_report.get("run_dates", [])
            if run_dates:
                # `run_dates` is the raw calendar range run() was invoked
                # for, unaware of `_latest_successful_as_of()`'s deliberate
                # fallback to the newest *successful trading* run when the
                # requested date is itself a weekend/holiday (see that
                # method's own docstring: "Pages can be rebuilt on any
                # calendar day, for example after a UI push on Friday").
                # On EGX's real Friday/Saturday non-trading days this
                # correctly makes source_data_as_of an earlier date than
                # any entry in run_dates -- an honest data lag, not a
                # staleness bug -- so exact membership would reject every
                # legitimate weekend/holiday rebuild. What this check must
                # still catch is source_data_as_of being *later* than the
                # run was even asked to cover, which is never legitimate.
                latest_requested = max(date.fromisoformat(d) for d in run_dates)
                if manifest.source_data_as_of > latest_requested:
                    problems.append(
                        f"manifest.json source_data_as_of={manifest.source_data_as_of.isoformat()!r} "
                        f"is later than every date execution_report.json run_dates={run_dates!r} "
                        "covers -- published data cannot be newer than what this run was asked to produce."
                    )

        completed_at_raw = execution_report.get("completed_at")
        if completed_at_raw:
            completed_at = datetime.fromisoformat(completed_at_raw)
            skew = abs((completed_at - manifest.generated_at).total_seconds())
            if skew > MAX_GENERATION_SKEW_SECONDS:
                problems.append(
                    f"execution_report.json completed_at ({completed_at_raw}) and manifest.json "
                    f"generated_at ({manifest.generated_at.isoformat()}) differ by {skew:.0f}s "
                    f"(> {MAX_GENERATION_SKEW_SECONDS}s) -- may be from different executions"
                )

        er_commit = execution_report.get("git_commit")
        if er_commit is not None and er_commit != manifest.git_commit:
            problems.append(
                f"execution_report.json git_commit={er_commit!r} != manifest.json "
                f"git_commit={manifest.git_commit!r}"
            )

        er_run_id = execution_report.get("workflow_run_id")
        if er_run_id is not None and er_run_id != manifest.workflow_run_id:
            problems.append(
                f"execution_report.json workflow_run_id={er_run_id!r} != manifest.json "
                f"workflow_run_id={manifest.workflow_run_id!r}"
            )

    if manifest.source_data_as_of is not None:
        expected = manifest.source_data_as_of.isoformat()

        for filename, field in _AS_OF_FIELDS.items():
            payload = _load_json(bundle_dir / filename)
            if payload is None:
                continue
            actual = payload.get(field)
            if actual != expected:
                problems.append(
                    f"{filename}'s {field}={actual!r} != manifest.json "
                    f"source_data_as_of={expected!r}"
                )

        recommendations = _load_json(bundle_dir / "recommendations.json")
        if recommendations:
            mismatched = sorted(
                {r.get("as_of") for r in recommendations if r.get("as_of") != expected}
            )
            if mismatched:
                problems.append(
                    f"recommendations.json contains as_of value(s) {mismatched} that don't "
                    f"match manifest.json source_data_as_of={expected!r}"
                )

    return problems
