"""Freeze rank/gate ablations and streaming thresholds, then compute all decisions blind."""
import hashlib,sys
import numpy as np
from rules4 import D,OLD,PREVIOUS,read,save,sha,quality,pre,post,fit,forecast

def subpre(r,q,d,lim):
    # Drop gap (0), gap squared (1), gap by angle (4), and gap by geometry (12,13).
    return np.delete(pre(r,q,d,lim),[0,1,4,12,13])
def subpost(r,q,d,m,lim):
    return np.delete(post(r,q,d,m,lim),[0,1,4,8,21])
def train():
    w=read(D/'policy-lock.json');lim=w['limit'];xs=[];zs=[];fs=[];full_pre=[];ys=[];bs=[]
    for i,p in enumerate((PREVIOUS,OLD)):
        for r in read(p/'case-outcomes.json'):
            d=r['scores']['direct'];m=r['scores']['always'];q=quality(p/'frames'/(r['id']+'.jpg'))
            v=(r,q,d['action'],m['action'],lim)
            xs.append(subpre(r,q,d['action'],lim));zs.append(subpost(*v));fs.append(post(*v))
            full_pre.append(forecast(w['pre'],pre(r,q,d['action'],lim)))
            bs.append(100*i+r['batch']);ys.append(int(m['success'])-int(d['success']))
    x,z,f,b,y=map(np.asarray,[xs,zs,fs,bs,ys]);acc=np.zeros(len(b));other=acc.copy()
    for group in np.unique(b):
        val=b==group
        for mat,arr in [(f,acc),(z,other)]:
            arr[val]=forecast(fit(mat[~val],y[~val]),mat[val])>0
    src=['protocol.txt','server.py','model_client.py','rules4.py','parent_policy.py','policy-lock.json','policy5.py','bench.py']
    save('study-lock.json',dict(rank_only=fit(x,y*acc),both_pre=fit(x,y*other),both_post=fit(z,y),
        ref=sorted(full_pre),hashes={n:sha(D/n) for n in src}))
def tie(key,salt):return hashlib.sha256((salt+key).encode()).hexdigest()
def ranked(ids,vals,field,cover=True):
    order=sorted(ids,key=lambda i:(-vals[i][field],tie(i,'strong-v4:')))
    if cover:
        leaders={next(i for i in order if vals[i]['task']==t) for t in ['square','round','dual']}
        return [i for i in order if i in leaders]+[i for i in order if i not in leaders]
    return order
def quota(ids,vals,k):
    groups=[[i for i in ids if vals[i]['task']==t] for t in ('square','round','dual')]
    expect=np.array([len(g)*k/10 for g in groups]);q=np.floor(expect).astype(int)
    for j in sorted(range(3),key=lambda j:(-(expect[j]-q[j]),j))[:k-int(q.sum())]:q[j]+=1
    return [i for g,n in zip(groups,q) for i in sorted(g,key=lambda i:tie(i,'stratum-05'))[:n]]
def stream(order,vals,k,ref):
    taken=[];left=k
    for j,i in enumerate(order):
        rem=len(order)-j
        if left and (left==rem or vals[i]['score']>=np.quantile(ref,1-left/rem)):
            taken.append(i);left-=1
    assert len(taken)==k
    return taken
def decide():
    s=read(D/'study-lock.json');assert all(sha(D/n)==v for n,v in s['hashes'].items())
    w=read(D/'policy-lock.json');lim=w['limit'];rows=read(D/'manifest.json');acts=read(D/'actions.json');v={}
    oldrows=[]
    for p in [PREVIOUS/'manifest.json',OLD/'manifest.json',D.parent/'强对照独立实验-04'/'manifest.json']+[D.parent/'独立公差实验-01'/'validated'/n for n in ['manifest.json','stress-manifest.json']]:oldrows+=read(p)
    for key in ['angle','seed','id']:assert not {r[key] for r in rows}&{r[key] for r in oldrows}
    assert len(rows)==len({r['seed'] for r in rows})==300
    for r in rows:
        i=r['id'];d=acts[i]['direct'];m=acts[i]['always'];q=quality(D/'frames'/(i+'.jpg'))
        pa=(r,q,d,lim);po=(r,q,d,m,lim)
        v[i]=dict(batch=r['batch'],task=r['task'],gap=r['gap'],score=float(forecast(w['pre'],pre(*pa))),
            accept=bool(forecast(w['post'],post(*po))>0),abscore=float(forecast(s['rank_only'],subpre(*pa))),
            bothscore=float(forecast(s['both_pre'],subpre(*pa))),bothaccept=bool(forecast(s['both_post'],subpost(*po))>0))
    batches=[]
    for j in range(30):
        ids=sorted(i for i in v if v[i]['batch']==j)
        orders=dict(natural=ids,first=sorted(ids,key=lambda i:v[i]['task']!='square'),last=sorted(ids,key=lambda i:v[i]['task']=='square'))
        sel={}
        for k in (8,6):
            choices=dict(full=ranked(ids,v,'score')[:k],random=sorted(ids,key=lambda i:tie(i,'random-05'))[:k],
                gap=sorted(ids,key=lambda i:(v[i]['gap'],tie(i,'gap-05')))[:k],strat=quota(ids,v,k),
                abrank=ranked(ids,v,'abscore')[:k],abboth=ranked(ids,v,'bothscore')[:k])
            choices.update({f'stream_{name}':stream(order,v,k,s['ref']) for name,order in orders.items()})
            assert all(len(set(z))==k for z in choices.values());sel[str(k)]=choices
        batches.append(dict(orders=orders,selections=sel))
    save('decisions.json',dict(items=v,batches=batches))
    save('before-replay.json',{n:sha(D/n) for n in ['manifest.json','actions.json','decisions.json','study-lock.json']})
if __name__=='__main__':{'train':train,'decide':decide}[sys.argv[1]]()
