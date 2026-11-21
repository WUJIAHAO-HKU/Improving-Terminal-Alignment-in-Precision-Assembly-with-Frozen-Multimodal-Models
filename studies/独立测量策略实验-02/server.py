"""Second experiment. Each manufacturing batch has 10 newly seeded parts."""
from rig_base import Rig as BaseRig, GAPS, TASKS, W, D, dump, read
import numpy as np
from PIL import Image
from robosuite.utils.camera_utils import get_real_depth_map
import hashlib, math, sys
ANGLES=[8,14,26,38,45]
def samples():
    rows=[]
    for batch in range(30):
        br=np.random.default_rng(671900+batch)
        ts=list(np.repeat(TASKS,3))+[str(br.choice(TASKS))]
        angles=list(np.repeat(ANGLES,2)); gaps=list(np.repeat(GAPS,2))
        br.shuffle(ts);br.shuffle(angles);br.shuffle(gaps)
        for j in range(10):
            seed=59211000+batch*10+j
            rng=np.random.default_rng(seed);x,y=rng.uniform(-16,16,2);cx,cy=rng.uniform(-18,18,2)
            mount=float(rng.uniform(10,42));hover=float(rng.uniform(36,50))
            rows.append(dict(id=f'B{batch:02d}P{j:02d}',task=str(ts[j]),batch=batch,k=j,seed=seed,gap=float(gaps[j]),angle=float(angles[j]),height=hover,mount=mount,x=float(x),y=float(y),camx=float(cx),camy=float(cy),split='test'))
    return rows
class Rig(BaseRig):
    def __init__(self,task,g):
        super().__init__(task,g)
        self.nominal_center=self.center.copy()
        if not self.dual:self.body0=self.s.model.body_pos[self.pid].copy()
    def pose(self,r,dx=0,dy=0,h=None,tilt=0):
        # Move the physical fixture within the anchored table; camera stays calibrated to workcell.
        self.center=self.nominal_center.copy();self.center[2]+=r['mount']/1000
        if not self.dual:
            self.s.model.body_pos[self.pid]=self.body0+[0,0,r['mount']/1000]
        super().pose(r,dx,dy,h,tilt)
        self.s.model.cam_pos[self.cam,2]-=r['mount']/1000
        self.s.forward()
        if not self.dual:
            gid=self.s.model.body_geomadr[self.pid]
            assert abs(self.s.data.geom_xpos[gid,2]+self.s.model.geom_size[gid,1 if self.task=='round' else 2]-self.center[2])<1e-7
    def render(self,r):
        self.pose(r);s=self.s
        rgb,depth=s.render(width=W,height=W,camera_name=self.cam_name,depth=True)
        rgb=rgb[::-1].copy();depth=get_real_depth_map(s,depth)[::-1].copy()
        a=math.radians(r['angle']);f=W/2/math.tan(math.radians(15))
        yy,xx=np.indices(depth.shape);v=(yy-(W-1)/2)/f
        levels=depth*(np.cos(a)+v*np.sin(a))*1000
        levels+=np.random.default_rng(r['seed']+660).normal(0,.65,levels.shape)
        crop=(abs(xx-(W-1)/2)<W*.37)&(abs(yy-(W-1)/2)<W*.37)
        z0=(500 if self.dual else 360)*np.cos(a)
        # Fixed broad search range for the whole cell, with no scene-specific fixture heights.
        edges=np.arange(math.floor(z0-125),math.ceil(z0+17),.5)
        hist,ee=np.histogram(levels[crop],edges);sm=np.convolve(hist,[1,2,3,2,1],mode='same');mid=(ee[:-1]+ee[1:])/2
        first=mid[np.argmax(sm)];second=mid[np.argmax(np.where(abs(mid-first)>12,sm,-1))]
        near,far=sorted([float(first),float(second)])
        Image.fromarray(rgb).save(D/'frames'/(r['id']+'.jpg'),quality=93)
        return dict(near=near,far=far,fov=30,width=W)
def main():
    cmd=sys.argv[1];rows=samples();out=[]
    if cmd=='score':actions=read('actions.json')
    for t in TASKS:
        for g in GAPS:
            rig=Rig(t,g)
            for r in rows:
                if r['task']!=t or r['gap']!=g:continue
                if cmd=='render':
                    r['depth']=rig.render(r);out.append(r)
                else:
                    for m,act in actions[r['id']].items():out.append(dict(id=r['id'],mode=m,**rig.rollout(r,*act)))
            rig.e.close();print(cmd,t,g,len(out),flush=True)
    dump('manifest.json' if cmd=='render' else 'scores.json',out)
if __name__=='__main__':main()

