## Summary

<!-- What changed and why. -->

## Truth Preservation checklist

Required for every PR — see `docs/TRUTH_PRESERVATION_POLICY.md` (`AD-60`).
**If any answer is YES, this PR must not be merged as-is**; rework the
change to fail closed (return `None`/empty/an unavailable error, leave a
status string honest) instead.

- [ ] Did this PR introduce any synthetic value (a number invented when a
      real one was unavailable)?
- [ ] Did this PR replace an UNKNOWN with a substitute (a market price
      standing in for a fair value, a default confidence, a guessed
      status)?
- [ ] Did this PR infer unavailable information instead of leaving it
      absent?
- [ ] Did this PR bypass the production decision engine (`DecisionService`/
      `meta.decision_engine`) — e.g. a frontend/API component computing or
      inferring a `BUY`/`SELL`/`HOLD`/action label itself?
- [ ] Did this PR weaken provenance (a displayed value with no `Provenance`
      it can point to)?
- [ ] Did this PR weaken a test protecting truthfulness, provenance,
      decision integrity, or status integrity (renamed, loosened, or
      deleted without a stronger replacement)?

## Test plan

<!-- Commands run and their result, e.g.:
- [ ] `cd research && uv run pytest`
- [ ] `npm test -w web -- --run`
- [ ] `npm test -w api -- --run`
- [ ] `npm run build -w web`
-->
