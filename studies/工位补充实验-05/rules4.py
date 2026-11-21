"""Train exclusively on completed experiments. Generate decisions before validation replay."""
import hashlib
import json
import math
from pathlib import Path
import sys
import numpy as np
from parent_policy import before, after, fit, forecast, quality, read

D=Path(__file__).resolve().parent
OLD=D.parent/'风险感知动作接受实验-03'
PREVIOUS=D.parent/'独立测量策略实验-02'
def save(name,obj):
    (D/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf8')
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
def excess(action,limit):
    return max(0.,abs(action[0])-limit[0])+max(0.,abs(action[1])-limit[1])
def pre(r,q,a,limit):
    c=math.log2(2/r['gap'])
    ob=math.tan(math.radians(r['angle']))
    return before(r,q)+[abs(a[0]),abs(a[1]),a[1]*ob,excess(a,limit),
        c*(r['task']=='square'),c*(r['task']=='round'),ob*(r['task']=='square'),ob*(r['task']=='round')]
def post(r,q,d,m,limit):
    z=r['depth']['far']-r['depth']['near']
    ob=math.tan(math.radians(r['angle']))
    delta=m[1]-d[1]
    return after(r,q,d,m)+[excess(d,limit),excess(m,limit),delta*ob,
        delta/(1+abs(z*ob)),abs(delta)*(r['task']=='round'),abs(m[0])-abs(d[0]),
        ob*(r['task']=='round'),math.log2(2/r['gap'])*(r['task']=='square')]
def train():
    old=read(OLD/'case-outcomes.json')
    audit=[]
    for r in old:
        d=r['scores']['direct']['success'];m=r['scores']['always']['success']
        chosen=r['ranks']['risk']<=6
        if not chosen and m and not d: label='漏测·强对照会采用' if r['accept'] else '漏测·强对照也会拒绝'
        elif not chosen and not m and d and r['accept']: label='跳过有害修正'
        elif chosen and m and not d and not r['accept']: label='已测误拒'
        else: continue
        audit.append(dict(id=r['id'],task=r['task'],gap=r['gap'],angle=r['angle'],rank=r['ranks']['risk'],
                          label=label,score=r['gain'],direct=r['scores']['direct'],measured=r['scores']['always']))
    save('development-audit.json',audit)
    rows=[];qs=[];batch=[]
    for i,folder in enumerate([PREVIOUS,OLD]):
        group=read(folder/'case-outcomes.json')
        rows+=group
        qs += [quality(folder/'frames'/(r['id']+'.jpg')) for r in group]
        batch += [i*100+r['batch'] for r in group]
    ds=[r['scores']['direct']['action'] for r in rows]
    ms=[r['scores']['always']['action'] for r in rows]
    labels=np.array([int(r['scores']['always']['success'])-int(r['scores']['direct']['success']) for r in rows])
    limit=np.quantile(np.abs([r['scores']['oracle']['action'] for r in rows]),.95,axis=0).tolist()
    x=np.array([pre(r,q,d,limit) for r,q,d in zip(rows,qs,ds)])
    z=np.array([post(r,q,d,m,limit) for r,q,d,m in zip(rows,qs,ds,ms)])
    batch=np.asarray(batch)
    accept=np.zeros(len(rows),bool)
    for key in np.unique(batch):
        val=batch==key
        accept[val]=forecast(fit(z[~val],labels[~val]),z[val])>0
    legacy=read(OLD/'policy-lock.json')
    src=[D/n for n in ('protocol.txt','rules4.py','parent_policy.py','model_client.py','rig_base.py','server.py','collect.py')]+[p/'case-outcomes.json' for p in (OLD,PREVIOUS)]
    save('policy-lock.json',dict(pre=fit(x,labels*accept),post=fit(z,labels),limit=limit,
        old_pre=legacy['measurement_model'],old_post=legacy['acceptance_model'],sha256={str(p):sha(p) for p in src}))
def decisions():
    lock=read(D/'policy-lock.json')
    assert all(sha(Path(p))==h for p,h in lock['sha256'].items())
    rows=read(D/'manifest.json')
    acts=read(D/'actions.json');out={}
    earlier=[]
    for p in [OLD/'manifest.json',PREVIOUS/'manifest.json']+[D.parent/'独立公差实验-01'/'validated'/n for n in ['manifest.json','stress-manifest.json']]:
        earlier.extend(read(p))
    assert len(rows)==len({r['seed'] for r in rows})==len(acts)==400
    for field in ('seed','angle','id'):
        assert not ({r[field] for r in earlier}&{r[field] for r in rows})
    for r in rows:
        key=r['id'];q=quality(D/'frames'/(key+'.jpg'));d=acts[key]['direct'];m=acts[key]['always'];lim=lock['limit']
        priority=float(forecast(lock['pre'],pre(r,q,d,lim)));gain=float(forecast(lock['post'],post(r,q,d,m,lim)))
        out[key]=dict(task=r['task'],batch=r['batch'],priority=priority,oldpriority=float(forecast(lock['old_pre'],before(r,q))),
            gain=gain,accept=gain>0,oldaccept=bool(forecast(lock['old_post'],after(r,q,d,m))>0))
    for b in range(40):
        ids=[k for k in out if out[k]['batch']==b]; assert len(ids)==10
        for field,rank in [('priority','rank'),('oldpriority','oldrank')]:
            salt='strong-v4:' if rank=='rank' else 'r3:'
            order=sorted(ids,key=lambda k:(-out[k][field],hashlib.sha256((salt+k).encode()).hexdigest()))
            if rank=='rank':
                leaders=[next(k for k in order if out[k]['task']==t) for t in ['round','square','dual']]
                order=[k for k in order if k in leaders]+[k for k in order if k not in leaders]
            for j,key in enumerate(order,1):out[key][rank]=j
    save('decisions.json',out)
    save('before-replay.json',{name:sha(D/name) for name in ('actions.json','manifest.json','policy-lock.json','decisions.json')})
if __name__=='__main__':
    {'train':train,'decide':decisions}[sys.argv[1]]()
