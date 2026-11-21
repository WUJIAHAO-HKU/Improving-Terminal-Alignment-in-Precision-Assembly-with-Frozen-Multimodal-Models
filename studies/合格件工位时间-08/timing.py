"""Time the deployed RGB-only geometry path and the small Sol policy overhead."""
from pathlib import Path
import hashlib,json,math,platform,sys,time
import numpy as np
import cv2

D=Path(__file__).resolve().parent
P=D.parent/'工位补充实验-05'
G=D.parent/'几何纠偏基线-07'
sys.path.extend([str(G),str(P)])
import geometry as geo
from rules4 import pre,post,forecast,quality

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))
def save(path,obj):
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf8')
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
def rgb_only(path,r,lock):
    im=cv2.imdecode(np.fromfile(path,dtype=np.uint8),cv2.IMREAD_COLOR)
    theta=math.radians(r['angle'])
    co,si=math.cos(theta),math.sin(theta)
    top,side=geo.color_classes(im,r['task'])
    hole,match=geo.fit_hole(top,r['task'],theta)
    hu=geo.project(hole[None,:2],hole[2],co,si)[0]
    try:
        peg,_,_=geo.fit_peg(top,side,r['task'],r['gap'],theta,hole,lock['prior'][r['task']],None)
    except ValueError:
        return [0.,0.]
    if match<=.14:
        return [0.,0.]
    pu=geo.project(peg[None,:2],peg[2],co,si)[0]
    move=geo.ray(pu,co,si)*peg[2]-geo.ray(hu,co,si)*hole[2]
    bx,by=lock['calibration'][r['task']+'rgb']
    return move-[bx,by*math.tan(theta)]

def main():
    gl=read(G/'lock.json'); assert sha(G/'geometry.py')==gl['hashes'][str(G/'geometry.py')]
    policy=read(P/'policy-lock.json');ref=read(P/'study-lock.json')['ref']
    golden=read(G/'actions.json');obs={r['id']:r for r in read(P/'case-outcomes.json')}
    thresholds={}
    for b in read(P/'decisions.json')['batches']:
        for k in (6,8):
            left=k
            for j,i in enumerate(b['orders']['natural']):
                rem=10-j
                thresholds[i,k]=(left,rem,i in b['selections'][str(k)]['stream_natural'])
                left-=int(thresholds[i,k][2])
    keyed={i:[] for i in golden};rng=np.random.default_rng(921840)
    ids=sorted(golden);nrep=3
    rgb_only(P/'frames'/(ids[0]+'.jpg'),obs[ids[0]],gl)
    for rep in range(nrep):
        for i in rng.permutation(ids):
            r=obs[i];path=P/'frames'/(i+'.jpg')
            t=time.perf_counter();a=rgb_only(path,r,gl);geo_s=time.perf_counter()-t
            assert np.allclose(a,golden[i]['rgb'],atol=1e-6,rtol=0),(i,a,golden[i]['rgb'])
            d=r['outcomes']['direct']['action'];m=r['outcomes']['always']['action']
            t=time.perf_counter();q=quality(path);q_s=time.perf_counter()-t
            t=time.perf_counter();v=forecast(policy['pre'],pre(r,q,d,policy['limit']));pre_s=time.perf_counter()-t
            assert abs(v-r['score'])<1e-8
            overhead={}
            for k in (6,8):
                l,n,used=thresholds[i,k];t=time.perf_counter()
                chosen=bool(l and (l==n or v>=np.quantile(ref,1-l/n)))
                overhead[str(k)]=time.perf_counter()-t
                assert chosen==used
            t=time.perf_counter();g=forecast(policy['post'],post(r,q,d,m,policy['limit']))>0;post_s=time.perf_counter()-t
            assert g==r['accept']
            keyed[i].append([geo_s,q_s,pre_s,overhead['6'],overhead['8'],post_s])
    save(D/'timing.json',dict(fields=['geo','quality','pre','quota6','quota8','post'],replicates=nrep,
         host=platform.processor(),opencv=cv2.__version__,raw=keyed))
if __name__=='__main__':main()

