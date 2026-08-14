from __future__ import annotations
import csv,re
from pathlib import Path
ROOT=Path('/home/ubuntu/EGX-Genom')
SOURCES={
 'ACTF': Path('/home/ubuntu/upload/www.investing.com_equities_act-financial-historical-data_1786706520672.md'),
 'IEEC': Path('/home/ubuntu/upload/www.investing.com_equities_industrial-engineer-enterprises-historical-data_1786706532717.md'),
}
MONTHS={m:i for i,m in enumerate(['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'],1)}
for ticker,src in SOURCES.items():
 text=src.read_text(encoding='utf-8')
 rows=[]
 for line in text.splitlines():
  if not line.startswith('|'): continue
  cells=[c.strip().replace('\\.','.') for c in line.strip().strip('|').split('|')]
  if len(cells)<6: continue
  dm=re.match(r'^([A-Z][a-z]{2}) (\d{1,2}), (\d{4})$',cells[0])
  vm=re.match(r'^([0-9.]+)([KMB])$',cells[5])
  if not dm or not vm: continue
  mon,day,year=dm.groups(); close,op,hi,lo=cells[1:5]; vol,suffix=vm.groups()
  mult={'K':1_000,'M':1_000_000,'B':1_000_000_000}[suffix]
  rows.append({'date':f'{int(year):04d}-{MONTHS[mon]:02d}-{int(day):02d}','open':op,'high':hi,'low':lo,'close':close,'volume':str(int(float(vol)*mult))})
 rows=sorted({r['date']:r for r in rows}.values(),key=lambda r:r['date'])
 if len(rows)<10: raise SystemExit(f'{ticker}: only {len(rows)} rows')
 out=ROOT/'research/data/prices'/f'{ticker}.csv'; out.parent.mkdir(parents=True,exist_ok=True)
 with out.open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=['date','open','high','low','close','volume']);w.writeheader();w.writerows(rows)
 print(ticker,len(rows),rows[-1]['date'],rows[-1]['close'],src)
