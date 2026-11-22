"""Recompute the locked policy and paired intervals, from part-level independent endpoints."""
import csv,json,math,sys
from pathlib import Path
import numpy as np
from scipy.stats import t
base=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf8')
def analyze(rows,lock):
 results={}
 for s,rule in lock['policy'].items():
  items=[dict(r) for r in rows if r['stratum']==s];bs=sorted({int(r['batch']) for r in items});n=len(items)
  assert len(bs)==lock['batches']['depth' if s=='Sol-depth' else 'franka']
  for b in bs:
   members=[r for r in items if int(r['batch'])==b];assert len(members)==(10 if s=='Sol-depth' else 5)
   assert sum(int(r['listed']) for r in members)==len(members)*4//5
  for r in items:
   listed=bool(int(r['listed']));old=listed and bool(int(r['legacy_keep']));ad=old and rule['families'][r['family']]['retain'];fixed=old and rule['fixed']=='legacy'
   d=int(r['first']);m=int(r['second']) if listed else d
   r.update(direct=d,switch=m,legacy=d if old else m,adaptive=d if ad else m,fixed=d if fixed else m)
   r.update(keep_old=old,keep_ad=ad)
  pairs={}
  for a,b in [('adaptive','fixed'),('adaptive','switch'),('adaptive','legacy'),('legacy','switch'),('adaptive','direct')]:
   key=a+'-'+b;delta=[r[a]-r[b] for r in items]
   means=np.array([np.mean([r[a]-r[b] for r in items if int(r['batch'])==k])*100 for k in bs])
   identity=(s.endswith('top') and (a,b) in [('adaptive','fixed'),('adaptive','switch')]) or (s=='Sol-depth' and {a,b}=={'legacy','fixed'})
   se=float(means.std(ddof=1)/math.sqrt(len(bs)));avg=float(means.mean());half=t.ppf(.975,len(bs)-1)*se
   pairs[key]=dict(wins=delta.count(1),losses=delta.count(-1),pp=avg,ci=[float(avg-half),float(avg+half)] if se else ([0.,0.] if identity else None),identical_by_design=identity)
  diagnostic={}
  for metric,direction in [('avoided_false_rejections',-1),('forgone_rescues',1)]:
   per_batch=[]
   for batch in bs:
    subset=[r for r in items if int(r['batch'])==batch and int(r['listed'])]
    changed=sum((int(r['keep_old'])-int(r['keep_ad']))*(r['direct']-r['switch']==direction) for r in subset)
    per_batch.append(100*changed/len(subset))
   avg=float(np.mean(per_batch));se=float(np.std(per_batch,ddof=1)/math.sqrt(len(bs)));half=t.ppf(.975,len(bs)-1)*se
   diagnostic[metric]=dict(per100measured=avg,ci=[float(avg-half),float(avg+half)] if se else None)
  results[s]=dict(diagnostics=diagnostic,n=n,measured=sum(int(r['listed']) for r in items),seated={m:sum(r[m] for r in items) for m in ['direct','switch','legacy','adaptive','fixed']},counts={k:dict(kept=sum(r[k] for r in items),rescued=sum(r[k] and r['direct']>r['switch'] for r in items),wrongly_rejected=sum(r[k] and r['direct']<r['switch'] for r in items)) for k in ['keep_old','keep_ad']},pairs=pairs)
 return results
if __name__=='__main__':
 rows=list(csv.DictReader((base/'parts.csv').open(encoding='utf8')));results=analyze(rows,read(base/'lock.json'));save(base/'results.json',results);print(json.dumps(results,indent=2))
