from __future__ import annotations
import json,re,urllib.request,csv,sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC,date,datetime
from pathlib import Path
sys.path[:0]=['/home/ubuntu/EGX-Genom/research/src','/home/ubuntu/EGX-Genom/research/scripts']
from agx_research.collectors.raw import build_raw_document
from agx_research.collectors.stockanalysis_financials import StockAnalysisFinancialsCollector
from agx_research.financials.provider import FinancialStatementProvider
from agx_research.sources.catalog import seed_registry
from agx_research.valuation.engine import FairValueEngine
ROOT=Path('/home/ubuntu/EGX-Genom'); OUT=ROOT/'audit'/'decision_101'; OUT.mkdir(parents=True,exist_ok=True)
HEAD={'User-Agent':'Mozilla/5.0 (research/egx-genom)'}
def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url,headers=HEAD),timeout=15) as r:return r.read().decode('utf-8','ignore')
def shares_from_stats(ticker):
    html=fetch(f'https://stockanalysis.com/quote/egx/{ticker}/statistics/')
    for p in [r'Shares Outstanding.{0,300}?title="([0-9,]+)"',r'"id":"sharesout"[^}]*"hover":"([0-9,]+)"']:
        m=re.search(p,html,re.I|re.S)
        if m:return float(m.group(1).replace(',',''))
    return None
class InMemory(FinancialStatementProvider):
    def __init__(self,items):self.items=items
    def get_line_items(self,ticker,start,end,*,statement_type=None):return [x for x in self.items if x.ticker==ticker and start<=x.period_end_date<=end and (statement_type is None or x.statement_type==statement_type)]
def main():
    spec=seed_registry().latest('stockanalysis_financials'); universe={}
    for p in (ROOT/'research'/'data'/'universe').glob('EGX*.csv'):
        with p.open(newline='',encoding='utf-8') as f:
            for r in csv.DictReader(f):universe[r['ticker'].strip().upper()]=r.get('company_name','')
    def one(t):
        try:
            url=StockAnalysisFinancialsCollector.url(t); html=fetch(url)
            doc=build_raw_document(source_id=spec.id,collector='LiveReadiness',collector_version='1',original_url=url,content_text=html,schema_version=spec.schema_version,license=spec.license)
            batch=StockAnalysisFinancialsCollector(spec,tickers=[t]).parse(doc); sh=shares_from_stats(t)
            # StockAnalysis explicitly labels these tables "Financials in millions EGP".
            # EPS is already per-share and is not scaled; absolute financial items are.
            for item in batch.financial_statement_line_items:
                if item.line_item=='eps_basic':
                    item.line_item='eps_diluted'
                else:
                    item.value *= 1_000_000.0
            if sh:
                latest=max((x.period_end_date for x in batch.financial_statement_line_items),default=date.min)
                from agx_research.financials.schema import FinancialStatementLineItem
                batch.financial_statement_line_items.append(FinancialStatementLineItem(ticker=t,period_end_date=latest,period_type='ANNUAL',statement_type='BALANCE_SHEET',line_item='shares_outstanding',value=sh,currency='EGP'))
            fv=FairValueEngine(InMemory(batch.financial_statement_line_items)).value(t,date.today(),sector=None)
            return {'ticker':t,'source':'stockanalysis','line_items':len(batch.financial_statement_line_items),'shares_outstanding':sh,'fair_value':fv.model_dump(mode='json') if fv else None,'warning':None if fv else 'valuation_engine_insufficient_models_or_stale_period'}
        except Exception as e:return {'ticker':t,'source':'stockanalysis','line_items':0,'shares_outstanding':None,'fair_value':None,'warning':f'{type(e).__name__}: {e}'}
    rows=[]; tickers=sorted(universe)
    with ThreadPoolExecutor(max_workers=16) as ex:
        fs={ex.submit(one,t):t for t in tickers}
        for i,f in enumerate(as_completed(fs),1):
            r=f.result(); rows.append(r); print(f'[{i}/{len(tickers)}] {r["ticker"]} items={r["line_items"]} shares={r["shares_outstanding"] is not None} fair_value={r["fair_value"] is not None}',flush=True)
    rows.sort(key=lambda x:x['ticker']); ready=sum(r['fair_value'] is not None for r in rows)
    out={'as_of':datetime.now(UTC).date().isoformat(),'universe':len(rows),'fair_value_ready':ready,'rows':rows,'note':'Only computed FairValueEngine results are included; no fair value is derived from price.'}
    (OUT/'live_readiness.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8'); print(json.dumps({'universe':len(rows),'fair_value_ready':ready}))
if __name__=='__main__':main()
