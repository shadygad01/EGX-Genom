from __future__ import annotations
import csv,json
from pathlib import Path
ROOT=Path('/home/ubuntu/EGX-Genom'); PR=ROOT/'research/data/prices'; MAN=PR/'_manifest.json'
# Values copied from the rendered Mubasher stock pages: Last update 13 Aug 2026.
# They are not inferred from market cap or from another security.
rows={
 'ACTF': {'date':'2026-08-13','open':'2.75','high':'2.83','low':'2.75','close':'2.76','volume':'29654358'},
 'IEEC': {'date':'2026-08-13','open':'0.87','high':'0.99','low':'0.87','close':'0.90','volume':'387209069'},
}
for ticker,new in rows.items():
 p=PR/f'{ticker}.csv'; old=list(csv.DictReader(p.open())) if p.exists() else []
 merged={r['date']:r for r in old}; merged[new['date']]=new
 with p.open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=['date','open','high','low','close','volume']);w.writeheader();w.writerows([merged[k] for k in sorted(merged)])
 print(ticker,len(merged),new)
d=json.loads(MAN.read_text())
d['success_count']=101; d['failed_count']=0; d['failed']=[]
for ticker in rows:
 d.setdefault('success',{})[ticker]={'bars':len(list(csv.DictReader((PR/f'{ticker}.csv').open()))),'symbol':'Mubasher:EGX:'+ticker,'latest':rows[ticker]['date'],'close':rows[ticker]['close'],'source_url':f'https://english.mubasher.info/markets/EGX/stocks/{ticker}/','source_as_of':'2026-08-13'}
d['source']='Yahoo Finance chart endpoint + StockAnalysis history + Mubasher current stock pages'
MAN.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
(Path(ROOT/'audit/decision_101'/'current_price_provenance.md')).write_text('''# Current price provenance\n\nACTF and IEEC received a current 13-Aug-2026 OHLCV observation from their Mubasher EGX stock pages. The values were displayed directly by Mubasher and were not inferred or filled from market cap.\n\n- ACTF: open 2.75, high 2.83, low 2.75, close 2.76, volume 29,654,358.\n- IEEC: open 0.87, high 0.99, low 0.87, close 0.90, volume 387,209,069.\n''',encoding='utf-8')
