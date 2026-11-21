import math, hashlib, json
from pathlib import Path
import numpy as np
from PIL import Image
D=Path(__file__).resolve().parent
METHODS=['clearance','view','joint','fit_clearance','fit_view']
BUDGETS=[9,8,7,6,5,4,3]
def quality(path):
    # RMS of horizontal/vertical photometric gradients over the central half of the initial RGB.
    im=np.asarray(Image.open(path).convert('L'),dtype=float);im=im[80:240,80:240]/255
    return math.log(.005+math.sqrt((np.mean(np.diff(im,axis=0)**2)+np.mean(np.diff(im,axis=1)**2))/2))
def features(r,q,method):
    small=math.log2(2/r['gap']);ob=math.tan(math.radians(r['angle']))
    return {'fit_clearance':[small,small**2],'fit_view':[ob], 'joint':[small,small**2,ob,q,small*ob,ob*q]}[method]
def train(old):
    rows=json.loads((old/'test-outcomes.json').read_text());w={}
    for m in ['fit_clearance','fit_view','joint']:
        X=np.array([features(r,quality(old/'frames'/(r['id']+'.jpg')),m) for r in rows])
        y=np.array([int(r['outcomes']['always']['success'])-int(r['outcomes']['direct']['success']) for r in rows])
        mu=X.mean(0);sd=np.maximum(X.std(0),.00001);X=(X-mu)/sd
        coef=np.linalg.solve(X.T@X+12*np.eye(X.shape[1]),X.T@(y-y.mean()))
        w[m]=dict(mu=mu.tolist(),sd=sd.tolist(),coef=coef.tolist(),intercept=float(y.mean()))
    (D/'locked-weights.json').write_text(json.dumps(w,indent=2))
def rankings(rows):
    w=json.loads((D/'locked-weights.json').read_text());out=[]
    for r in rows:
        q=quality(D/'frames'/(r['id']+'.jpg'))
        score={'clearance':-r['gap'],'view':r['angle']}
        for m,v in w.items():
            z=(np.array(features(r,q,m))-v['mu'])/v['sd']
            score[m]=float(z@v['coef']+v['intercept'])
        tie=hashlib.sha256(('tie-v2a:'+r['id']).encode()).hexdigest()
        out.append(dict(id=r['id'],batch=r['batch'],quality=q,scores=score,tie=tie,ranks={}))
    for b in range(30):
        for m in METHODS:
            order=sorted((r for r in out if r['batch']==b),key=lambda r:(-r['scores'][m],r['tie']))
            assert len(order)==10
            for j,r in enumerate(order):r['ranks'][m]=j+1
    return out
if __name__=='__main__':
    import sys
    if sys.argv[1]=='train':train(Path(sys.argv[2]))
    else:(D/'locked-ranks.json').write_text(json.dumps(rankings(json.loads((D/'manifest.json').read_text())),indent=2))

