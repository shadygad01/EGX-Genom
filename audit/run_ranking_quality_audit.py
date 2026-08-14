from __future__ import annotations
import json
from collections import Counter
from datetime import date
from pathlib import Path
ROOT=Path('/home/ubuntu/EGX-Genom')
D=ROOT/'research/data/dashboard'; OUT=ROOT/'audit/decision_101'
recs=json.loads((D/'recommendations.json').read_text()) if (D/'recommendations.json').exists() else []
readiness=json.loads((D/'decision_readiness.json').read_text()) if (D/'decision_readiness.json').exists() else []
issues=[]
rank_values=[r.get('rank') for r in recs]
if len(recs)!=101: issues.append(f'recommendation_count={len(recs)}')
if sorted(rank_values)!=list(range(1,len(recs)+1)): issues.append('rank_not_permutation')
if any(r.get('confidence_type')!='confidence_score_not_calibrated_probability' for r in recs): issues.append('confidence_contract_violation')
if any('expected_return_type' not in r for r in recs): issues.append('expected_return_contract_violation')
if any(r.get('portfolio_action_status')!='requires_position_data' for r in recs): issues.append('portfolio_action_semantics_violation')
if any(r.get('source')=='mock' for r in readiness): issues.append('mock_source_reached_readiness')
latest_periods=[]
for r in readiness:
 fv=r.get('valuation') or {}
 lp=fv.get('latest_period')
 if lp: latest_periods.append(lp)
if any(p>date.today().isoformat() for p in latest_periods): issues.append('future_financial_period')
metrics={
 'top_1':None,'top_3':None,'top_5':None,'top_10':None,'rank_ic':None,
 'confidence_calibration':None,'expected_vs_realized_return':None,
}
result={
 'as_of':date.today().isoformat(),'recommendations':len(recs),
 'rank_contract':'passed' if not any(x in issues for x in ['recommendation_count='+str(len(recs)),'rank_not_permutation']) else 'failed',
 'contract_issues':issues,
 'actions':dict(Counter(r.get('action') for r in recs)),
 'horizons':dict(Counter(r.get('horizon_label') for r in recs)),
 'market_stances':dict(Counter(r.get('market_stance') for r in recs)),
 'historical_metrics':metrics,
 'historical_status':'insufficient_data',
 'historical_blockers':['No point-in-time publication_date for financial inputs','No realized forward-return ledger joined to this production ranking','Only current as-of recommendations are available'],
 'note':'No historical ranking metric or calibration value is fabricated.'
}
(OUT/'ranking_quality_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps(result,ensure_ascii=False))
