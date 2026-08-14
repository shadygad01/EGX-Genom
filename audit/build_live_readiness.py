from __future__ import annotations
import json,re,urllib.request,csv,sys
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import UTC,date,datetime
import math
from pathlib import Path
sys.path[:0]=['/home/ubuntu/EGX-Genom/research/src','/home/ubuntu/EGX-Genom/research/scripts']
from agx_research.collectors.raw import build_raw_document
from agx_research.collectors.stockanalysis_financials import StockAnalysisFinancialsCollector
from agx_research.collectors.mubasher_financials import MubasherFinancialsCollector
from agx_research.financials.provider import FinancialStatementProvider
from agx_research.sources.catalog import seed_registry
from agx_research.valuation.engine import FairValueEngine
ROOT=Path('/home/ubuntu/EGX-Genom'); OUT=ROOT/'audit'/'decision_101'; OUT.mkdir(parents=True,exist_ok=True)
HEAD={'User-Agent':'Mozilla/5.0 (research/egx-genom)'}
def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url,headers=HEAD),timeout=15) as r:return r.read().decode('utf-8','ignore')
def shares_from_stats(ticker):
    try: html=fetch(f'https://stockanalysis.com/quote/egx/{ticker}/statistics/')
    except Exception: return None
    for p in [r'Shares Outstanding.{0,300}?title="([0-9,]+)"',r'"id":"sharesout"[^}]*"hover":"([0-9,]+)"']:
        m=re.search(p,html,re.I|re.S)
        if m:return float(m.group(1).replace(',',''))
    return None
class InMemory(FinancialStatementProvider):
    def __init__(self,items):self.items=items
    def get_line_items(self,ticker,start,end,*,statement_type=None):return [x for x in self.items if x.ticker==ticker and start<=x.period_end_date<=end and (statement_type is None or x.statement_type==statement_type)]
def validate_items(items):
    if not items:return items,'missing_line_items'
    currencies={('EGP' if 'EGP' in str(x.currency).upper() else str(x.currency).strip()) for x in items}
    if len(currencies)>1:return [],'mixed_currency'
    if any(not math.isfinite(float(x.value)) for x in items):return [],'non_finite_value'
    if any(x.period_end_date>date.today() for x in items):return [],'future_period'
    return items,None
def classify_sector(company):
    c=(company or '').casefold()
    if any(k in c for k in ('bank','banking')): return 'Banks'
    if any(k in c for k in ('telecom','telecommunications','mobile')): return 'Telecommunications'
    if any(k in c for k in ('real estate','real-estate','housing','property')): return 'Real Estate'
    if any(k in c for k in ('technology','software','informatics')): return 'Technology'
    if any(k in c for k in ('cement','fertilizer','steel','chem')): return 'Materials'
    return None
def model_gate_snapshot(items, shares):
    latest={}
    for x in sorted(items,key=lambda z:z.period_end_date): latest[x.line_item]=x.value
    def positive(name): return latest.get(name) is not None and latest.get(name)>0
    gates={
      'pe': 'ready' if positive('eps_diluted') or positive('eps_basic') else 'missing_or_non_positive_eps',
      'pb': 'ready' if shares and positive('total_equity') else ('missing_total_equity' if not positive('total_equity') else 'missing_shares'),
      'residual_income': 'ready' if shares and positive('total_equity') and (positive('eps_diluted') or positive('eps_basic')) else 'missing_equity_eps_or_shares',
      'ev_ebitda': 'ready' if shares and positive('ebitda') else 'missing_or_non_positive_ebitda_or_shares',
      'earnings_power': 'ready' if shares and positive('operating_income') else 'missing_or_non_positive_operating_income_or_shares',
      'dcf': 'ready' if shares and positive('free_cash_flow') else 'missing_or_non_positive_fcf_or_shares',
      'ddm': 'ready' if positive('dividend_per_share') else 'missing_or_non_positive_dividend',
    }
    return {'available_fields':sorted(k for k,v in latest.items() if v is not None),'model_gates':gates}
def main():
    specs=seed_registry(); spec=specs.latest('stockanalysis_financials'); mub_spec=specs.latest('mubasher_financials'); universe={}
    for p in (ROOT/'research'/'data'/'universe').glob('EGX*.csv'):
        with p.open(newline='',encoding='utf-8') as f:
            for r in csv.DictReader(f):universe[r['ticker'].strip().upper()]=r.get('company_name','')
    def one(t):
        try:
            source='stockanalysis'; batch=None; sh=shares_from_stats(t)
            try:
                url=StockAnalysisFinancialsCollector.url(t); html=fetch(url)
                doc=build_raw_document(source_id=spec.id,collector='LiveReadiness',collector_version='1',original_url=url,content_text=html,schema_version=spec.schema_version,license=spec.license)
                batch=StockAnalysisFinancialsCollector(spec,tickers=[t]).parse(doc)
            except Exception:
                batch=None
            if batch is None or not batch.financial_statement_line_items:
                source='mubasher'; url=MubasherFinancialsCollector.url(t); html=fetch(url)
                doc=build_raw_document(source_id=mub_spec.id,collector='LiveReadiness:MubasherFallback',collector_version='1',original_url=url,content_text=html,schema_version=mub_spec.schema_version,license=mub_spec.license)
                batch=MubasherFinancialsCollector(mub_spec,tickers=[t]).parse(doc)
            if source=='stockanalysis':
                # StockAnalysis explicitly labels these tables "Financials in millions EGP".
                # EPS is already per-share and is not scaled; absolute financial items are.
                for item in batch.financial_statement_line_items:
                    if item.line_item=='eps_basic': item.line_item='eps_diluted'
                    elif item.line_item in {'eps_diluted','dividend_per_share','shares_outstanding'}: pass
                    else: item.value*=1_000_000.0
            elif sh and batch.financial_statement_line_items and all('EGP' in str(item.currency) for item in batch.financial_statement_line_items):
                # Transparent derived EPS only from disclosed net income and shares.
                from agx_research.financials.schema import FinancialStatementLineItem
                for item in list(batch.financial_statement_line_items):
                    if item.line_item=='net_income':
                        batch.financial_statement_line_items.append(FinancialStatementLineItem(ticker=t,period_end_date=item.period_end_date,period_type=item.period_type,statement_type='INCOME_STATEMENT',line_item='eps_diluted',value=item.value/sh,currency='EGP'))
            if sh:
                latest=max((x.period_end_date for x in batch.financial_statement_line_items),default=date.min)
                from agx_research.financials.schema import FinancialStatementLineItem
                batch.financial_statement_line_items.append(FinancialStatementLineItem(ticker=t,period_end_date=latest,period_type='ANNUAL',statement_type='BALANCE_SHEET',line_item='shares_outstanding',value=sh,currency='EGP'))
            validated,validation_warning=validate_items(batch.financial_statement_line_items)
            sector=classify_sector(universe.get(t,''))
            diagnostics=model_gate_snapshot(validated,sh) if not validation_warning else {'available_fields':[],'model_gates':{}}
            fv=FairValueEngine(InMemory(validated)).value(t,date.today(),sector=sector) if not validation_warning else None
            return {'ticker':t,'company_name':universe.get(t,''),'sector':sector,'source':source,'line_items':len(validated),'shares_outstanding':sh,'financial_validation':validation_warning,'diagnostics':diagnostics,'fair_value':fv.model_dump(mode='json') if fv else None,'warning':validation_warning or (None if fv else 'valuation_engine_insufficient_models_or_stale_period')}
        except Exception as e:return {'ticker':t,'source':'stockanalysis_then_mubasher','line_items':0,'shares_outstanding':None,'fair_value':None,'warning':f'{type(e).__name__}: {e}'}
    rows=[]; tickers=sorted(universe)
    with ThreadPoolExecutor(max_workers=16) as ex:
        fs={ex.submit(one,t):t for t in tickers}
        for i,f in enumerate(as_completed(fs),1):
            r=f.result(); rows.append(r); print(f'[{i}/{len(tickers)}] {r["ticker"]} source={r["source"]} items={r["line_items"]} fair_value={r["fair_value"] is not None}',flush=True)
    rows.sort(key=lambda x:x['ticker']); ready=sum(r['fair_value'] is not None for r in rows)
    out={'as_of':datetime.now(UTC).date().isoformat(),'universe':len(rows),'fair_value_ready':ready,'rows':rows,'note':'StockAnalysis primary with Mubasher fallback; only computed FairValueEngine results are included; no fair value is derived from price.'}
    (OUT/'live_readiness.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8'); print(json.dumps({'universe':len(rows),'fair_value_ready':ready}))
if __name__=='__main__':main()
