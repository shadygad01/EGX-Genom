"""Regression test for the one shared-state mutation in
`.github/workflows/deploy-pages.yml` (AD-65, docs/ARCHITECTURE_DECISIONS.md):
"Persist updated production state to production/state-latest" force-pushes
a real branch every scheduled main-branch run restores from. A
`workflow_dispatch` test run from a feature branch must be able to
exercise collection/analysis/validation end-to-end without that step ever
running -- otherwise triggering the workflow for validation purposes
would itself corrupt shared production continuity. Checked as plain text
(no YAML dependency) the same way `check_truth_preservation.py` checks
other structural invariants.
"""

from __future__ import annotations

from pathlib import Path

WORKFLOW_PATH = (
    Path(__file__).resolve().parents[2] / ".github" / "workflows" / "deploy-pages.yml"
)


def _step_block(text: str, step_name: str) -> str:
    start = text.index(f"- name: {step_name}")
    next_step = text.find("\n      - name:", start + 1)
    return text[start : next_step if next_step != -1 else len(text)]


def test_persist_production_state_step_is_gated_to_main_only():
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    block = _step_block(text, "Persist updated production state to production/state-latest")
    assert "if:" in block, "the persist-state step must have an if: condition at all"
    assert "github.ref == 'refs/heads/main'" in block, (
        "the persist-state step must be gated to main -- otherwise a workflow_dispatch "
        "test run from a feature branch would force-push production/state-latest, "
        "corrupting shared state every scheduled main-branch run restores from"
    )


def test_deploy_job_remains_gated_to_main_only():
    """Same invariant, the pre-existing half -- regression-proofed here too
    so both halves of "feature branches never mutate shared production
    state" are checked in one place."""
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    deploy_job_start = text.index("\n  deploy:")
    deploy_job = text[deploy_job_start:]
    if_line_start = deploy_job.index("if:")
    if_line = deploy_job[if_line_start : deploy_job.index("\n", if_line_start)]
    assert "github.ref == 'refs/heads/main'" in if_line


def test_no_other_step_pushes_to_a_shared_branch_unconditionally():
    """Structural floor: any future step added to this workflow that runs
    `git push` must either target a per-run-unique ref or be gated to
    main, so this regression can't quietly reappear one step over."""
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    for line_no, line in enumerate(text.splitlines(), start=1):
        if "git push" not in line:
            continue
        # Walk backwards to the nearest preceding "- name:" step header and
        # confirm that step's own if: condition (if any) is main-gated.
        preceding = text.splitlines()[:line_no]
        step_start = next(
            (i for i in range(len(preceding) - 1, -1, -1) if "- name:" in preceding[i]), None
        )
        assert step_start is not None, f"git push at line {line_no} is outside any named step"
        step_name = preceding[step_start].split("- name:", 1)[1].strip()
        block = _step_block(text, step_name)
        assert "github.ref == 'refs/heads/main'" in block, (
            f"step {step_name!r} runs 'git push' but isn't gated to main -- "
            "a feature-branch workflow_dispatch run would mutate shared state"
        )
