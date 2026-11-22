from pathlib import Path
from reproduce import read,base
import csv,json,hashlib,sys
import numpy as np
from collections import Counter
from scipy.stats import binomtest
L=read(base/'lock.json');cal=read(base/'calibration.json')
assert all(hashlib.sha256((base/n).read_bytes()).hexdigest()==s for n,s in L['source_sha'].items())
for s,rule in L['policy'].items():
 c=[x for x in cal if x['stratum']==s and x['listed'] and x['legacy_keep']]
 assert rule['fixed']==('legacy' if sum(x['diff'] for x in c)>0 else 'switch')
 for fam,obj in rule['families'].items():
  a=Counter(x['diff'] for x in c if x['family']==fam);n=a[-1]+a[1]
  assert (obj['wins'],obj['losses'])==(a[1],a[-1])
  assert obj['retain']==bool(n>=8 and binomtest(a[1],n,.5,alternative='greater').pvalue<.05)
d=base/'depth';sys.path.insert(0,str(d));from rules4 import quality,pre,post,forecast
from policy5 import stream
w=read(d/'weights.json');ref=read(d/'ref.json');a=read(d/'actions.json');g=read(d/'gates.json');m=read(d/'manifest.json');lst=read(d/'list.json')
v={}
for r in m:
 i=r['id'];q=quality(d/'frames'/(i+'.jpg'));v[i]=dict(score=float(forecast(w['pre'],pre(r,q,a[i]['direct'],w['limit']))))
 if i in lst:assert np.isclose(g[i]['score'],forecast(w['post'],post(r,q,a[i]['direct'],a[i]['measured'],w['limit'])))
assert lst==[i for b in range(32) for i in stream(sorted(r['id'] for r in m if r['batch']==b),v,8,ref)]
scores=read(d/'scores.json');assert len(scores)==576
drequests=list((d/'responses').glob('*.json'));assert len(drequests)==576
out={'depth_requests':len(drequests),'depth_attempts':sum(read(x)['attempts'] for x in drequests)}
F=base/'formal';R=F/'records'
for model in ['gpt-6.2-sol','gpt-6.1-terra']:
 counts=Counter();attempts=0;endpoints=0
 for r in read(F/'scenes.json'):
  s=R/r['id'];z=s/model
  for ip in z.glob('*-input.json'):
   mode=ip.name.split('-')[0];req=read(ip);assert req['model']==model
   for image in req['images']:assert image['sha256']==hashlib.sha256((s/image['path']).read_bytes()).hexdigest()
   reply=z/(mode+'-reply.json');assert reply.exists();counts[mode]+=1
   trials=[read(v) for v in z.glob(mode+'-cycle-*-attempt-*.json')];attempts+=len(trials);assert any(v['error'] is None for v in trials)
  for p in z.glob('*/receipt.json'):
   b=read(p);endpoints+=1;assert b['run_id']=='franka-acceptance-v1' and b['checkpoint_id']==read(z/'grip.json')['checkpoint_id']
   assert b['reply_sha256']==hashlib.sha256((z/(b['branch']+'-reply.json')).read_bytes()).hexdigest()
   e=b['endpoint'];dr=b['drift_mm'];ok=b['lifted'] and b['carry_bilateral_samples']>=8 and not e['right'] and not e['left'] and b['margin_mm']>=-.15 and 6.6<e['part_mm'][2]<7.5 and e['tilt_deg']<3 and dr<.35
   assert b['success']==bool(ok)
 assert counts=={'grip':160,'first':160,'overhead':128} and endpoints==288
 out[model]=dict(calls=dict(counts),attempts=attempts,endpoints=endpoints)
print(json.dumps(out,indent=2));(base/'checks.json').write_text(json.dumps(out,indent=2),encoding='utf8')
