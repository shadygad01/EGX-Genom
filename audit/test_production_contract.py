import json
from pathlib import Path

ROOT=Path('/home/ubuntu/EGX-Genom')
readiness=json.loads((ROOT/'research/data/dashboard/decision_readiness.json').read_text())
recs=json.loads((ROOT/'research/data/dashboard/recommendations.json').read_text())
assert len(readiness)==101, len(readiness)
assert len(recs)==101, len(recs)
assert sorted(r.get('rank') for r in recs)==list(range(1,102))
assert set(r.get('market_stance') for r in recs) <= {'attractive','neutral','unattractive'}
for row in readiness:
    fv=row.get('valuation')
    if fv:
        assert len(fv.get('included_models',[]))>=3, row['ticker']
        assert all(isinstance(v,(int,float)) and v>0 for m,v in fv.get('models',{}).items() if m in fv['included_models'])
for rec in recs:
    assert rec.get('evidence_status') in {'sufficient','insufficient_evidence'}
    if rec.get('action')=='abstain': assert rec.get('evidence_status')=='insufficient_evidence'
print('production_contract_passed', {'readiness':len(readiness),'recommendations':len(recs),'ranks':'1-101','stances':sorted(set(r['market_stance'] for r in recs))})
