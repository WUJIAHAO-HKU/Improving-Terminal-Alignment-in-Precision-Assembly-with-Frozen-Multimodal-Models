"""Calibrated natural-contour geometry and blind, modality-specific acceptance estimates."""
import cv2,numpy as np
def camera(cam):
    xyz=np.array([6,-205,239] if cam=='eye' else [0,0,294],float)
    back=xyz-np.array([0,0,5] if cam=='eye' else [0,0,0]);back/=np.linalg.norm(back)
    right=np.cross([0,0,1],back);right=right/np.linalg.norm(right) if np.linalg.norm(right)>1e-8 else np.array([1.,0,0])
    return xyz,back,right,np.cross(back,right),180/np.tan(np.radians(38 if cam=='eye' else 37)/2)
def xy(pts,z,cam):
    xyz,back,right,up,f=camera(cam);p=np.asarray(pts)
    ray=-back+(p[:,0,None]-239.5)/f*right+(179.5-p[:,1,None])/f*up
    return xyz[:2]+ray[:,:2]*(z-xyz[2])/ray[:,2,None]
def pose(x,y,a):return dict(x=round(float(np.clip(x,-92,92)),3),y=round(float(np.clip(y,-57,57)),3),yaw=round(float(np.clip(a,-75,75)),3))
def answer(q):
    values=np.asarray([float(q[k]) for k in ('x','y','yaw')]);assert np.isfinite(values).all();return pose(*values)
def geometry(img,r,cam='eye',depth=None):
    im=cv2.imread(str(img));B,G,R=im.astype(float).transpose(2,0,1)
    mask=((R>1.22*B)&(R>1.10*G)&(R>27)).astype('uint8')
    if depth is not None:
        xyz,back,right,up,f=camera(cam);v,u=np.indices(mask.shape)
        rayz=-back[2]+(u-239.5)/f*right[2]+(179.5-v)/f*up[2]
        z=xyz[2]+rayz*depth;mask &= ((z>=12)&(z<=15)).astype('uint8')
    cc,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)
    cc=[c for c in cc if cv2.contourArea(c)>=7];task=r['task']
    fallback=pose(41,(-18 if r['port']=='near' else 19) if task=='connector' else 0,0)
    if not cc:return fallback,False
    cloud=[xy(c.reshape(-1,2),14,cam) for c in cc]
    if task in ('twin','connector'):
        pts=[(s.min(0)+s.max(0))/2 for s in cloud]
        candidates=[]
        for i,p in enumerate(pts):
            for q in pts[i+1:]:
                d=q-p;mid=(q+p)/2;theta=(np.degrees(np.arctan2(d[1],d[0]))+90)%180-90
                if abs(np.linalg.norm(d)-r['size'])>8 or abs(theta)>32:continue
                candidates.append((mid,theta,abs(np.linalg.norm(d)-r['size'])))
        if not candidates:return fallback,False
        if task=='connector':
            candidates=sorted(candidates,key=lambda c:c[0][1])
            mid,theta,_=candidates[0 if r['port']=='near' else -1]
        else:mid,theta,_=min(candidates,key=lambda c:c[2])
    else:
        pts=max(cloud,key=len);mid=(pts.max(0)+pts.min(0))/2
        angles=np.arange(-20.,21.,1)
        def mismatch(a):
            co,si=np.cos(np.radians(a)),np.sin(np.radians(a));t=(pts-mid)@np.array([[co,-si],[si,co]])
            if task=='blade':return np.prod(np.ptp(t,axis=0))
            # Low projection variance on the positive-X flat of the D profile.
            edge=t[:,0]>=np.quantile(t[:,0],.78);return np.std(t[edge,0])
        theta=min(angles,key=mismatch)
    return pose(*mid,theta),True
def diff(a,b,r):
    return float(np.hypot(a['x']-b['x'],a['y']-b['y'])+r['size']*.5*np.radians(abs(a['yaw']-b['yaw'])))
def public(r):return dict(task=r['task'],size=r['size'],gap=r['gap'],width=r['width'],radius=r['radius'],port=('near' if r['other_y']>0 else 'far') if r['task']=='connector' else '')

