from __future__ import annotations
import csv,json
from datetime import date,datetime,timedelta
from pathlib import Path
from collections import Counter
ROOT=Path('/home/ubuntu/EGX-Genom'); DATA=ROOT/'research/data'; OUT=ROOT/'audit/decision_101'
readiness=json.loads((DATA/'dashboard/decision_readiness.json').read_text())
price_files=list((DATA/'prices').glob('*.csv'))
windows=[]
for p in price_files:
 rows=list(csv.DictReader(p.open()))
 dates=[r.get('date') for r in rows if r.get('date')]
 if dates:
  first,last=dates[0],dates[-1]
  windows.append({'ticker':p.stem,'first_price_date':first,'last_price_date':last,'bars':len(rows),'has_60_bar_window':len(rows)>=60})
published=sum(1 for r in readiness if r.get('published_at'))
valuation_snapshots=sum(1 for r in readiness if r.get('valuation') and r['valuation'].get('latest_period'))
# A production ranking walk-forward requires both point-in-time inputs and realized forward returns.
result={
 'as_of':date.today().isoformat(),
 'universe':len(readiness),
 'price_series':len(windows),
 'published_at_records':published,
 'valuation_period_end_records':valuation_snapshots,
 'historical_ranking_status':'blocked_insufficient_point_in_time_inputs',
 'metrics':{'top_1':None,'top_3':None,'top_5':None,'top_10':None,'rank_ic':None,'mean_realized_return':None,'mfe':None,'mae':None,'time_to_target':None},
 'required_inputs':['decision snapshots by as_of','published_at for each financial input','forward returns after each decision','frozen universe by as_of','corporate-action-adjusted prices'],
 'available_price_window_summary':{
   'series_with_60_bars':sum(x['has_60_bar_window'] for x in windows),
   'latest_price_date_max':max((x['last_price_date'] for x in windows),default=None),
   'latest_price_date_min':min((x['last_price_date'] for x in windows),default=None)
 },
 'note':'No Top-K or realized-return metric is produced because current Fair Value snapshots are not point-in-time and no joined forward-return ledger exists.'
}
(OUT/'production_walk_forward.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps(result,ensure_ascii=False))
