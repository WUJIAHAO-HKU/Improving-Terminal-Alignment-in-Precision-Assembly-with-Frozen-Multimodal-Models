"""Two-stage action decisions. Only the fit step sees round 02 labels."""
import hashlib
import json
import math
from pathlib import Path
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / '独立测量策略实验-02'
def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def quality(path):
    gray = np.asarray(Image.open(path).convert('L'), dtype=float)[80:240,80:240] / 255
    return math.log(.005 + math.sqrt(sum(np.mean(np.diff(gray, axis=i)**2) for i in (0,1))/2))

def before(r, q):
    c = math.log2(2/r['gap'])
    a = math.tan(math.radians(r['angle']))
    return [c,c*c,a,q,c*a,a*q,int(r['task']=='square'),int(r['task']=='dual')]

def after(r, q, direct, measured):
    gap = r['gap']
    dx,dy = np.asarray(measured) - direct
    near,far = r['depth']['near'],r['depth']['far']
    return before(r,q) + [math.log1p(math.hypot(dx,dy)/gap), math.log1p(abs(dy)),
        abs(measured[1])-abs(direct[1]), math.hypot(*measured)-math.hypot(*direct),
        (far-near), (far-near)*math.tan(math.radians(r['angle']))]

def fit(x,y):
    mu=x.mean(0)
    sd=np.maximum(x.std(0),1e-6)
    z=(x-mu)/sd
    coef=np.linalg.solve(z.T@z + 12*np.eye(z.shape[1]),z.T@(y-y.mean()))
    return dict(mu=mu.tolist(),sd=sd.tolist(),coef=coef.tolist(),intercept=float(y.mean()))

def forecast(model,x):
    return ((np.asarray(x)-model['mu'])/model['sd'])@model['coef'] + model['intercept']

def lock():
    rows=read(OLD/'case-outcomes.json')
    test=read(HERE/'manifest.json')
    assert len(test)==len({r['seed'] for r in test})==300
    assert not {r['seed'] for r in rows} & {r['seed'] for r in test}
    assert not {r['angle'] for r in rows} & {r['angle'] for r in test}
    b=np.array([r['batch'] for r in rows])
    x=np.array([before(r,r['rgb_quality']) for r in rows])
    z=np.array([after(r,r['rgb_quality'],r['scores']['direct']['action'],r['scores']['always']['action']) for r in rows])
    y=np.array([int(r['scores']['always']['success'])-int(r['scores']['direct']['success']) for r in rows])
    accepted=np.zeros(len(rows),bool)
    for batch in np.unique(b):
        valid=b==batch
        accepted[valid]=forecast(fit(z[~valid],y[~valid]),z[valid])>0
    pre=fit(x,y*accepted)
    post=fit(z,y)
    cases={}
    for r in test:
        q=quality(HERE/'frames'/(r['id']+'.jpg'))
        cases[r['id']]=dict(batch=r['batch'],q=q,priority=float(forecast(pre,before(r,q))),gap=r['gap'],pitch=r['angle'],ranks={})
    for batch in range(30):
        ids=[key for key,v in cases.items() if v['batch']==batch]
        assert len(ids)==10
        for method,field,sign in [('risk','priority',-1),('clearance','gap',1),('view','pitch',-1)]:
            order=sorted(ids,key=lambda key:(sign*cases[key][field],hashlib.sha256(('r3:'+key).encode()).hexdigest()))
            for j,key in enumerate(order,1):
                cases[key]['ranks'][method]=j
    sources=[HERE/'protocol.txt',HERE/'policy.py',HERE/'manifest.json',HERE/'model_client.py',OLD/'case-outcomes.json']
    record=dict(measurement_model=pre,acceptance_model=post,cases=cases,sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources})
    (HERE/'policy-lock.json').write_text(json.dumps(record,indent=2))
if __name__=='__main__':
    lock()
