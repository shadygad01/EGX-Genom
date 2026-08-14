import json
from pathlib import Path
ROOT=Path('/home/ubuntu/EGX-Genom'); src=ROOT/'audit/decision_101/live_readiness.json'; dst=ROOT/'research/data/dashboard/decision_readiness.json'
data=json.loads(src.read_text(encoding='utf-8'))
out=[]
for r in data['rows']:
    fv=r.get('fair_value')
    out.append({'ticker':r['ticker'],'as_of':data['as_of'],'status':'ready' if fv else 'blocked','decision':'invest' if fv else 'abstain','fair_value_available':bool(fv),'valuation':fv,'financial_periods':5 if r['line_items'] else 0,'blockers':[] if fv else [r.get('warning') or 'No multi-model fair value'],'next_actions':[] if fv else ['Acquire/validate missing financial or price evidence']})
dst.parent.mkdir(parents=True,exist_ok=True); dst.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8'); print('wrote',dst,'rows',len(out),'fair_value',sum(x['fair_value_available'] for x in out))
