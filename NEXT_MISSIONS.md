# Next Missions

All 9 sections of the Production User Experience are now built (see
`CURRENT_MISSION.md`). What's next, in order:

## 1. Quality pass across all 9 sections

The mission's own quality checklist, re-verified now that every section
exists rather than assumed page by page:

- **Responsive layout** — spot-checked at 1024px and 1700px so far (both
  clean); a pass at common laptop/ultrawide widths and the sidebar's
  collapse behavior on narrow viewports is still worth a dedicated look.
- **Accessibility** — `aria-label`/`role` present on the nav, states, and
  progress meters; a full keyboard-navigation and screen-reader pass
  (tab order across master/detail pages, focus trapping, color-contrast
  check on the Meter/Badge palette) has not been done yet.
- **Performance** — the Knowledge Graph's force layout is O(n²) per
  render pass; fine at current data volumes (tens of nodes) but worth
  re-checking once real provenance data grows the graph substantially.
- **Cross-page consistency** — every page uses the shared primitives
  (`Card`, `Badge`, `StatTile`, `DataTable`, `Section`,
  `EmptyState`/`LoadingState`/`ErrorState`) and the same empty-state
  honesty pattern; worth a final side-by-side pass once real (non-mock)
  data exists to compare against.

## 2. Known frontend gaps waiting on new backend artifacts

Each of these was deliberately left as an honest "not yet available" UI
gap rather than fabricated, per the mission's own anti-fabrication
constraint:

- **Market Regime classification** (Market Intelligence, Company Research
  Workspace) — no artifact exists upstream yet.
- **Market Breadth & Liquidity** (Market Intelligence) — needs a
  backend-computed artifact (advancers/decliners, adjusted volume); the
  frontend must not compute returns from raw price bars itself.
- **Review Board decision history** (Research Center) — no repository
  persists past `BoardDecision`s yet.
- **Discovery Engine detail** (Mission Control) — `acquisition_intelligence`
  has no dashboard export yet.
- **Raw log lines** (System Administration) — no artifact carries them
  yet.

None of these block using the platform today — each shows an honest
empty state explaining what's missing and why, per `CLAUDE.md`'s
anti-fabrication principle. Building any of them is a small, well-scoped
follow-up (a thin new export following the same pattern as every other
artifact) whenever the underlying backend capability exists.

## 3. Backend/data-acquisition mission — paused, not abandoned

The prior mission's own next-steps (EGX official connection, richer
PDF-based extraction, calibration passes once real data exists) remain
valid but are paused per the project owner's instruction not to do
backend work during this frontend phase. See `docs/ROADMAP.md`'s
"Post-1.0" section for where they resume.

## Beyond this

No further page or section is queued. Future work here should come from
either the quality pass above, or a genuine gap the project owner
surfaces after using the platform.
