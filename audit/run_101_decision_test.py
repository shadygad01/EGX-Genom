from __future__ import annotations
import csv,json,sys
from collections import Counter
from datetime import datetime,UTC
from pathlib import Path
sys.path.insert(0,'/home/ubuntu/EGX-Genom/research/scripts')
sys.path.insert(0,'/home/ubuntu/EGX-Genom/research/src')
import build_decision_engine as engine

ROOT=Path('/home/ubuntu/EGX-Genom'); OUT=ROOT/'audit'/'decision_101'; OUT.mkdir(parents=True,exist_ok=True)
coverage=json.loads((ROOT/'audit'/'combined_101_coverage'/'results.json').read_text())
selected={r['ticker']:r for r in coverage['selected']}
readiness_rows=json.loads((ROOT/'research'/'data'/'dashboard'/'decision_readiness.json').read_text(encoding='utf-8')) if (ROOT/'research'/'data'/'dashboard'/'decision_readiness.json').exists() else []
readiness_by_ticker={r['ticker']:r for r in readiness_rows}
macro=engine.load_macro()
tickers=[]; memberships={}
for p in (ROOT/'research'/'data'/'universe').glob('EGX*.csv'):
    index=p.stem
    with p.open(newline='',encoding='utf-8') as f:
        for r in csv.DictReader(f):
            t=r['ticker'].strip().upper(); tickers.append(t); memberships.setdefault(t,[]).append(index)
tickers=sorted(set(tickers))
rows=[]
for ticker in tickers:
    cov=selected.get(ticker,{})
    bars=engine.load_price_bars(ticker)
    stats=engine.compute_price_stats(bars) if bars and not engine.is_price_stale(bars) and len(bars)>=engine.MIN_PRICE_BARS_MICRO else None
    # Fair value is loaded only from the live FairValueEngine readiness artifact.
    live=readiness_by_ticker.get(ticker,{})
    readiness={'ticker':ticker,'financial_periods':len(cov.get('periods',[])),'valuation':live.get('valuation'),'fair_value_available':bool(live.get('valuation'))}
    if stats:
        rec=engine.score_ticker(ticker,readiness,stats,macro)
        action=rec['action']; reason='missing_fair_value' if action=='abstain' else 'engine_action'
    else:
        action='abstain'
        rec={'ticker':ticker,'action':action,'confidence':0.0,'combined_expected_return':None,'current_price':stats and stats.get('current_price'),'fair_value':None,'upside_pct':None,'data_quality':{'price_bars':len(bars),'has_fair_value':False,'financial_periods':len(cov.get('periods',[]))}}
        reason='missing_or_stale_price'
    rows.append({'ticker':ticker,'indices':sorted(set(memberships.get(ticker,[]))),'coverage_source':cov.get('source'),'financial_line_items':cov.get('line_items',0),'financial_periods':len(cov.get('periods',[])),'price_bars':len(bars),'price_status':'usable' if stats else 'missing_or_stale','action':action,'reason':reason,'confidence':rec.get('confidence',0.0),'current_price':rec.get('current_price'),'fair_value':rec.get('fair_value'),'upside_pct':rec.get('upside_pct'),'combined_expected_return':rec.get('combined_expected_return')})
summary={'as_of':datetime.now(UTC).date().isoformat(),'universe':len(rows),'coverage_101':sum(r['financial_line_items']>0 for r in rows),'action_counts':dict(Counter(r['action'] for r in rows)),'reason_counts':dict(Counter(r['reason'] for r in rows)),'usable_price_count':sum(r['price_status']=='usable' for r in rows),'fair_value_count':sum(r['fair_value'] is not None for r in rows),'note':'No fair values are fabricated; financial coverage alone does not create a valuation.'}
(ROOT/'audit'/'decision_101'/'results.json').write_text(json.dumps({'summary':summary,'rows':rows},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
