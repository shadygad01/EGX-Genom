import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Badge, type BadgeVariant } from "../components/primitives/Badge";
import { Card } from "../components/primitives/Card";
import { DataTable } from "../components/primitives/DataTable";
import { Disclaimer } from "../components/primitives/Disclaimer";
import { Meter } from "../components/primitives/Meter";
import { Section } from "../components/primitives/Section";
import { StatTile } from "../components/primitives/StatTile";
import { EmptyState, ErrorState, LoadingState } from "../components/primitives/States";
import { dataProvider } from "../data/factory";
import { LiveDecisionsUnavailableError, type MacroSnapshot } from "../data/DataProvider";
import { useArtifact } from "../hooks/useArtifact";
import { useEnumLabel } from "../hooks/useEnumLabel";
import { useFormatters } from "../hooks/useFormatters";
import { usePortfolioPositions } from "../hooks/usePortfolioPositions";
import { formatPercent, formatSignedPercent, titleCase } from "../lib/format";
import type {
  CapitalAllocationPlan,
  CapitalSource,
  PortfolioPosition,
  PositionAwareDecision,
  Recommendation,
  SystemMaturityLevel,
} from "../types";
import styles from "./CIODesk.module.css";

function formatCapitalSources(sources: CapitalSource[]): string {
  if (sources.length === 0) return "—";
  return sources.map((s) => `${s.ticker ?? "cash"}: ${formatPercent(s.amount)}`).join(", ");
}

const TREND_VARIANT: Record<string, BadgeVariant> = {
  bullish: "positive",
  bearish: "negative",
  neutral: "neutral",
};

const VOLATILITY_VARIANT: Record<string, BadgeVariant> = {
  low: "neutral",
  elevated: "warning",
  high: "negative",
};

const ACTION_VARIANT: Record<string, BadgeVariant> = {
  buy: "positive",
  increase_position: "positive",
  hold: "neutral",
  reduce_position: "warning",
  exit: "negative",
  no_action: "default",
};

const WARNING_VARIANT: Record<string, "warningCritical" | "warningWarning" | "warningInfo"> = {
  critical: "warningCritical",
  warning: "warningWarning",
  info: "warningInfo",
};

const COMMITTEE_STANCE_VARIANT: Record<string, BadgeVariant> = {
  aligned: "positive",
  normal: "positive",
  consistent: "positive",
  mixed: "warning",
  diverging: "negative",
  elevated: "negative",
  conflicted: "negative",
  no_data: "neutral",
};

const SYSTEM_MATURITY_VARIANT: Record<SystemMaturityLevel, BadgeVariant> = {
  early: "neutral",
  validating: "neutral",
  developing: "warning",
  established: "positive",
  verified: "positive",
};

type OpportunityRow = { kind: "opportunity"; position: PortfolioPosition; companyName: string; recommendation: Recommendation | null };
type ActionRow = { kind: "decision"; decision: PositionAwareDecision; companyName: string };
type TodaysActionRow = OpportunityRow | ActionRow;

/** The CIO Desk -- landing page, answers exactly one question: "what
 * should I do today?" Five sections only (Market Regime / Today's
 * Actions / Portfolio Summary / Warnings / Investment Committee Summary),
 * per the Institutional Investment Operating System mission's product
 * law. Research content (news, papers, knowledge timelines, system
 * health) intentionally lives elsewhere now -- this page never mixes in
 * a second question. */
export function CIODesk() {
  const { t } = useTranslation("cioDesk");
  const { t: tCommon } = useTranslation("common");
  const label = useEnumLabel();
  const { formatDate } = useFormatters();
  const navigate = useNavigate();
  const { toPositionInputs, hasPositions } = usePortfolioPositions();

  const marketState = useArtifact((p) => p.getMarketState());
  const regime = useArtifact((p) => p.getMarketRegime());
  const investmentCases = useArtifact((p) => p.getInvestmentCases());
  const portfolioSummary = useArtifact((p) => p.getPortfolioSummary());
  const warnings = useArtifact((p) => p.getWarnings());
  const committeeSummary = useArtifact((p) => p.getCommitteeSummary());
  const systemMaturity = useArtifact((p) => p.getSystemMaturity());
  const macroSnapshot = useArtifact((p) => p.getMacroSnapshot());
  const shadowFund = useArtifact((p) => p.getShadowFund());

  const [liveDecisions, setLiveDecisions] = useState<PositionAwareDecision[] | null>(null);
  const [liveCapitalPlan, setLiveCapitalPlan] = useState<CapitalAllocationPlan | null>(null);
  const [liveLoading, setLiveLoading] = useState(false);
  const [liveUnavailable, setLiveUnavailable] = useState(false);

  const asOf = marketState.data?.as_of ?? new Date().toISOString().slice(0, 10);
  const companyNames = marketState.data?.constituents ?? {};

  useEffect(() => {
    if (!hasPositions) {
      setLiveDecisions(null);
      setLiveCapitalPlan(null);
      return;
    }
    let cancelled = false;
    setLiveLoading(true);
    setLiveUnavailable(false);
    const request = { date: asOf, positions: toPositionInputs() };
    Promise.all([dataProvider.postDecisions(request), dataProvider.postCapitalAllocation(request)])
      .then(([decisions, plan]) => {
        if (!cancelled) {
          setLiveDecisions(decisions);
          setLiveCapitalPlan(plan);
        }
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        if (err instanceof LiveDecisionsUnavailableError) setLiveUnavailable(true);
        setLiveDecisions(null);
        setLiveCapitalPlan(null);
      })
      .finally(() => {
        if (!cancelled) setLiveLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasPositions, asOf]);

  const actionRows = useMemo<TodaysActionRow[]>(() => {
    if (liveDecisions) {
      return liveDecisions
        .filter((d) => d.action !== "no_action" && d.action !== "hold")
        .sort((a, b) => Math.abs(b.target_weight - b.current_weight) - Math.abs(a.target_weight - a.current_weight))
        .map((decision) => ({ kind: "decision" as const, decision, companyName: companyNames[decision.ticker] ?? "" }));
    }
    const positions = investmentCases.data?.portfolio?.positions ?? [];
    const recommendationByTicker = new Map((investmentCases.data?.recommendations ?? []).map((r) => [r.ticker, r]));
    return positions
      .filter((p) => p.weight > 0)
      .sort((a, b) => b.weight - a.weight)
      .map((position) => ({
        kind: "opportunity" as const,
        position,
        companyName: companyNames[position.ticker] ?? "",
        recommendation: recommendationByTicker.get(position.ticker) ?? null,
      }));
  }, [liveDecisions, investmentCases.data, companyNames]);

  const executionCandidates = useMemo(() => {
    const recommendations = investmentCases.data?.recommendations ?? [];
    const prices = marketState.data?.dataset_snapshot.price_history ?? {};
    return recommendations
      .map((recommendation) => {
        const decision = recommendation.horizon_decisions?.investment;
        const latestBar = prices[recommendation.ticker]?.at(-1);
        const actionable = decision?.action === "buy_candidate" && decision.publication_status === "publication_ready";
        const blocker = decision?.abstention_reasons?.[0]
          ?? (decision?.publication_status === "research_only" ? t("executionDesk.researchOnly") : decision?.action ?? t("executionDesk.whyNot"));
        return { recommendation, decision, latestBar, actionable, blocker };
      })
      .sort((a, b) => {
        if (a.actionable !== b.actionable) return a.actionable ? -1 : 1;
        return (b.decision?.risk_adjusted_score ?? -Infinity) - (a.decision?.risk_adjusted_score ?? -Infinity);
      });
  }, [investmentCases.data, marketState.data, t]);

  const actionableCandidates = executionCandidates.filter((candidate) => candidate.actionable).slice(0, 8);
  const blockedCandidates = executionCandidates.filter((candidate) => !candidate.actionable).slice(0, 8);

  // Holdings were entered but the live backend itself is unavailable (the
  // static deployment) vs. no holdings entered yet -- two different blockers,
  // so the per-card empty state must say which one actually applies.
  // The shadow fund is a real, position-unaware production artifact. It can
  // safely power model allocation intelligence in static mode, but it must
  // never be presented as a personalized plan for the investor's holdings.
  const modelCapitalPlan = shadowFund.data?.capital_allocation_plan ?? null;
  const displayedCapitalPlan = liveCapitalPlan ?? modelCapitalPlan;
  const needsHoldingsCardTitle = liveUnavailable && !modelCapitalPlan
    ? t("capitalAllocation.needsBackendTitle")
    : t("capitalAllocation.needsHoldingsTitle");

  return (
    <>
      <Disclaimer />

      <Card title={t("marketRegime.title")} subtitle={t("marketRegime.subtitle")}>
        {regime.loading && <LoadingState rows={1} />}
        {regime.error && <ErrorState detail={regime.error.message} onRetry={regime.reload} />}
        {!regime.loading && !regime.error && !regime.data && (
          <EmptyState title={t("marketRegime.emptyTitle")} detail={t("marketRegime.emptyDetail")} />
        )}
        {regime.data && (
          <div className={styles.regimeBanner}>
            <Badge variant={TREND_VARIANT[regime.data.trend] ?? "neutral"}>{label("marketTrend", regime.data.trend)}</Badge>
            <Badge variant={VOLATILITY_VARIANT[regime.data.volatility] ?? "neutral"}>
              {t("marketRegime.volatilityBadge", { level: label("volatilityLevel", regime.data.volatility) })}
            </Badge>
            {regime.data.cumulative_return_pct != null && (
              <span className={styles.regimeReturn}>
                {formatSignedPercent(regime.data.cumulative_return_pct / 100)} ({regime.data.trading_days_observed}d)
              </span>
            )}
            <Link to="/market" className={styles.regimeLink}>{t("marketRegime.viewDetail")}</Link>
          </div>
        )}
      </Card>

      <Section title={t("executionDesk.title")} description={t("executionDesk.description")}>
        <Card title={t("executionDesk.actionable")} subtitle={t("executionDesk.staleData")}>
          {actionableCandidates.length === 0 ? (
            <EmptyState title={t("executionDesk.noActionable")} />
          ) : (
            <DataTable
              rows={actionableCandidates}
              getRowKey={(row) => row.recommendation.ticker}
              onRowClick={(row) => navigate(`/cases/${row.recommendation.ticker}`)}
              columns={[
                {
                  key: "ticker",
                  header: tCommon("table.ticker"),
                  render: (row) => <span className={`${styles.tickerCode} num`}>{row.recommendation.ticker}</span>,
                },
                {
                  key: "action",
                  header: tCommon("table.decision"),
                  render: (row) => <Badge variant="positive">{titleCase(row.decision?.action ?? "buy_candidate")}</Badge>,
                },
                {
                  key: "price",
                  header: t("executionDesk.referencePrice"),
                  align: "right",
                  render: (row) => <span className="num">{row.latestBar?.close != null ? row.latestBar.close.toFixed(2) : "—"}</span>,
                },
                {
                  key: "return",
                  header: tCommon("table.expectedReturn"),
                  align: "right",
                  render: (row) => <span className="num">{formatSignedPercent(row.decision?.expected_return ?? 0)}</span>,
                },
                {
                  key: "confidence",
                  header: tCommon("table.confidence"),
                  render: (row) => <Meter value={row.decision?.confidence ?? 0} label={formatPercent(row.decision?.confidence ?? 0)} />,
                },
                {
                  key: "entry",
                  header: t("executionDesk.entry"),
                  render: (row) => <span className={styles.thesisCell}>{row.decision?.entry_condition ?? "—"}</span>,
                },
                {
                  key: "review",
                  header: t("executionDesk.review"),
                  render: (row) => <span className="num">{row.decision?.valid_until ?? "—"}</span>,
                },
              ]}
            />
          )}
        </Card>
        <Card title={t("executionDesk.blocked")} subtitle={t("executionDesk.blockedDetail")}>
          {blockedCandidates.length === 0 ? (
            <EmptyState title={t("executionDesk.noBlockers")} />
          ) : (
            <DataTable
              rows={blockedCandidates}
              getRowKey={(row) => row.recommendation.ticker}
              onRowClick={(row) => navigate(`/cases/${row.recommendation.ticker}`)}
              columns={[
                {
                  key: "ticker",
                  header: tCommon("table.ticker"),
                  render: (row) => <span className={`${styles.tickerCode} num`}>{row.recommendation.ticker}</span>,
                },
                {
                  key: "action",
                  header: tCommon("table.decision"),
                  render: (row) => <Badge variant="warning">{titleCase(row.decision?.action ?? "abstain")}</Badge>,
                },
                {
                  key: "reason",
                  header: t("executionDesk.whyNot"),
                  render: (row) => <span className={styles.riskCell}>{row.blocker}</span>,
                },
                {
                  key: "review",
                  header: t("executionDesk.review"),
                  render: (row) => <span className="num">{row.decision?.valid_until ?? "—"}</span>,
                },
              ]}
            />
          )}
        </Card>
      </Section>

      {!hasPositions && (
        <Card title={t("holdingsCta.title")} className={styles.holdingsCta}>
          <p className={styles.holdingsCtaDetail}>{t("holdingsCta.detail")}</p>
          <Link to="/portfolio" className={styles.holdingsCtaLink}>{t("holdingsCta.action")}</Link>
        </Card>
      )}

      <Section title={t("capitalAllocation.title")} description={t("capitalAllocation.description")}>
        <p className={styles.actionsSourceNote}>
          {liveCapitalPlan
            ? t("capitalAllocation.sourceLive")
            : displayedCapitalPlan
              ? t("capitalAllocation.sourceShadowFund")
              : liveUnavailable
                ? t("capitalAllocation.sourceUnavailable")
                : t("capitalAllocation.sourceModelPortfolio")}
        </p>

        <Card title={t("capitalAllocation.queue.title")} subtitle={t("capitalAllocation.queue.description")}>
          {(liveLoading || investmentCases.loading) && <LoadingState rows={4} />}
          {!liveLoading && !investmentCases.loading && displayedCapitalPlan && (
            <DataTable
              rows={displayedCapitalPlan.queue}
              getRowKey={(row) => row.ticker}
              onRowClick={(row) => navigate(`/cases/${row.ticker}`)}
              emptyTitle={t("todaysActions.emptyTitle")}
              emptyDetail={t("todaysActions.emptyDetail")}
              columns={[
                {
                  key: "priority",
                  header: t("capitalAllocation.queue.priority"),
                  render: (row) => <span className="num">#{row.priority}</span>,
                },
                {
                  key: "ticker",
                  header: tCommon("table.ticker"),
                  render: (row) => (
                    <div className={styles.tickerCell}>
                      <span className={`${styles.tickerCode} num`}>{row.ticker}</span>
                      <span className={styles.tickerCompany}>
                        {companyNames[row.ticker] ?? ""}
                        {row.sector ? ` · ${row.sector}` : ""}
                      </span>
                    </div>
                  ),
                },
                {
                  key: "decision",
                  header: tCommon("table.decision"),
                  render: (row) => <Badge variant={ACTION_VARIANT[row.action] ?? "default"}>{titleCase(row.action)}</Badge>,
                },
                {
                  key: "confidence",
                  header: t("capitalAllocation.queue.confidence"),
                  render: (row) => <Meter value={row.confidence} label={formatPercent(row.confidence)} />,
                },
                {
                  key: "weight",
                  header: t("capitalAllocation.queue.targetAllocation"),
                  align: "right",
                  render: (row) => (
                    <span className="num">
                      {formatPercent(row.target_weight)} ({formatSignedPercent(row.capital_delta)})
                    </span>
                  ),
                },
                {
                  key: "requiredAction",
                  header: t("capitalAllocation.queue.requiredAction"),
                  render: (row) => <span className={styles.thesisCell}>{row.required_action}</span>,
                },
                {
                  key: "contribution",
                  header: t("capitalAllocation.queue.expectedContribution"),
                  align: "right",
                  render: (row) => (
                    <span className="num">{row.expected_contribution != null ? formatSignedPercent(row.expected_contribution) : "—"}</span>
                  ),
                },
                {
                  key: "benefit",
                  header: t("capitalAllocation.queue.marginalBenefit"),
                  align: "right",
                  render: (row) => <span className="num">{row.marginal_benefit.toFixed(3)}</span>,
                },
                {
                  key: "risk",
                  header: t("capitalAllocation.queue.marginalRisk"),
                  align: "right",
                  render: (row) => <span className="num">{row.marginal_risk != null ? formatPercent(row.marginal_risk) : "—"}</span>,
                },
                {
                  key: "sources",
                  header: t("capitalAllocation.queue.capitalSources"),
                  render: (row) => <span className={styles.thesisCell}>{formatCapitalSources(row.capital_sources)}</span>,
                },
                {
                  key: "opportunityCost",
                  header: t("capitalAllocation.queue.opportunityCost"),
                  render: (row) => <span className={styles.riskCell}>{row.opportunity_cost_note}</span>,
                },
                {
                  key: "reasoning",
                  header: t("capitalAllocation.queue.reasoning"),
                  render: (row) =>
                    row.reasoning.length === 0 ? (
                      <span className={styles.riskCell}>—</span>
                    ) : (
                      <ul className={styles.reasonsList}>
                        {row.reasoning.map((reason, i) => (
                          <li key={i}>{reason}</li>
                        ))}
                      </ul>
                    ),
                },
              ]}
            />
          )}
          {!liveLoading && !investmentCases.loading && !displayedCapitalPlan && (
            <>
              <p className={styles.actionsSourceNote}>{t("capitalAllocation.queue.fallbackNote")}</p>
              <DataTable
                rows={actionRows}
                getRowKey={(row) => (row.kind === "decision" ? row.decision.ticker : row.position.ticker)}
                onRowClick={(row) => navigate(`/cases/${row.kind === "decision" ? row.decision.ticker : row.position.ticker}`)}
                emptyTitle={t("todaysActions.emptyTitle")}
                emptyDetail={t("todaysActions.emptyDetail")}
                columns={[
                  {
                    key: "ticker",
                    header: tCommon("table.ticker"),
                    render: (row) => {
                      const ticker = row.kind === "decision" ? row.decision.ticker : row.position.ticker;
                      return (
                        <div className={styles.tickerCell}>
                          <span className={`${styles.tickerCode} num`}>{ticker}</span>
                          <span className={styles.tickerCompany}>{row.companyName}</span>
                        </div>
                      );
                    },
                  },
                  {
                    key: "decision",
                    header: tCommon("table.decision"),
                    render: (row) =>
                      row.kind === "decision" ? (
                        <Badge variant={ACTION_VARIANT[row.decision.action] ?? "default"}>{titleCase(row.decision.action)}</Badge>
                      ) : (
                        <Badge variant="accent">{t("todaysActions.suggestedBuy")}</Badge>
                      ),
                  },
                  {
                    key: "weight",
                    header: t("todaysActions.targetWeight"),
                    align: "right",
                    render: (row) => (
                      <span className="num">{formatPercent(row.kind === "decision" ? row.decision.target_weight : row.position.weight)}</span>
                    ),
                  },
                  {
                    key: "confidence",
                    header: tCommon("table.confidence"),
                    render: (row) => (
                      <Meter
                        value={row.kind === "decision" ? row.decision.confidence : row.position.confidence}
                        label={formatPercent(row.kind === "decision" ? row.decision.confidence : row.position.confidence)}
                      />
                    ),
                  },
                  {
                    key: "horizon",
                    header: t("todaysActions.holdingPeriod"),
                    render: () => label("horizon", "investment"),
                  },
                  {
                    key: "thesis",
                    header: t("todaysActions.thesis"),
                    render: (row) => (
                      <span className={styles.thesisCell}>
                        {row.kind === "decision"
                          ? row.decision.investment_thesis
                          : row.recommendation?.explanation.why_this_stock ?? ""}
                      </span>
                    ),
                  },
                  {
                    key: "reasons",
                    header: t("todaysActions.topReasons"),
                    render: (row) => {
                      const reasons =
                        row.kind === "decision"
                          ? row.decision.explanation.supporting_evidence
                          : row.recommendation?.explanation.supporting_evidence ?? [];
                      if (reasons.length === 0) return <span className={styles.riskCell}>—</span>;
                      return (
                        <ul className={styles.reasonsList}>
                          {reasons.slice(0, 3).map((r, i) => (
                            <li key={i}>{r}</li>
                          ))}
                        </ul>
                      );
                    },
                  },
                  {
                    key: "risk",
                    header: t("todaysActions.largestRisk"),
                    render: (row) => (
                      <span className={styles.riskCell}>
                        {row.kind === "decision"
                          ? row.decision.key_risks[0] ?? "—"
                          : row.recommendation?.explanation.why_not_others ?? t("todaysActions.notAssessed")}
                      </span>
                    ),
                  },
                ]}
              />
            </>
          )}
        </Card>

        <Card title={t("capitalAllocation.recycling.title")} subtitle={t("capitalAllocation.recycling.description")}>
          {!displayedCapitalPlan && <EmptyState title={needsHoldingsCardTitle} />}
          {displayedCapitalPlan && displayedCapitalPlan.capital_recycled.length === 0 && (
            <EmptyState title={t("capitalAllocation.recycling.emptyTitle")} detail={t("capitalAllocation.recycling.emptyDetail")} />
          )}
          {displayedCapitalPlan && displayedCapitalPlan.capital_recycled.length > 0 && (
            <ul className={styles.flowList}>
              {displayedCapitalPlan.capital_recycled.map((f, i) => (
                <li key={i}>
                  <span className="num">{f.from_ticker}</span> → <span className="num">{f.to_ticker}</span>:{" "}
                  <span className="num">{formatPercent(f.amount)}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title={t("capitalAllocation.released.title")} subtitle={t("capitalAllocation.released.description")}>
          {!displayedCapitalPlan && <EmptyState title={needsHoldingsCardTitle} />}
          {displayedCapitalPlan && displayedCapitalPlan.capital_released_today.length === 0 && (
            <EmptyState title={t("capitalAllocation.released.emptyTitle")} detail={t("capitalAllocation.released.emptyDetail")} />
          )}
          {displayedCapitalPlan && displayedCapitalPlan.capital_released_today.length > 0 && (
            <ul className={styles.flowList}>
              {displayedCapitalPlan.capital_released_today.map((r) => (
                <li key={r.ticker}>
                  <span className="num">{r.ticker}</span>: <span className="num">{formatPercent(r.amount)}</span> →{" "}
                  {formatCapitalSources(r.destinations)}
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title={t("capitalAllocation.bestNew.title")} subtitle={t("capitalAllocation.bestNew.description")}>
          {displayedCapitalPlan ? (
            displayedCapitalPlan.best_new_opportunities.length === 0 ? (
              <EmptyState title={t("capitalAllocation.bestNew.emptyTitle")} detail={t("capitalAllocation.bestNew.emptyDetail")} />
            ) : (
              <ul className={styles.rankList}>
                {displayedCapitalPlan.best_new_opportunities.map((r) => (
                  <li key={r.ticker}>
                    <span className="num">#{r.rank}</span> <span className={`${styles.tickerCode} num`}>{r.ticker}</span> —{" "}
                    {t("capitalAllocation.bestNew.score", { score: r.opportunity_score.toFixed(3) })}
                  </li>
                ))}
              </ul>
            )
          ) : (investmentCases.data?.portfolio?.positions ?? []).filter((p) => p.weight > 0).length === 0 ? (
            <EmptyState title={t("capitalAllocation.bestNew.emptyTitle")} detail={t("capitalAllocation.bestNew.emptyDetail")} />
          ) : (
            <ul className={styles.rankList}>
              {(investmentCases.data?.portfolio?.positions ?? [])
                .filter((p) => p.weight > 0)
                .slice(0, 5)
                .map((p, i) => (
                  <li key={p.ticker}>
                    <span className="num">#{i + 1}</span> <span className={`${styles.tickerCode} num`}>{p.ticker}</span> —{" "}
                    {t("capitalAllocation.bestNew.modelPortfolioBadge")}
                  </li>
                ))}
            </ul>
          )}
        </Card>

        <Card title={t("capitalAllocation.highestCost.title")} subtitle={t("capitalAllocation.highestCost.description")}>
          {!displayedCapitalPlan && <EmptyState title={needsHoldingsCardTitle} />}
          {displayedCapitalPlan && displayedCapitalPlan.highest_opportunity_cost.length === 0 && (
            <EmptyState title={t("capitalAllocation.highestCost.emptyTitle")} detail={t("capitalAllocation.highestCost.emptyDetail")} />
          )}
          {displayedCapitalPlan && displayedCapitalPlan.highest_opportunity_cost.length > 0 && (
            <ul className={styles.rankList}>
              {displayedCapitalPlan.highest_opportunity_cost.map((h) => (
                <li key={h.ticker}>
                  <span className={`${styles.tickerCode} num`}>{h.ticker}</span>{" "}
                  {t("capitalAllocation.bestNew.score", { score: h.opportunity_score.toFixed(3) })} — {h.reason}
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title={t("capitalAllocation.allocationChanges.title")} subtitle={t("capitalAllocation.allocationChanges.description")}>
          {!displayedCapitalPlan && <EmptyState title={needsHoldingsCardTitle} />}
          {displayedCapitalPlan && displayedCapitalPlan.allocation_changes.length === 0 && (
            <EmptyState title={t("capitalAllocation.allocationChanges.emptyTitle")} detail={t("capitalAllocation.allocationChanges.emptyDetail")} />
          )}
          {displayedCapitalPlan && displayedCapitalPlan.allocation_changes.length > 0 && (
            <DataTable
              rows={displayedCapitalPlan.allocation_changes}
              getRowKey={(c) => c.ticker}
              onRowClick={(c) => navigate(`/cases/${c.ticker}`)}
              columns={[
                {
                  key: "ticker",
                  header: tCommon("table.ticker"),
                  render: (c) => <span className={`${styles.tickerCode} num`}>{c.ticker}</span>,
                },
                {
                  key: "decision",
                  header: tCommon("table.decision"),
                  render: (c) => <Badge variant={ACTION_VARIANT[c.action] ?? "default"}>{titleCase(c.action)}</Badge>,
                },
                {
                  key: "from",
                  header: t("capitalAllocation.allocationChanges.from"),
                  align: "right",
                  render: (c) => <span className="num">{formatPercent(c.current_weight)}</span>,
                },
                {
                  key: "to",
                  header: t("capitalAllocation.allocationChanges.to"),
                  align: "right",
                  render: (c) => <span className="num">{formatPercent(c.target_weight)}</span>,
                },
                {
                  key: "delta",
                  header: t("capitalAllocation.allocationChanges.delta"),
                  align: "right",
                  render: (c) => <span className="num">{formatSignedPercent(c.capital_delta)}</span>,
                },
              ]}
            />
          )}
        </Card>

        <Card title={t("capitalAllocation.cashWaiting.title")} subtitle={t("capitalAllocation.cashWaiting.description")}>
          {!displayedCapitalPlan && <EmptyState title={needsHoldingsCardTitle} />}
          {displayedCapitalPlan && (
            <>
              <div className={styles.statGrid}>
                <StatTile label={t("capitalAllocation.cashWaiting.before")} value={formatPercent(displayedCapitalPlan.cash_waiting.idle_cash_before)} />
                <StatTile label={t("capitalAllocation.cashWaiting.after")} value={formatPercent(displayedCapitalPlan.cash_waiting.idle_cash_after)} />
              </div>
              <p className={styles.actionsSourceNote}>{displayedCapitalPlan.cash_waiting.reason}</p>
            </>
          )}
        </Card>
      </Section>

      <Section title={t("portfolioSummary.title")} description={t("portfolioSummary.description")}>
        {portfolioSummary.loading && <LoadingState rows={1} />}
        {portfolioSummary.error && <ErrorState detail={portfolioSummary.error.message} onRetry={portfolioSummary.reload} />}
        {!portfolioSummary.loading && !portfolioSummary.error && !portfolioSummary.data && (
          <EmptyState title={t("portfolioSummary.emptyTitle")} detail={t("portfolioSummary.emptyDetail")} />
        )}
        {portfolioSummary.data && (
          <>
            <p className={styles.actionsSourceNote}>
              {portfolioSummary.data.is_live_portfolio ? t("portfolioSummary.sourceLive") : t("portfolioSummary.sourceModelPortfolio")}
            </p>
            <div className={styles.statGrid}>
              <StatTile label={t("portfolioSummary.cash")} value={formatPercent(portfolioSummary.data.cash_weight)} />
              <StatTile label={t("portfolioSummary.invested")} value={formatPercent(portfolioSummary.data.invested_weight)} />
              <StatTile
                label={t("portfolioSummary.expectedReturn")}
                value={portfolioSummary.data.expected_return != null ? formatSignedPercent(portfolioSummary.data.expected_return) : "—"}
              />
              <StatTile
                label={t("portfolioSummary.expectedDownside")}
                value={portfolioSummary.data.expected_risk != null ? formatPercent(portfolioSummary.data.expected_risk) : "—"}
              />
              <StatTile
                label={t("portfolioSummary.diversification")}
                value={label("concentrationStatus", portfolioSummary.data.concentration.status)}
              />
              <StatTile label={t("portfolioSummary.positions")} value={portfolioSummary.data.position_count} />
            </div>
            {portfolioSummary.data.sector_exposures.length > 0 && (
              <div className={styles.sectorList}>
                {portfolioSummary.data.sector_exposures.map((s) => (
                  <div key={s.sector} className={styles.sectorRow}>
                    <span className={styles.sectorName}>{s.sector}</span>
                    <Meter value={s.weight} label={formatPercent(s.weight)} />
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </Section>

      <Section title={t("warnings.title")} description={t("warnings.description")}>
        {warnings.loading && <LoadingState rows={2} />}
        {warnings.error && <ErrorState detail={warnings.error.message} onRetry={warnings.reload} />}
        {!warnings.loading && !warnings.error && (!warnings.data || warnings.data.warnings.length === 0) && (
          <EmptyState title={t("warnings.emptyTitle")} detail={t("warnings.emptyDetail")} />
        )}
        {warnings.data && warnings.data.warnings.length > 0 && (
          <div className={styles.warningsList}>
            {warnings.data.warnings.map((w, i) => (
              <div key={i} className={`${styles.warningItem} ${styles[WARNING_VARIANT[w.severity]]}`}>
                <div className={styles.warningHead}>
                  <span className={styles.warningTitle}>{w.title}</span>
                  <Badge variant={w.severity === "critical" ? "negative" : w.severity === "warning" ? "warning" : "neutral"}>
                    {label("warningCategory", w.category)}
                  </Badge>
                </div>
                <span className={styles.warningDetail}>{w.detail}</span>
              </div>
            ))}
          </div>
        )}
      </Section>

      <Section title="الاقتصاد الكلي ومركز القرار" description="بيانات حقيقية من Yahoo Finance وWorld Bank — تُحدَّث يومياً وتدخل في صناعة قرار الشراء والبيع">
        {macroSnapshot.loading && <LoadingState rows={2} />}
        {macroSnapshot.error && <ErrorState detail={macroSnapshot.error.message} onRetry={macroSnapshot.reload} />}
        {!macroSnapshot.loading && !macroSnapshot.error && !macroSnapshot.data && (
          <EmptyState
            title="بيانات الاقتصاد الكلي غير متاحة حاليًا"
            detail="يتم تحديث بيانات Yahoo Finance وWorld Bank تلقائيًا مع كل تشغيل إنتاجي. لن تُستخدم قيم تقديرية؛ أعد المحاولة بعد اكتمال التحديث أو راجع صحة المصادر في Source Intelligence."
          />
        )}
        {macroSnapshot.data && (
          <>
          <div className={styles.macroCardSrc} style={{ marginBottom: "var(--space-3)" }}>
            آخر snapshot موثّق: {macroSnapshot.data.as_of} · المصادر: Yahoo Finance وWorld Bank
          </div>
          <div className={styles.macroGrid}>
            {/* EGP/USD */}
            <div className={styles.macroCard}>
              <div className={styles.macroCardLabel}>سعر الصرف</div>
              <div className={styles.macroCardValue}>
                {macroSnapshot.data.egp_usd.current != null
                  ? `${(1 / macroSnapshot.data.egp_usd.current).toFixed(2)} جنيه / دولار`
                  : "—"}
              </div>
              {macroSnapshot.data.egp_usd.change_30d_pct != null && (
                <div className={`${styles.macroCardChange} ${
                  macroSnapshot.data.egp_usd.change_30d_pct > 0 ? styles.macroPositive : styles.macroNegative
                }`}>
                  {macroSnapshot.data.egp_usd.change_30d_pct > 0 ? "↑" : "↓"}
                  {Math.abs(macroSnapshot.data.egp_usd.change_30d_pct).toFixed(1)}% (30 يوم)
                </div>
              )}
              <div className={styles.macroCardSrc}>Yahoo Finance · {macroSnapshot.data.egp_usd.series_length} قراءة</div>
            </div>

            {/* Brent Oil */}
            {macroSnapshot.data.brent_usd.current != null && (
              <div className={styles.macroCard}>
                <div className={styles.macroCardLabel}>خام برنت</div>
                <div className={styles.macroCardValue}>
                  ${macroSnapshot.data.brent_usd.current.toFixed(1)} / برميل
                </div>
                <div className={styles.macroCardChange}>
                  {macroSnapshot.data.brent_usd.current > 90
                    ? "مرتفع — يدعم AMOC وEGCH"
                    : macroSnapshot.data.brent_usd.current < 70
                    ? "منخفض — يضغط على قطاع الطاقة"
                    : "معتدل — تأثير محدود"}
                </div>
                <div className={styles.macroCardSrc}>Yahoo Finance · {macroSnapshot.data.brent_usd.date}</div>
              </div>
            )}

            {/* CPI Inflation */}
            <div className={styles.macroCard}>
              <div className={styles.macroCardLabel}>التضخم</div>
              <div className={styles.macroCardValue}>
                {macroSnapshot.data.cpi_inflation_pct.current != null
                  ? `${macroSnapshot.data.cpi_inflation_pct.current.toFixed(1)}%`
                  : "غير متاح"}
              </div>
              <div className={`${styles.macroCardChange} ${
                macroSnapshot.data.cpi_inflation_pct.regime === "very_high" || macroSnapshot.data.cpi_inflation_pct.regime === "high"
                  ? styles.macroNegative
                  : macroSnapshot.data.cpi_inflation_pct.regime === "low"
                  ? styles.macroPositive
                  : ""
              }`}>
                {macroSnapshot.data.cpi_inflation_pct.regime === "very_high" && "مرتفع جداً — يضغط العوائد الحقيقية"}
                {macroSnapshot.data.cpi_inflation_pct.regime === "high" && "مرتفع — راقب قرارات CBE"}
                {macroSnapshot.data.cpi_inflation_pct.regime === "moderate" && "معتدل"}
                {macroSnapshot.data.cpi_inflation_pct.regime === "low" && "منخفض — بيئة داعمة"}
                {macroSnapshot.data.cpi_inflation_pct.regime === "unknown" && "يتطلب تحديث البيانات"}
              </div>
              <div className={styles.macroCardSrc}>World Bank · {macroSnapshot.data.cpi_inflation_pct.date ?? "N/A"}</div>
            </div>

            {/* GDP Growth */}
            {macroSnapshot.data.gdp_growth_pct.current != null && (
              <div className={styles.macroCard}>
                <div className={styles.macroCardLabel}>نمو الناتج المحلي</div>
                <div className={styles.macroCardValue}>
                  {macroSnapshot.data.gdp_growth_pct.current.toFixed(1)}%
                </div>
                <div className={`${styles.macroCardChange} ${
                  macroSnapshot.data.gdp_growth_pct.current > 4 ? styles.macroPositive : ""
                }`}>
                  {macroSnapshot.data.gdp_growth_pct.current > 5
                    ? "نمو قوي — داعم لتوسع الأرباح"
                    : macroSnapshot.data.gdp_growth_pct.current > 3
                    ? "نمو معقول"
                    : "نمو بطيء"}
                </div>
                <div className={styles.macroCardSrc}>World Bank · {macroSnapshot.data.gdp_growth_pct.date?.slice(0, 4)}</div>
              </div>
            )}
          </div>
          </>
        )}

        {/* Decision Implications */}
        {macroSnapshot.data && macroSnapshot.data.decision_implications.length > 0 && (
          <div className={styles.macroImplications}>
            <div className={styles.macroImplicationsTitle}>تأثير الاقتصاد الكلي على قرارات الاستثمار</div>
            {macroSnapshot.data.decision_implications.map((imp, i) => (
              <div key={i} className={styles.macroImplicationRow}>
                <span className={styles.macroImplicationBullet}>◆</span>
                <span>{imp}</span>
              </div>
            ))}
          </div>
        )}
      </Section>

      <Section title={t("committeeSummary.title")} description={t("committeeSummary.description")}>
        {!systemMaturity.loading && !systemMaturity.error && systemMaturity.data && (
          <div className={styles.systemMaturityRow}>
            <span className={styles.systemMaturityLabel}>{t("committeeSummary.systemMaturity")}</span>
            <Badge variant={SYSTEM_MATURITY_VARIANT[systemMaturity.data.level] ?? "neutral"}>
              {label("systemMaturity", systemMaturity.data.level)}
            </Badge>
            <span className={styles.systemMaturityRationale}>{systemMaturity.data.rationale}</span>
          </div>
        )}
        {committeeSummary.loading && <LoadingState rows={2} />}
        {committeeSummary.error && <ErrorState detail={committeeSummary.error.message} onRetry={committeeSummary.reload} />}
        {!committeeSummary.loading && !committeeSummary.error && !committeeSummary.data && (
          <EmptyState title={t("committeeSummary.emptyTitle")} detail={t("committeeSummary.emptyDetail")} />
        )}
        {committeeSummary.data && (
          <div className={styles.committeeGrid}>
            {committeeSummary.data.opinions.map((o) => (
              <div
                key={o.committee}
                className={`${styles.committeeCard} ${o.committee === "chief_investment_officer" ? styles.committeeCardCio : ""}`}
              >
                <div className={styles.committeeName}>{label("committee", o.committee)}</div>
                <Badge variant={COMMITTEE_STANCE_VARIANT[o.stance] ?? "neutral"}>{label("committeeStance", o.stance)}</Badge>
                <p className={styles.committeeNote}>{o.note}</p>
              </div>
            ))}
          </div>
        )}
      </Section>
    </>
  );
}
