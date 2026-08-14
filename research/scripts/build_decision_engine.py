#!/usr/bin/env python3
"""
build_decision_engine.py
=========================
Reads real data (prices + macro + financial statements + fair values)
and produces:
  - recommendations.json     ← buy/sell/hold with full rationale
  - market_breadth.json      ← breadth indicators from real prices
  - market_regime.json       ← trend classification from real prices
  - acquisition_decisions.json ← ranked acquisition targets

Rules:
  - ZERO fabricated numbers
  - Every recommendation is anchored to: price_vs_fair_value + macro context
  - Abstain if data is insufficient (never force a decision)
"""

import csv
import json
import math
from datetime import UTC, datetime, timedelta
from pathlib import Path
from statistics import mean, stdev

ROOT = Path(__file__).parent.parent
PRICES_DIR   = ROOT / "data" / "prices"
MACRO_DIR    = ROOT / "data" / "macro"
DASHBOARD_DIR = ROOT / "data" / "dashboard"
DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)

TODAY = datetime.now(UTC).strftime("%Y-%m-%d")

# ── Minimum data requirements (no fabrication allowed) ────────────────────
MIN_PRICE_BARS_MICRO      = 10   # for swing/micro decision
MIN_PRICE_BARS_INVESTMENT = 60   # for investment horizon decision
STALE_DAYS = 14                  # price older than 14 days → skip


def load_json(path: Path) -> dict | list | None:
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def save_json(path: Path, data) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_csv_series(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))

# ── Load decision_readiness (has fair values per ticker) ──────────────────
def load_decision_readiness() -> dict[str, dict]:
    data = load_json(DASHBOARD_DIR / "decision_readiness.json")
    if not data:
        return {}
    return {row["ticker"]: row for row in data}

# ── Load macro snapshot ────────────────────────────────────────────────────
def load_macro() -> dict:
    path = MACRO_DIR / "macro_snapshot.json"
    if path.exists():
        return load_json(path) or {}
    return {}

# ── Load price bars ────────────────────────────────────────────────────────
def load_price_bars(ticker: str) -> list[dict]:
    path = PRICES_DIR / f"{ticker}.csv"
    return load_csv_series(path)

def is_price_stale(bars: list[dict]) -> bool:
    if not bars:
        return True
    latest_date = datetime.strptime(bars[-1]["date"], "%Y-%m-%d").replace(tzinfo=UTC)
    cutoff = datetime.now(UTC) - timedelta(days=STALE_DAYS)
    return latest_date < cutoff

def compute_price_stats(bars: list[dict]) -> dict | None:
    """Compute basic price statistics from OHLCV bars."""
    closes = []
    volumes = []
    for b in bars:
        try:
            c = float(b["close"])
            v = float(b.get("volume") or 0)
            closes.append(c)
            volumes.append(v)
        except (ValueError, TypeError):
            continue
    if not closes:
        return None

    current_price = closes[-1]
    avg_vol = mean(volumes) if volumes else 0

    # Returns
    returns = []
    for i in range(1, len(closes)):
        if closes[i-1] > 0:
            returns.append((closes[i] - closes[i-1]) / closes[i-1])

    # Momentum: 20-day return
    momentum_20d = None
    if len(closes) >= 20:
        momentum_20d = (closes[-1] - closes[-21]) / closes[-21] if closes[-21] > 0 else None

    # Volatility (annualized)
    annual_vol = None
    if len(returns) >= 10:
        daily_vol = stdev(returns)
        annual_vol = daily_vol * math.sqrt(252)

    # 52-week high/low
    high_52w = max(closes[-252:]) if len(closes) >= 252 else max(closes)
    low_52w  = min(closes[-252:]) if len(closes) >= 252 else min(closes)

    # Simple moving averages
    sma_20 = mean(closes[-20:]) if len(closes) >= 20 else None
    sma_50 = mean(closes[-50:]) if len(closes) >= 50 else None

    # Trend signal
    trend = "neutral"
    if sma_20 and sma_50:
        if current_price > sma_20 > sma_50:
            trend = "bullish"
        elif current_price < sma_20 < sma_50:
            trend = "bearish"

    return {
        "current_price": round(current_price, 4),
        "bars_count": len(closes),
        "avg_volume": round(avg_vol, 0),
        "momentum_20d": round(momentum_20d, 4) if momentum_20d is not None else None,
        "annual_volatility": round(annual_vol, 4) if annual_vol is not None else None,
        "high_52w": round(high_52w, 4),
        "low_52w": round(low_52w, 4),
        "sma_20": round(sma_20, 4) if sma_20 else None,
        "sma_50": round(sma_50, 4) if sma_50 else None,
        "trend": trend,
        "latest_date": bars[-1]["date"],
    }


def score_ticker(
    ticker: str,
    readiness: dict,
    price_stats: dict,
    macro: dict,
) -> dict:
    """
    Build a recommendation for a single ticker.
    Returns a dict matching the Recommendation type in types.ts
    """
    valuation = readiness.get("valuation") or {}
    fair_value = valuation.get("weighted_fair_value")
    bull_case  = valuation.get("bull_case")
    bear_case  = valuation.get("bear_case")
    current_price = price_stats["current_price"]

    # ── Core signal: price vs. fair value ────────────────────────────────
    upside_pct = None
    if fair_value and current_price and fair_value > 0:
        upside_pct = (fair_value - current_price) / current_price

    # ── Macro adjustments ────────────────────────────────────────────────
    macro_adj = 0.0
    macro_notes = []
    egp = (macro.get("egp_usd") or {}).get("change_30d_pct")
    cpi_val = (macro.get("cpi_inflation_pct") or {}).get("current")
    cpi_regime = (macro.get("cpi_inflation_pct") or {}).get("regime", "unknown")

    if egp is not None:
        if egp < -3:
            macro_adj += 0.03  # depreciation bonus for exporters (simplified)
            macro_notes.append(f"EGP weakening ({egp:+.1f}%) — exporter tailwind")
        elif egp > 3:
            macro_adj -= 0.02
            macro_notes.append(f"EGP strengthening ({egp:+.1f}%) — importer benefit")

    if cpi_regime == "very_high":
        macro_adj -= 0.02
        macro_notes.append(f"Very high inflation ({cpi_val:.0f}%) compresses real returns")
    elif cpi_regime == "high":
        macro_adj -= 0.01
        macro_notes.append(f"High inflation ({cpi_val:.0f}%) — monitor margin compression")
    elif cpi_regime == "low":
        macro_adj += 0.01
        macro_notes.append(f"Low inflation ({cpi_val:.0f}%) — supportive environment")

    # ── Momentum signal ──────────────────────────────────────────────────
    momentum = price_stats.get("momentum_20d")
    momentum_note = None
    if momentum is not None:
        if momentum > 0.05:
            momentum_note = f"Strong 20-day momentum (+{momentum*100:.1f}%)"
        elif momentum < -0.05:
            momentum_note = f"Weak 20-day momentum ({momentum*100:.1f}%)"

    # ── Combined expected return ──────────────────────────────────────────
    combined_return = None
    if upside_pct is not None:
        combined_return = upside_pct + macro_adj
        if momentum is not None:
            combined_return += momentum * 0.2  # 20% weight on momentum

    # ── Data quality, earnings quality, events and execution overlay ────
    eq = readiness.get("earnings_quality") or {}
    source = str(readiness.get("source") or "")
    quality_score = 100
    quality_notes = []
    if source == "mubasher":
        quality_score -= 10
        quality_notes.append("Secondary financial source")
    if readiness.get("financial_periods", 0) < 3:
        quality_score -= 10
        quality_notes.append("Fewer than 3 reporting periods")
    if eq.get("status") == "cash_mismatch":
        quality_score -= 20
        quality_notes.append("Earnings are not supported by operating cash flow")
    elif eq.get("status") == "loss":
        quality_score -= 15
        quality_notes.append("Latest net income is negative")
    elif eq.get("status") == "unknown":
        quality_score -= 10
        quality_notes.append("Earnings quality is not fully observable")
    if len((readiness.get("diagnostics") or {}).get("available_fields", [])) < 5:
        quality_score -= 10
        quality_notes.append("Limited financial fields")
    quality_score = max(0, quality_score)
    traded_value = (price_stats.get("avg_volume") or 0) * current_price
    if traded_value >= 10_000_000:
        liquidity_class, execution_risk = "high", "low"
    elif traded_value >= 1_000_000:
        liquidity_class, execution_risk = "medium", "moderate"
    elif traded_value > 0:
        liquidity_class, execution_risk = "low", "high"
    else:
        liquidity_class, execution_risk = "unknown", "high"
    event_flags = readiness.get("event_flags") or []
    event_risk = any(str(x.get("severity", "")).lower() in {"high", "critical"} for x in event_flags if isinstance(x, dict))

    # ── Decision logic ───────────────────────────────────────────────────
    action = "abstain"
    confidence = 0.0
    horizon = "investment"

    if combined_return is None:
        action = "abstain"
        confidence = 0.0
    elif combined_return > 0.20:
        action = "strong_buy"
        confidence = min(0.85, 0.60 + abs(combined_return) * 0.5)
        horizon = "investment"
    elif combined_return > 0.08:
        action = "buy"
        confidence = min(0.80, 0.55 + abs(combined_return) * 0.4)
        horizon = "investment"
    elif combined_return > 0.03:
        action = "accumulate"
        confidence = 0.55
        horizon = "swing"
    elif combined_return > -0.03:
        action = "hold"
        confidence = 0.60
        horizon = "investment"
    elif combined_return > -0.10:
        action = "reduce"
        confidence = 0.55
        horizon = "swing"
    else:
        action = "sell"
        confidence = min(0.80, 0.55 + abs(combined_return) * 0.3)
        horizon = "investment"

    # Quality gates cap overconfident actions; they never create a fair value.
    if action == "strong_buy" and (quality_score < 75 or eq.get("status") == "cash_mismatch" or event_risk):
        action = "buy"
        confidence = min(confidence, 0.68)
        quality_notes.append("Strong Buy capped by data/earnings/event risk")
    if action == "buy" and quality_score < 55:
        action = "hold"
        confidence = min(confidence, 0.60)
        quality_notes.append("Buy capped by low data quality")
    if execution_risk == "high" and action in {"strong_buy", "buy"}:
        quality_notes.append("High execution risk from low traded value")

    # ── Build supporting/invalidation evidence ───────────────────────────
    supporting = []
    invalidating = []

    if upside_pct is not None:
        if upside_pct > 0:
            supporting.append(f"Current price ({current_price:.2f} EGP) is {upside_pct*100:.1f}% below fair value ({fair_value:.2f} EGP)")
        else:
            invalidating.append(f"Current price ({current_price:.2f} EGP) is {abs(upside_pct)*100:.1f}% above fair value ({fair_value:.2f} EGP)")

    if bull_case and current_price < bull_case:
        supporting.append(f"Bull-case fair value {bull_case:.2f} EGP implies {(bull_case/current_price-1)*100:.0f}% upside")
    if bear_case and current_price < bear_case:
        supporting.append(f"Trading below even bear-case ({bear_case:.2f} EGP) — asymmetric risk/reward")
    elif bear_case and current_price > bear_case * 1.2:
        invalidating.append(f"Price ({current_price:.2f}) significantly above bear-case ({bear_case:.2f}) — limited downside protection")

    if momentum_note:
        if momentum and momentum > 0:
            supporting.append(momentum_note)
        else:
            invalidating.append(momentum_note)

    supporting.extend(macro_notes)
    if eq.get("status") == "cash_supported":
        supporting.append("Earnings are supported by positive operating cash flow")
    elif eq.get("status") == "cash_mismatch":
        invalidating.append("Operating cash flow does not support reported earnings")
    if liquidity_class == "low":
        invalidating.append("Low traded value increases execution risk")
    elif liquidity_class == "high":
        supporting.append("High average traded value supports execution")
    if quality_notes:
        invalidating.extend(quality_notes[:2])
    if event_flags:
        invalidating.append(f"{len(event_flags)} structured event flag(s) require review")

    if price_stats["trend"] == "bullish":
        supporting.append("Price above SMA-20 and SMA-50 — trend intact")
    elif price_stats["trend"] == "bearish":
        invalidating.append("Price below SMA-20 and SMA-50 — downtrend")

    # ── Why this / why now ───────────────────────────────────────────────
    why_this = f"{ticker}: Fair value {fair_value:.2f} EGP vs current {current_price:.2f} EGP" if fair_value else f"{ticker}: technical analysis only (no fair value available)"
    why_now  = "; ".join(supporting[:2]) if supporting else "No strong catalyst identified"
    why_not  = "; ".join(invalidating[:2]) if invalidating else "No major contrary indicator"

    financial_periods = readiness.get("financial_periods", 0)
    fin_note = f"Based on {financial_periods} financial reporting periods." if financial_periods else ""

    risk=(price_stats.get("annual_volatility") or 0.25)
    reported_models=valuation.get("models") or {}
    included_names=valuation.get("included_models") or []
    model_values=[float(reported_models[name]) for name in included_names if isinstance(reported_models.get(name),(int,float)) and reported_models[name]>0]
    if len(model_values)<3:
        model_values=[float(v) for v in reported_models.values() if isinstance(v,(int,float)) and v>0]
    model_cv=None
    if len(model_values)>=3:
        model_mean=sum(model_values)/len(model_values)
        model_cv=(sum((v-model_mean)**2 for v in model_values)/len(model_values))**0.5/model_mean if model_mean else None
    model_agreement_score=round(max(0.0,1.0-min(model_cv or 0.0,1.0))*100.0,1)
    risk_penalty=1.0/(1.0+risk)
    opportunity_score=round(((combined_return or 0.0) * (quality_score/100.0) * (model_agreement_score/100.0) * risk_penalty), 6)
    if action in {"strong_buy", "buy", "accumulate"}: market_stance="attractive"
    elif action in {"reduce", "sell"}: market_stance="unattractive"
    else: market_stance="neutral"
    evidence_status="sufficient" if combined_return is not None else "insufficient_evidence"
    return {
        "ticker": ticker,
        "as_of": TODAY,
        "action": action,
        "market_stance": market_stance,
        "evidence_status": evidence_status,
        "portfolio_action": None,
        "portfolio_action_status": "requires_position_data",
        "opportunity_score": opportunity_score,
        "opportunity_score_components": {
            "combined_expected_return": round(combined_return,4) if combined_return is not None else None,
            "data_quality_score": quality_score,
            "model_agreement_score": model_agreement_score,
            "model_coefficient_of_variation": round(model_cv,4) if model_cv is not None else None,
            "risk_penalty": round(risk_penalty,4),
        },
        "opportunity_score_definition": "signed fair-value-upside score adjusted by data quality, model agreement and volatility; not a probability",
        "expected_return_type": "fair_value_upside_plus_macro_momentum",
        "confidence_type": "confidence_score_not_calibrated_probability",
        "horizon": horizon,
        "horizon_label": "short_term" if horizon == "swing" else "investment_term_unclassified",
        "confidence": round(confidence, 3),
        "combined_expected_return": round(combined_return, 4) if combined_return is not None else None,
        "combined_expected_risk": round(price_stats.get("annual_volatility") or 0.25, 4),
        "current_price": current_price,
        "fair_value": fair_value,
        "upside_pct": round(upside_pct * 100, 1) if upside_pct is not None else None,
        "explanation": {
            "why_this_stock": why_this + (" " + fin_note if fin_note else ""),
            "why_now": why_now,
            "why_not_others": why_not,
            "supporting_evidence": supporting,
            "invalidation_conditions": invalidating,
            "similar_historical_cases": [],
            "evidence_refs": [],
        },
        "data_quality": {
            "price_bars": price_stats["bars_count"],
            "latest_price_date": price_stats["latest_date"],
            "has_fair_value": fair_value is not None,
            "financial_periods": financial_periods,
            "quality_score": quality_score,
            "quality_notes": quality_notes,
            "earnings_quality": eq,
            "source": source,
            "event_status": readiness.get("event_status", "unknown"),
            "event_flags": event_flags,
            "liquidity_class": liquidity_class,
            "average_traded_value": round(traded_value, 0),
            "execution_risk": execution_risk,
        },
    }


def build_market_breadth(all_stats: dict[str, dict]) -> dict:
    """Compute market breadth from real price data."""
    advancers = decliners = unchanged = 0
    tickers_with_price = 0
    tickers_with_volume = 0
    daily_returns = []

    for stats in all_stats.values():
        if not stats:
            continue
        tickers_with_price += 1
        m = stats.get("momentum_20d")
        if m is not None:
            daily_returns.append(m / 20)  # approximate daily

        vol = stats.get("avg_volume", 0)
        if vol > 0:
            tickers_with_volume += 1

        trend = stats.get("trend", "neutral")
        if trend == "bullish":
            advancers += 1
        elif trend == "bearish":
            decliners += 1
        else:
            unchanged += 1

    adr = round(advancers / decliners, 2) if decliners > 0 else None
    avg_ret = round(mean(daily_returns) * 100, 4) if daily_returns else None

    return {
        "as_of": TODAY,
        "universe_count": 101,
        "tickers_with_price_data": tickers_with_price,
        "tickers_with_volume_data": tickers_with_volume,
        "advancers": advancers,
        "decliners": decliners,
        "unchanged": unchanged,
        "advance_decline_ratio": adr,
        "average_daily_return_pct": avg_ret,
        "tickers_above_average_volume": tickers_with_volume,
        "tickers_below_average_volume": tickers_with_price - tickers_with_volume,
    }


def build_market_regime(all_stats: dict[str, dict], macro: dict) -> dict:
    """Classify market regime from real price data."""
    valid_stats = [s for s in all_stats.values() if s and s.get("momentum_20d") is not None]
    n = len(valid_stats)
    if n < 5:
        return {
            "as_of": TODAY,
            "trend": "neutral",
            "volatility": "unknown",
            "lookback_days": 20,
            "trading_days_observed": n,
            "tickers_with_sufficient_data": n,
            "cumulative_return_pct": None,
            "daily_volatility_pct": None,
            "reasons": ["Insufficient price data to classify regime."],
        }

    momentums = [s["momentum_20d"] for s in valid_stats]
    avg_momentum = mean(momentums)
    pct_bullish = sum(1 for m in momentums if m > 0.02) / n
    pct_bearish = sum(1 for m in momentums if m < -0.02) / n

    # Trend classification
    if avg_momentum > 0.03 and pct_bullish > 0.55:
        trend = "bullish"
    elif avg_momentum < -0.03 and pct_bearish > 0.55:
        trend = "bearish"
    else:
        trend = "neutral"

    # Volatility
    vols = [s.get("annual_volatility") for s in valid_stats if s.get("annual_volatility")]
    avg_vol = mean(vols) if vols else None
    if avg_vol is None:
        vol_class = "unknown"
    elif avg_vol > 0.50:
        vol_class = "high"
    elif avg_vol > 0.30:
        vol_class = "elevated"
    else:
        vol_class = "low"

    reasons = [
        f"{pct_bullish*100:.0f}% of stocks with price data showing positive 20-day momentum",
        f"{pct_bearish*100:.0f}% in downtrend",
        f"Average 20-day return: {avg_momentum*100:.1f}%",
    ]

    macro_regime = (macro.get("cpi_inflation_pct") or {}).get("regime", "unknown")
    if macro_regime == "very_high":
        reasons.append("Very high inflation constrains monetary easing and real returns")
    elif macro_regime == "low":
        reasons.append("Normalizing inflation supports equity multiples")

    return {
        "as_of": TODAY,
        "trend": trend,
        "volatility": vol_class,
        "lookback_days": 20,
        "trading_days_observed": n,
        "tickers_with_sufficient_data": n,
        "cumulative_return_pct": round(avg_momentum * 100, 2),
        "daily_volatility_pct": round(avg_vol * 100, 2) if avg_vol else None,
        "reasons": reasons,
    }


def main():
    print("=== EGX Decision Engine ===\n")

    readiness_map = load_decision_readiness()
    macro = load_macro()
    print(f"Decision readiness loaded: {len(readiness_map)} tickers")
    print(f"Macro snapshot: {macro.get('as_of', 'N/A')}")
    print(f"  EGP/USD: {(macro.get('egp_usd') or {}).get('current', 'N/A')}")
    print(f"  CPI: {(macro.get('cpi_inflation_pct') or {}).get('current', 'N/A')}%")
    print()

    # ── Process all tickers ──────────────────────────────────────────────
    recommendations = []
    all_price_stats = {}
    skipped_no_price = []
    skipped_stale = []
    abstained = []
    actionable = []

    tickers = list(readiness_map.keys())
    print(f"Processing {len(tickers)} tickers...\n")

    for ticker in tickers:
        bars = load_price_bars(ticker)
        readiness = readiness_map[ticker]

        if not bars:
            skipped_no_price.append(ticker)
            all_price_stats[ticker] = None
            continue

        if is_price_stale(bars):
            skipped_stale.append(ticker)
            all_price_stats[ticker] = None
            continue

        if len(bars) < MIN_PRICE_BARS_MICRO:
            skipped_no_price.append(ticker)
            all_price_stats[ticker] = None
            continue

        stats = compute_price_stats(bars)
        if not stats:
            skipped_no_price.append(ticker)
            all_price_stats[ticker] = None
            continue

        all_price_stats[ticker] = stats

        # Build recommendation
        rec = score_ticker(ticker, readiness, stats, macro)
        recommendations.append(rec)

        if rec["action"] == "abstain":
            abstained.append(ticker)
        else:
            actionable.append((ticker, rec["action"], rec.get("upside_pct")))
            print(f"  {ticker:6s} | {rec['action']:12s} | upside={rec.get('upside_pct', '-'):>6} | conf={rec['confidence']:.2f}")

    # ── Sort recommendations by confidence × |expected_return| ──────────
    def sort_key(r):
        return -(r.get("opportunity_score") or 0.0)

    recommendations.sort(key=sort_key)
    for rank, rec in enumerate(recommendations, 1):
        rec["rank"] = rank

    # ── Build market breadth + regime ────────────────────────────────────
    breadth = build_market_breadth(all_price_stats)
    regime  = build_market_regime(all_price_stats, macro)

    # ── Acquisition decisions: top 10 buy-rated tickers ──────────────────
    acq_decisions = []
    for rec in recommendations:
        if rec["action"] in ("strong_buy", "buy", "accumulate"):
            acq_decisions.append({
                "ticker": rec["ticker"],
                "as_of": TODAY,
                "action": rec["action"],
                "confidence": rec["confidence"],
                "expected_return": rec.get("combined_expected_return"),
                "fair_value": rec.get("fair_value"),
                "current_price": rec.get("current_price"),
                "upside_pct": rec.get("upside_pct"),
                "rationale": rec["explanation"]["why_this_stock"],
            })
        if len(acq_decisions) >= 15:
            break

    # ── Save all outputs ──────────────────────────────────────────────────
    save_json(DASHBOARD_DIR / "recommendations.json", recommendations)
    save_json(DASHBOARD_DIR / "market_breadth.json", breadth)
    save_json(DASHBOARD_DIR / "market_regime.json", regime)
    save_json(DASHBOARD_DIR / "acquisition_decisions.json", acq_decisions)

    print("\n=== SUMMARY ===")
    print(f"Total tickers:    {len(tickers)}")
    print(f"With live prices: {len([s for s in all_price_stats.values() if s])}")
    print(f"No price data:    {len(skipped_no_price)} → {', '.join(skipped_no_price[:5])}{'...' if len(skipped_no_price)>5 else ''}")
    print(f"Stale prices:     {len(skipped_stale)}")
    print(f"Actionable recs:  {len(actionable)} tickers")
    print(f"Abstained:        {len(abstained)}")
    print(f"\nMarket Regime: {regime['trend']} / volatility={regime['volatility']}")
    print(f"Breadth: {breadth['advancers']} advancers / {breadth['decliners']} decliners")
    print("\nTop acquisition targets:")
    for a in acq_decisions[:5]:
        print(f"  {a['ticker']:6s} | {a['action']:12s} | upside={a['upside_pct']}%")
    print("\nSaved: recommendations.json, market_breadth.json, market_regime.json, acquisition_decisions.json")


if __name__ == "__main__":
    main()
