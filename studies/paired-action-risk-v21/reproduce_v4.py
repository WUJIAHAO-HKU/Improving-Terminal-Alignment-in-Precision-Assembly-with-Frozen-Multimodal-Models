"""Reproduce the locked paired-action-risk V4 result without model calls.
Run from this directory with Python 3.10+ and scipy installed.
"""
import csv, json, math
from pathlib import Path
from scipy.stats import t
BASE=Path(__file__).resolve().parent
rows=list(csv.DictReader((BASE/'parts.csv').open(encoding='utf-8')))
assert len(rows)==400 and sum(int(r['listed']) for r in rows)==320
batches=sorted({int(r['batch']) for r in rows})
assert len(batches)==40 and all(sum(int(r['batch'])==b for r in rows)==10 for b in batches)
for r in rows:
    assert r['chosen'] in ('0','1') and r['fixed'] in ('0','1')
D=[sum(int(r['chosen'])-int(r['fixed']) for r in rows if int(r['batch'])==b) for b in batches]
mean=sum(D)/len(D); sd=(sum((x-mean)**2 for x in D)/(len(D)-1))**0.5
half=t.ppf(.975,len(D)-1)*sd/math.sqrt(len(D))
tstat=mean/(sd/math.sqrt(len(D)))
out={
 'n':len(rows),'listed':sum(int(r['listed']) for r in rows),
 'fixed':sum(int(r['fixed']) for r in rows),'chosen':sum(int(r['chosen']) for r in rows),
 'delta_seats_per_100':100*mean/10,
 'delta_seats_per_100_ci':[100*(mean-half)/10,100*(mean+half)/10],
 'one_sided_p':float(t.sf(tstat,len(D)-1)),
 'two_sided_p':float(2*t.sf(abs(tstat),len(D)-1)),
 'rescued':sum(int(r['chosen'])>int(r['fixed']) for r in rows),
 'rejected':sum(int(r['chosen'])<int(r['fixed']) for r in rows),
}
print(json.dumps(out,indent=2))
assert out['fixed']==95 and out['chosen']==99 and out['rescued']==4 and out['rejected']==0
assert out['delta_seats_per_100_ci'][0]>0
(BASE/'reproduced-results.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
