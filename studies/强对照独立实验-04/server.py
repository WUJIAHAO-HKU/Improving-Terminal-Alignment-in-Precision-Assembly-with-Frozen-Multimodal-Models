"""Round 4 independent strong-control validation."""
from rig_base import Rig as BaseRig,GAPS,TASKS,W,D,dump,read
import numpy as np,math,sys
from PIL import Image
from robosuite.utils.camera_utils import get_real_depth_map
N=10
def samples():
 rows=[]
 for batch in range(40):
  rg=np.random.default_rng(843211+batch);tasklist=list(np.repeat(TASKS,3))+[str(rg.choice(TASKS))];rg.shuffle(tasklist)
  for j in range(10):
   seed=83541100+batch*10+j;x,y=rg.uniform(-17,17,2);gap=float(rg.choice(GAPS,p=[.25,.25,.2,.2,.1]));angle=float(rg.choice([5,11,23,35,43,49]));mount=float(rg.uniform(6,48));height=float(rg.uniform(34,52));cx,cy=rg.uniform(-20,20,2)
   rows.append(dict(id=f'D{batch:02d}P{j:02d}',task=tasklist[j],batch=batch,k=j,seed=seed,x=float(x),y=float(y),gap=gap,angle=angle,mount=mount,height=height,camx=float(cx),camy=float(cy),split='test'))
 return rows
class Rig(BaseRig):
 def __init__(self,task,g):super().__init__(task,g);self.nominal_center=self.center.copy();self.body0=None if self.dual else self.s.model.body_pos[self.pid].copy()
 def pose(self,r,dx=0,dy=0,h=None,tilt=0):
  self.center=self.nominal_center.copy();self.center[2]+=r['mount']/1000
  if not self.dual:self.s.model.body_pos[self.pid]=self.body0+[0,0,r['mount']/1000]
  super().pose(r,dx,dy,h,tilt);self.s.model.cam_pos[self.cam,2]-=r['mount']/1000;self.s.forward()
 def render(self,r):
  self.pose(r);s=self.s;rgb,depth=s.render(width=W,height=W,camera_name=self.cam_name,depth=True);rgb=rgb[::-1].copy();depth=get_real_depth_map(s,depth)[::-1].copy()
  a=math.radians(r['angle']);f=W/2/math.tan(math.radians(15));yy,xx=np.indices(depth.shape);v=(yy-(W-1)/2)/f
  levels=depth*(math.cos(a)+v*math.sin(a))*1000+np.random.default_rng(r['seed']+333).normal(0,.8,depth.shape)
  crop=(abs(xx-(W-1)/2)<W*.37)&(abs(yy-(W-1)/2)<W*.37);z0=(500 if self.dual else 360)*math.cos(a)
  edges=np.arange(math.floor(z0-145),math.ceil(z0+18),.5);hist,ee=np.histogram(levels[crop],edges);sm=np.convolve(hist,[1,2,3,2,1],mode='same');mid=(ee[:-1]+ee[1:])/2;first=mid[np.argmax(sm)];second=mid[np.argmax(np.where(abs(mid-first)>12,sm,-1))];near,far=sorted([float(first),float(second)])
  Image.fromarray(rgb).save(D/'frames'/(r['id']+'.jpg'),quality=93);return dict(near=near,far=far,fov=30,width=W)
def main():
 cmd=sys.argv[1];rows=samples();out=[];acts=read('actions.json') if cmd=='score' else {}
 for t in TASKS:
  for g in GAPS:
   rig=Rig(t,g)
   for r in rows:
    if r['task']!=t or r['gap']!=g:continue
    if cmd=='render':r['depth']=rig.render(r);out.append(r)
    else:
     for m,a in acts[r['id']].items():out.append(dict(id=r['id'],mode=m,**rig.rollout(r,*a)))
   rig.e.close();print(cmd,t,g,len(out),flush=True)
 dump('manifest.json' if cmd=='render' else 'scores.json',out)
if __name__=='__main__':main()

