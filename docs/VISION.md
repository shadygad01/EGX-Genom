# Project Alpha Genome (AGX) — Vision

> This document is the project charter, preserved verbatim as the source of
> truth for scope and principles. See `CLAUDE.md` for how the current
> codebase maps onto it, and `docs/ARCHITECTURE.md` for the technical design.

## Vision

Project Alpha Genome (AGX) is an autonomous quantitative research platform
dedicated exclusively to the Egyptian Stock Exchange.

Its mission is not to analyze the market.

Its mission is to continuously discover, validate, learn, and improve
predictive investment knowledge that generates Alpha opportunities in EGX30.

The system must behave as an independent research organization rather than a
recommendation engine.

No component is allowed to rely on intuition.

Every conclusion must be supported by measurable evidence.

## Core Mission

Every trading day the platform must answer one question:

> Which EGX30 stocks currently offer the highest probability investment
> opportunities over multiple time horizons, and why?

## Core Principles

These principles are immutable.

1. **No recommendation without evidence.**
2. **No discovered pattern enters production before statistical validation.**
3. **Every prediction must be explainable.** Black-box predictions are
   forbidden.
4. **Every discovered relationship has a lifecycle.** Birth → Validation →
   Promotion → Monitoring → Retirement.
5. **Everything is versioned.** Patterns, features, models, knowledge,
   experiments, predictions, datasets.
6. **AI never decides alone.** AI proposes. Evidence approves.
7. **Knowledge continuously evolves.** Nothing is permanent.
8. **Humans define goals. The system discovers knowledge.**

## Primary Objective

Discover Alpha. Not news. Not technical indicators. Not financial statements.
Alpha.

## Success Criteria

The platform succeeds only if it continuously improves its predictive
performance through autonomous research.

## Supported Market

Egyptian Stock Exchange only.

- Primary focus: EGX30
- Secondary data: All listed Egyptian companies whenever they improve
  predictive capability.

## Time Horizons

The platform simultaneously optimizes three independent horizons. Each
horizon has independent models; their outputs are combined by a Meta
Decision Engine.

| Horizon         | Window          |
|-----------------|-----------------|
| Micro Alpha     | 1–3 trading days |
| Swing Alpha     | 1–4 weeks        |
| Investment Alpha| 1–6 months       |

## System Philosophy

The market is treated as a living network, not as independent stocks. Every
company affects other companies. Every sector affects other sectors.
Macroeconomic variables affect sectors. Political events affect macro
variables. Corporate events affect prices. The system must model these
relationships rather than isolated data.

## Definition of Alpha

Alpha is defined as: a statistically validated market behavior that
repeatedly produces excess expected return after accounting for uncertainty
and risk.

- Patterns without repeatability are not Alpha.
- Patterns without validation are not Alpha.
- Patterns without explanation are not Alpha.

## Research Philosophy

The platform does not search for answers. It generates hypotheses, e.g.:

- Does higher oil price improve fertilizer sector performance?
- Does EGX70 lead EGX30?
- Do positive earnings create delayed reactions?
- Do foreign inflows predict banking strength?

Every hypothesis becomes an experiment. Experiments either survive or
disappear.

## Scientific Method

Every hypothesis follows the same lifecycle:

```
Observation
  -> Hypothesis
  -> Data Collection
  -> Experiment
  -> Statistical Validation
  -> Stress Test
  -> Backtest
  -> Peer Validation
  -> Promotion
  -> Continuous Monitoring
  -> Retirement if performance degrades
```

## Knowledge Philosophy

Knowledge is not static. Every knowledge object contains:

- Unique ID
- Discovery Date
- Creator Agent
- Supporting Evidence
- Confidence
- Statistical Strength
- Economic Explanation
- Affected Assets
- Applicable Time Horizon
- Expected Return
- Expected Risk
- Current Status
- Performance History
- Retirement Status

## Agents Philosophy

Agents are researchers, not decision makers. Each agent has one
responsibility and produces research. No agent can publish knowledge
directly.

## Decision Philosophy

Final recommendations are created only after combining: Market Structure,
Macroeconomics, Corporate Events, Financial Performance, News Intelligence,
Liquidity, Technical Structure, Historical Patterns, Discovered Knowledge,
Risk Assessment.

No individual signal can create a recommendation.

## Continuous Learning

Every market day creates new knowledge. Old knowledge is reevaluated. Weak
knowledge is retired. Strong knowledge gains confidence. The platform never
stops learning.

## Explainability

Every recommendation must answer:

- Why this stock?
- Why now?
- Why not another stock?
- What evidence supports this idea?
- What historical cases are similar?
- What invalidates this thesis?

## Final Goal

Build the most intelligent research system ever created for the Egyptian
Stock Exchange — not by encoding investment rules, but by allowing the
platform to discover them independently using scientific validation and
continuous learning.
