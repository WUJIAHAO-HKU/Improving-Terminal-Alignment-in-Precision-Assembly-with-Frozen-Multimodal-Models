"""Independent, seeded terminal assembly experiment. SI units internally; exported distances in mm."""
import sys, json, math, random, pathlib, hashlib
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image
import robosuite as suite
from robosuite.utils.camera_utils import get_real_depth_map
from robosuite.controllers import load_controller_config

D=pathlib.Path('.'); (D/'frames').mkdir(exist_ok=True)
GAPS=[4,2,1,.5,.25]; TASKS=['square','round','dual']
N=8
W=320
def dump(p,obj): pathlib.Path(p).write_text(json.dumps(obj,indent=2),encoding='utf-8')
def read(p): return json.loads(pathlib.Path(p).read_text(encoding='utf-8'))
def samples():
    rows=[]
    for task in TASKS:
        for split,n,seed in [('cal',4,708713),('test',N,948371)]:
            for k in range(n):
                seed_i=seed+TASKS.index(task)*991+k+(87011 if task=='round' else 0)
                rg=np.random.default_rng(seed_i)
                x,y=rg.uniform(-15,15,2); drift=rg.uniform(-18,18,2)
                a=float(rg.choice([0,20,32])); height=float(rg.uniform(12,34))
                for g in GAPS:
                    rows.append(dict(id=f'{task}-{split}-{k:02d}-{str(g).replace(".","p")}',task=task,split=split,k=k,seed=seed_i,gap=g,x=x,y=y,camx=drift[0],camy=drift[1],angle=a,height=height))
    return rows
class Rig:
    def __init__(self,task,g):
        self.task=task;self.g=g;self.dual=task=='dual'
        name={'square':'NutAssemblySquare','round':'NutAssemblyRound','dual':'TwoArmPegInHole'}[task]
        np.random.seed(145)
        self.e=suite.make(name,robots=['Panda','Panda'] if self.dual else 'Panda',has_renderer=False,has_offscreen_renderer=True,use_camera_obs=False,controller_configs=load_controller_config(default_controller='OSC_POSE'))
        e=self.e;e.reset(); xml=ET.fromstring(e.model.get_xml())
        if self.dual:
            # Terminal held-parts fixture: preserve native plate + cylinder and robot bodies.
            # Position the held pieces relative to fixed flange poses, avoiding IK/grasp errors in this diagnostic.
            self.radius=50.; self.cam_name='agentview';self.center=np.array([0.,0.,1.35])
            for bname in [e.peg.root_body,e.hole.root_body]:
                par=next(p for p in xml.iter() if any(c.get('name')==bname and c.tag=='body' for c in p))
                body=next(c for c in par if c.get('name')==bname and c.tag=='body')
                par.remove(body);xml.find('worldbody').append(body);body.set('mocap','true');body.set('quat','1 0 0 0');body.set('pos','0 0 1.35')
                if bname==e.peg.root_body:
                    for gg in body.iter('geom'):
                        size=gg.get('size').split();size[0]=str((50-g)/1000);gg.set('size',' '.join(size))
        else:
            self.radius=22.75 if task=='square' else min(31.2,30*math.sqrt(2)-11.25)
            self.cam_name='birdview'; self.pegname='peg1' if task=='square' else 'peg2'
            for gg in xml.findall(".//body[@name='%s']/geom"%self.pegname):
                size=gg.get('size').split();size[0]=str((self.radius-g)/1000)
                if task=='square':size[1]=size[0]
                gg.set('size',' '.join(size))
        e.reset_from_xml_string(ET.tostring(xml,encoding='unicode'));self.s=s=e.sim;self.state=s.get_state()
        self.cam=s.model.camera_name2id(self.cam_name);s.model.cam_fovy[self.cam]=30
        if self.dual:
            self.pid=e.peg_body_id;self.hid=e.hole_body_id
            self.pm=s.model.body_mocapid[self.pid];self.hm=s.model.body_mocapid[self.hid]
            self.half=s.model.geom_size[s.model.body_geomadr[self.pid],1]
        else:
            self.pid=s.model.body_name2id(self.pegname);self.nut=next(n for n in e.nuts if task.capitalize() in n.name)
            self.hid=e.obj_body_id[self.nut.name];gid=s.model.body_geomadr[self.pid]
            self.center=s.data.body_xpos[self.pid].copy()
            half_height=s.model.geom_size[gid,1 if task=='round' else 2]
            assert abs(half_height-.1)<1e-7
            self.center[2]=s.data.geom_xpos[gid,2]+half_height
    def pose(self,r,dx=0,dy=0,h=None,tilt=0):
        s=self.s;s.set_state(self.state);off=np.array([r['x']+dx,r['y']+dy,0])/1000
        hh=r['height']/1000 if h is None else h
        q=np.array([np.cos(tilt/2),np.sin(tilt/2),0,0])
        if self.dual:
            s.data.mocap_pos[self.pm]=self.center-[0,0,self.half];s.data.mocap_quat[self.pm]=[1,0,0,0]
            s.data.mocap_pos[self.hm]=self.center+off+[-.11,0,hh];s.data.mocap_quat[self.hm]=q
        else:
            s.data.set_joint_qpos(self.nut.joints[0],np.r_[self.center+off+[0,0,hh],q]);s.data.set_joint_qvel(self.nut.joints[0],np.zeros(6))
        a=math.radians(r['angle']);dist=.50 if self.dual else .36
        s.model.cam_pos[self.cam]=self.center+np.array([r['camx']/1000,r['camy']/1000-dist*np.sin(a),dist*np.cos(a)])
        s.model.cam_quat[self.cam]=[np.cos(a/2),np.sin(a/2),0,0];s.forward()
    def render(self,r):
        self.pose(r);s=self.s
        rgb,depth=s.render(width=W,height=W,camera_name=self.cam_name,depth=True)
        rgb=rgb[::-1].copy();depth=get_real_depth_map(s,depth)[::-1].copy()
        # Estimate top planes from RGB-D pixels and nominal camera pitch. No object masks or object poses in estimator.
        a=math.radians(r['angle']);f=W/2/math.tan(math.radians(15))
        yy,xx=np.indices(depth.shape);v=(yy-(W-1)/2)/f
        levels=depth*(np.cos(a)+v*np.sin(a))*1000
        rng=np.random.default_rng(r['seed']+660);levels+=rng.normal(0,.65,levels.shape)
        crop=(abs(xx-(W-1)/2)<W*.37)&(abs(yy-(W-1)/2)<W*.37)
        # Search near nominal working distance; top surfaces are the two dominant separated planes within this band.
        z0=(500 if self.dual else 360)*np.cos(a)
        edges=np.arange(math.floor(z0-63),math.ceil(z0+17),.5);hist,ee=np.histogram(levels[crop],edges)
        sm=np.convolve(hist,[1,2,3,2,1],mode='same');mid=(ee[:-1]+ee[1:])/2
        first=mid[np.argmax(sm)];mask=abs(mid-first)>12;second=mid[np.argmax(np.where(mask,sm,-1))]
        near,far=sorted([first,second])
        Image.fromarray(rgb).save(D/'frames'/(r['id']+'.jpg'),quality=93)
        return dict(near=round(float(near),2),far=round(float(far),2),fov=30,width=W)
    def geometry(self):
        s=self.s;pos=s.data.body_xpos[self.hid].copy();rot=s.data.body_xmat[self.hid].reshape(3,3);tilt=math.degrees(math.acos(np.clip(rot[2,2],-1,1)))
        if self.dual:pos+=rot@np.array([.11,0,0])
        xy=(pos-self.center)[:2]*1000
        h=(pos[2]-(self.center[2] if self.dual else self.e.table_offset[2]))*1000
        if self.task=='round':lat=np.linalg.norm(xy)
        else:lat=max(abs(xy))
        valid=bool(lat<=self.g+.35 and tilt<4 and ((-38<h<-25) if self.dual else (8<h<12.5)))
        return valid,h,lat,tilt
    def rollout(self,r,dx,dy,substeps=450):
        self.pose(r,dx,dy);s=self.s
        if self.dual:
            # Contact-arrested descent for two held rigid bodies. Simulation fixture, not a bimanual controller.
            stop=False
            for h in np.arange(r['height'], -32.1,-.25):
                s.data.mocap_pos[self.hm,2]=self.center[2]+h/1000;s.forward()
                for con in s.data.contact[:s.data.ncon]:
                    b={s.model.geom_bodyid[con.geom1],s.model.geom_bodyid[con.geom2]}
                    if b=={self.pid,self.hid} and con.dist<-.00015:stop=True;break
                if stop:break
                # MuJoCo filters mocap/mocap contacts; geometric overlap at plate entrance also arrests feed.
                if h<=10 and max(abs(r['x']+dx),abs(r['y']+dy))>self.g:break
            stable=True
        else:
            for _ in range(substeps-50):s.step()
            prev=s.data.body_xpos[self.hid].copy()
            for _ in range(50):s.step()
            stable=np.linalg.norm(s.data.body_xpos[self.hid]-prev)<.001
        ok,h,lat,tilt=self.geometry()
        return dict(success=bool(ok and stable),official=bool(self.e._check_success()),height=round(float(h),2),lateral=round(float(lat),2),tilt=round(float(tilt),2),stable=bool(stable))
    def fixtures(self,r):
        out=[]
        for label,xy,h,tilt in [('seated',0,-.032 if self.dual else self.e.table_offset[2]+.010-self.center[2],0),('hover',0,.030,0),('partial',0,-.012,0),('tilted',0,.010,.22),('miss',80,-.032 if self.dual else self.e.table_offset[2]+.010-self.center[2],0)]:
            self.pose(r,xy-r['x'],-r['y'],h,tilt)
            ok,z,l,a=self.geometry();out.append(dict(task=self.task,gap=self.g,label=label,expected=label=='seated',strict=ok,official=bool(self.e._check_success()),height=z))
        return out
def main():
    cmd=sys.argv[1];allrows=samples();output=[];fx=[]
    if cmd=='score':actions=read('actions.json')
    for task in ([sys.argv[2]] if len(sys.argv)>2 else TASKS):
        for g in GAPS:
            rig=Rig(task,g);rows=[r for r in allrows if r['task']==task and r['gap']==g]
            if cmd=='render':
                fx+=rig.fixtures(rows[0])
                for r in rows:r['depth']=rig.render(r);output.append(r)
            else:
                for r in rows:
                    if r['id'] not in actions:continue
                    for mode,act in actions[r['id']].items():
                        out=rig.rollout(r,*act);output.append(dict(id=r['id'],mode=mode,**out))
            rig.e.close()
            print(cmd,task,g,len(output),flush=True)
    if cmd=='render':dump('manifest.json',output);dump('fixtures.json',fx)
    else:dump('scores.json',output)
if __name__=='__main__':main()

