from pathlib import Path
import json,sys,numpy as np
from policy15 import *
D=Path('.')
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,v):Path(p).write_text(json.dumps(v,indent=2),encoding='utf8')
def make(m,kit):
    if kit:from decide13 import geometry,spec,targets,discrepancy
    else:from policy import geometry,public,diff
    gain=read('gain.json')[('kits_' if kit else 'four_')+m];out={};plans={}
    for r in read('scenes.json'):
        i=r['id'];root=D/'responses'/m
        a,b=[read(root/(i+'-'+k+'.json'))['anchor' if kit else 'action'] for k in ['first','overhead']]
        if kit:
            g,ok=geometry(r,'eye','first');h,okh=geometry(r,'top','overhead');dist=lambda x,y:discrepancy(x,y,r)
            cat,L,sh=features(r,True,spec);pk=read(root/(i+'-prefix.json'))['picks']
            plans[i]={k:[dict(op='assemble',pick=pk[j],place=w) for j,w in enumerate(targets(r,x)) if j] for k,x in [('first',a),('overhead',b)]}
        else:
            d=D/'initial'/i;rr=public(r);g,ok=geometry(d/'00-eye.png',rr);h,okh=geometry(d/'00-top.png',rr,'top');dist=lambda x,y:diff(x,y,rr)
            cat,L,sh=features(r,False);plans[i]={'first':a,'overhead':b}
        if not okh:h=g;sh=0
        pre=dist(a,g)/r['gap'] if ok else 1e6
        out[i]=dict(batch=r['batch'],old_pre=pre,new_pre=score(pre,gain[cat]),cat=cat,old_accept=dist(b,h)<dist(a,h),new_accept=gate(vec(a),vec(b),vec(h),L,sh))
    for b in set(v['batch'] for v in out.values()):
        ids=[i for i,v in out.items() if v['batch']==b]
        for k in ('old','new'):
            for j,i in enumerate(sorted(ids,key=lambda i:(-out[i][k+'_pre'],i)),1):out[i][k+'_rank']=j
    save(m+'-choices.json',out);save(m+('-plans.json' if kit else '-evaluate.json'),plans)

