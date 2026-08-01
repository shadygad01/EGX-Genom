"""Investment Proof Framework -- the final mission.

Where `institutional_validation/` (a prior mission) answers 10 platform-
level questions ("can the system rank the full universe / reject / hold
cash / ...?"), this package goes one layer deeper: it proves *how* and
*why* the decision engine reaches each individual decision, and whether
that process is stable, calibratable, and trustworthy enough for capital.
It composes `institutional_validation/`'s scenario builders and report
primitives rather than duplicating them -- neither package re-implements
the other's mechanism.

Every engine here follows the same status vocabulary as
`institutional_validation.report.CheckVerdict` (`PASS`/`PARTIAL`/
`BLOCKED`/`FAIL`), reusing that exact enum rather than declaring a
parallel one. This mission's own vocabulary ("READY FOR DATA" instead of
"NOT IMPLEMENTED") is a *rendering* choice, applied wherever `BLOCKED` is
displayed to a human -- the underlying status is still `BLOCKED`, not a
new state. A capability described as ready for data means: the mechanism
is fully engineered and tested against real code paths; it will start
producing real numbers automatically the moment enough real evaluated
history exists, with no redesign required.
"""
