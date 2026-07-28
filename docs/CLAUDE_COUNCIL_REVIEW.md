# Claude Council Review — 2026-07-28

Five independent specialist reviews inspected the current code and tests. This
file records their objections and the resulting engineering decisions; it is
not a claim that external publication gates have passed.

## Reviewers and verdicts

1. **Decision reviewer:** production thresholds, adversarial confidence and
   publication posture needed fail-closed rules. Those items are now enforced.
2. **Source reviewer:** catalogue size overstated operational/legal coverage;
   an owner-authorized robots override contradicted source safety. Legal use is
   now an independent state and the production override was removed.
3. **UX reviewer:** the product needed decision-first Arabic output, an honest
   performance record and direct source truth. Those surfaces now exist.
4. **Scientific reviewer:** found selection leakage, date-misaligned pairs,
   daily returns relabeled as every horizon, readiness bypass, time-traveling
   knowledge, and non-executed actions counted as trades. All six P0 findings
   were corrected in the production path.
5. **Product reviewer:** the landing page could show a research-only BUY beneath
   a do-not-trade warning, while the company page reverted to blended metrics.
   The landing decision now admits only `publication_ready` horizons; company
   research is displayed separately for short, medium and long horizons, with
   research-only position size forced to zero.

## What works well

- One explicit action per horizon, with validity, risk, entry, invalidation and
  evidence fields.
- Fail-closed publication gate and visible blockers.
- Append-only outcome ledger and benchmark-matched performance.
- Source lineage/truth artifacts distinguish catalogue from actual use.
- Arabic RTL decision-first route and explicit abstention.
- Broad automated test coverage across research, API and web layers.

## Weaknesses still requiring improvement

- Evidence references are now verified against RawDocument identity, source,
  hash, fetch time, freshness, coverage, legal state and independence. The
  remaining external task is supplying those real documents at production
  scale, not another self-attested JSON claim.
- Moving-block bootstrap and Newey-West HAC now protect the implemented return
  tests; more advanced regime-specific dependence models remain a calibration
  opportunity once long real histories exist.
- The correction family is now persistent across every stored hypothesis, not
  reset per run. A less conservative pre-registered alpha-spending policy can
  replace cumulative Bonferroni only after real research-volume calibration.
- Entry and invalidation conditions remain prose when no verified numeric/event
  threshold exists; such cases should ultimately abstain.
- Live licensed EGX prices, official statements and a legal approval are absent.

## Free improvement decisions implemented

1. Separate source `legal_use_status` from collector implementation status.
2. Remove the production `respect_robots=False` price override.
3. Seal the chronological test tail before agents discover hypotheses.
4. Align pair returns by shared trade dates.
5. Compute horizon-matched 3/20/126-trading-day forward returns.
6. Use held-out hit rate rather than `1 - p-value` as the confidence input.
7. Enforce Decision Readiness before production recommendations are created.
8. Exclude WATCH, AVOID and ABSTAIN from executed-trade performance.
9. Require positive mean, median and 95% lower bound plus a drawdown ceiling in
   the publication performance gate.
10. Prevent future-discovered knowledge from appearing in past predictions.
11. Hide research-only candidates from the landing-page executable decision and
    force their displayed position size to zero.
12. Resolve publication evidence against the immutable raw-document archive and
    require fresh, complete and independently grouped corroboration.
13. Replace IID bootstrap with moving blocks and use Newey-West HAC for
    overlapping walk-forward windows.
14. Count every persisted hypothesis attempt in the multiple-testing family.

## Council conclusion

AGX is materially safer and clearer than the reviewed baseline, but remains a
research decision system. It must not be represented as publication-ready until
the external gates and the remaining statistical/evidence-reference items above
are closed with real evidence.
