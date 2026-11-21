from pathlib import Path
import cv2,json,numpy as np
from recipe_info import spec
from camera import xy,camera
D=Path(__file__).resolve().parent
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,v):Path(p).write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf8')
def pose(p,a):
    return [float(np.clip(p[0],-102,102)),float(np.clip(p[1],-62,62)),float(np.clip(a,-80,80))]
def angle(vec):return (np.degrees(np.arctan2(vec[1],vec[0]))+90)%180-90
def targets(r,anchor):
    ref=spec(r);ang=anchor[2];u=np.array([np.cos(np.radians(ang)),np.sin(np.radians(ang))])
    return [pose(np.array(anchor[:2])+{'M':0,'LR':0,'L':-1,'R':1}[v['column']]*r['span']/2*u,ang) for v in ref]
def markers(r):
    return len({v['column'] for v in spec(r)} & {'L','R','LR'})>0 or any(v['profile']=='double' for v in spec(r))
def geometry(r,cam,mode):
    # All placement arms share the model-defined grasps; geometric method only estimates mating station frame.
    d=D/'observations'/r['id'];im=cv2.imdecode(np.fromfile(d/f'initial-{cam}.jpg',np.uint8),1)
    B,G,R=im.astype(float).transpose(2,0,1);mask=(R>1.20*B)&(R>1.08*G)&(R>28)
    z=spec(r)[0]['pin_top']
    if mode=='depth':
        dep=np.load(d/'initial-depth.npy');xyz,back,right,up,f=camera(cam);v,u=np.indices(mask.shape)
        zz=xyz[2]+(-back[2]+(u-239.5)/f*right[2]+(179.5-v)/f*up[2])*dep
        mask &= (zz>z-2)&(zz<z+1)
    cc,_=cv2.findContours(mask.astype('uint8'),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)
    p=[xy(x.reshape(-1,2),z,cam) for x in cc if cv2.contourArea(x)>=7]
    default=[43.,3.,0.]
    if not p:return default,False
    if markers(r):
        pts=[(v.min(0)+v.max(0))/2 for v in p]
        cand=[(abs(np.linalg.norm(q-v)-r['span']),q,v) for j,v in enumerate(pts) for q in pts[j+1:] if abs(angle(q-v))<26]
        if not cand:return default,False
        loss,q,v=min(cand,key=lambda e:e[0])
        if loss>9:return default,False
        return pose((v+q)/2,angle(q-v)),True
    pts=max(p,key=len);center=(pts.max(0)+pts.min(0))/2
    # For a single source with circular symmetry yaw is immaterial. Otherwise fit the outline.
    if all(v['profile']=='round' for v in spec(r)):a=0.
    else:
        def loss(a):
            t=np.radians(a);q=(pts-center)@np.array([[np.cos(t),-np.sin(t)],[np.sin(t),np.cos(t)]])
            return float(np.std(q[q[:,0]>=np.quantile(q[:,0],.78),0]) if any(v['profile']=='dflat' for v in spec(r)) else np.prod(np.ptp(q,axis=0)))
        a=min(np.arange(-16.,17.),key=loss)
    return pose(center,a),True
def discrepancy(a,b,r):return float(np.linalg.norm(np.subtract(a[:2],b[:2]))+r['span']/2*np.radians(abs(a[2]-b[2])))
def branches(model):
    rows=read(D/'scenes.json');allplans={};ch={}
    for r in rows:
        i=r['id'];d=D/'responses'/model
        get=lambda n:read(d/f'{i}-{n}.json')
        first=get('prefix');source=first['picks']
        g,ok=geometry(r,'eye','first');gd,od=geometry(r,'eye','depth');gt,ot=geometry(r,'top','overhead')
        anc={k:get(k)['anchor'] for k in ('first','repeat','depth','overhead')}
        refs={'repeat':g,'depth':gd if od else g,'overhead':gt if ot else g}
        ch[i]=dict(batch=r['batch'],pre=discrepancy(anc['first'],g,r)/r['gap'] if ok else 1e6,accept={k:discrepancy(anc[k],v,r)<discrepancy(anc['first'],v,r) for k,v in refs.items()})
        anc.update(geometry=g,geometry_depth=refs['depth'],geometry_top=refs['overhead'])
        allplans[i]={k:[dict(op='assemble',pick=source[j],place=a) for j,a in enumerate(targets(r,v)) if j>0] for k,v in anc.items()}
    for b in sorted({r['batch'] for r in rows}):
        for rank,i in enumerate(sorted([i for i in ch if ch[i]['batch']==b],key=lambda i:(-ch[i]['pre'],i)),1):ch[i]['rank']=rank
    save(D/(model+'-choices.json'),ch);save(D/(model+'-plans.json'),allplans)

