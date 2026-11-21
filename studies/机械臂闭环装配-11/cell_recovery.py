"""MuJoCo millimetre task interface for a physical XYZ-theta Cartesian assembly robot."""
import sys, json, math, os, subprocess, shutil
from pathlib import Path
import xml.etree.ElementTree as E
import numpy as np
import mujoco as mj
from PIL import Image
ROOT=Path(__file__).resolve().parent
def val(a):return ' '.join('%.9g'%x for x in a)
def pt(a):return val(np.asarray(a)/1000)
def add(parent,tag,**kw):return E.SubElement(parent,tag,{k:str(v) for k,v in kw.items()})
def box(p,name,xyz,half,color,**kw):return add(p,'geom',name=name,type='box',pos=pt(xyz),size=pt(half),rgba=color,**kw)
MET='.28 .35 .39 1';AL='.62 .67 .68 1';BLUE='.24 .36 .46 1';GOLD='.67 .49 .27 1'
def build(scene):
    h=scene['gap']; halfsep=scene['pitch_mm']/2
    root=E.Element('mujoco');add(root,'compiler',angle='degree');add(root,'option',timestep='.001',integrator='implicitfast',iterations='60',gravity='0 0 -9.81')
    v=add(root,'visual');add(v,'global',offwidth=640,offheight=480);add(v,'map',znear='.004')
    default=add(root,'default');add(default,'geom',friction='1.5 .015 .0001',solref='.004 1',solimp='.95 .99 .001',condim='4')
    asset=add(root,'asset');world=add(root,'worldbody')
    add(world,'light',pos='.18 -.19 .32',dir='-.4 .4 -1',diffuse='.85 .85 .85',castshadow='true')
    add(world,'light',pos='-.17 -.08 .2',dir='.3 .1 -1',diffuse='.36 .36 .36',castshadow='false')
    box(world,'table',(0,0,-4),(145,105,4),'.34 .36 .38 1')
    for sign in (-1,1):
        box(world,'column'+str(sign),(sign*112,55,78),(5,6,78),MET)
    box(world,'rail',(0,55,154),(117,5,6),AL)
    fixed=add(world,'body',name='fixture',pos=pt([scene['tx'],scene['ty'],0]),euler=val([0,0,scene['ta']]))
    box(fixed,'base',(0,0,2),(halfsep+13,17,2),MET)
    for j,x in enumerate([-halfsep,halfsep]):
        add(fixed,'geom',name=f'pin{j}',type='cylinder',pos=pt([x,0,9]),size=pt([4,5]),rgba=GOLD)
    slide=add(world,'body',name='xcar',pos='0 0 .148')
    actuators=add(root,'actuator')
    def joint(body,n,axis,rng,kp,kv,typ='slide',force=200):
        add(body,'joint',name=n,type=typ,axis=axis,range=rng,damping='0.03',armature='.00005' if typ=='hinge' else '.005')
        add(actuators,'position',name=n,joint=n,kp=kp,kv=kv,forcerange=f'{-force} {force}')
    def decor(body,n,pos,size,color):box(body,n,pos,size,color,contype='0',conaffinity='0')
    joint(slide,'x','1 0 0','-.105 .105',7500,65);decor(slide,'xrail',(0,4,0),(4,68,4),AL)
    y=add(slide,'body',name='ycar');joint(y,'y','0 1 0','-.065 .065',7500,60);decor(y,'ycarriage',(0,0,-5),(7,8,6),BLUE)
    z=add(y,'body',name='zcar');joint(z,'z','0 0 1','-.148 -.034',7500,48);decor(z,'vertical',(0,0,61),(3,3,41),AL)
    hand=add(z,'body',name='wrist');joint(hand,'yaw','0 0 1','-170 170',18,.3,'hinge',5)
    decor(hand,'palm',(0,0,15),(10,25,4),BLUE)
    for s,n in [(-1,'left'),(1,'right')]:
        finger=add(hand,'body',name=n,pos=pt([0,s*23,0]))
        joint(finger,n,('0 1 0' if s==-1 else '0 -1 0'),'0 .016',1500,3,force=12)
        box(finger,n+'pad',(0,0,5),(8,1.8,6.8),'.13 .13 .14 1',mass='.012')
    part=add(world,'body',name='cover',pos=pt([scene['sx'],scene['sy'],3.04]),euler=val([0,0,scene['sa']]))
    add(part,'freejoint',name='free');add(part,'inertial',pos='0 0 0',mass='.042',diaginertia='.0000022 .000010 .000011')
    # The two through holes are actual voids. Convex wedges tile each surrounding cell.
    for j,sign in enumerate([-1,1]):
        cx=sign*halfsep
        a=np.unique(np.round(np.mod(np.r_[np.arange(24)*2*np.pi/24,[np.arctan2(dy*12,dx*halfsep) for dx in (-1,1) for dy in (-1,1)]],2*np.pi),8))
        rays=np.column_stack([np.cos(a),np.sin(a)]);outer=rays*np.min(np.array([halfsep,12])/np.maximum(np.abs(rays),1e-14),axis=1)[:,None]
        inner=rays*(4+h)
        for k in range(len(a)):
            l=(k+1)%len(a);quad=np.array([inner[k],outer[k],outer[l],inner[l]])+[cx,0]
            name=f'cover_{j}_{k}';vs=[[x,y,zz] for zz in (-3,3) for x,y in quad]
            add(asset,'mesh',name=name,vertex=pt(np.ravel(vs)));add(part,'geom',name=name,type='mesh',mesh=name,rgba=AL)
    for name,cam,aim,fov in [('eye',(6,-205,239),(0,0,5),38),('top',(0,0,294),(0,0,0),37),('video',(168,-300,195),(0,0,55),38)]:
        back=np.array(cam,dtype=float)-aim;back/=np.linalg.norm(back)
        right=np.cross([0,0,1],back);right=right/np.linalg.norm(right) if np.linalg.norm(right)>1e-8 else np.array([1.,0,0])
        up=np.cross(back,right);add(world,'camera',name=name,pos=pt(cam),xyaxes=val([*right,*up]),fovy=fov)
    model=mj.MjModel.from_xml_string(E.tostring(root,encoding='unicode'));return model,mj.MjData(model)
class Cell:
    def __init__(self,r,folder,step):
        self.r=r;self.dir=folder;folder.mkdir(exist_ok=True,parents=True);self.m,self.d=build(r);self.step=step
        self.ren=mj.Renderer(self.m,height=360,width=480)
        self.geom=[mj.mj_id2name(self.m,mj.mjtObj.mjOBJ_GEOM,i) for i in range(self.m.ngeom)]
        self.body=self.m.body('cover').id;self.samples=[];self.frame=0
        if step==0:
            self.d.qpos[:6]=[0,-.045,-.070,0,0,0];self.d.ctrl[:]=self.d.qpos[:6];mj.mj_forward(self.m,self.d)
        else:
            f=np.load(folder/'state.npz');spec=mj.mjtState.mjSTATE_INTEGRATION
            mj.mj_setState(self.m,self.d,f['state'],spec);mj.mj_forward(self.m,self.d)
        self.pipe=subprocess.Popen(['ffmpeg','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','480x360','-r','25','-i','-','-c:v','libx264','-threads','1','-pix_fmt','yuv420p','-preset','veryfast',str(folder/f'clip{step:02}.mp4')],stdin=subprocess.PIPE)
    def arm(self):return np.r_[self.d.qpos[:2]*1000,148+self.d.qpos[2]*1000,np.degrees(self.d.qpos[3])]
    def contacts(self):
        hits=set()
        for c in self.d.contact:
            a,b=self.geom[c.geom1],self.geom[c.geom2]
            if a.startswith('cover_'):hits.add(b)
            elif b.startswith('cover_'):hits.add(a)
        return hits
    def sample(self):
        rot=self.d.xmat[self.body].reshape(3,3);pos=self.d.xpos[self.body]*1000
        hits=self.contacts();self.samples.append(dict(t=round(self.d.time,4),arm=self.arm().round(3).tolist(),part=pos.round(3).tolist(),yaw=round(float(np.degrees(np.arctan2(rot[1,0],rot[0,0]))),3),left='leftpad' in hits,right='rightpad' in hits))
        self.ren.update_scene(self.d,camera='video');self.pipe.stdin.write(self.ren.render().tobytes())
    def move(self,pose,jaw,steps):
        start=self.d.ctrl.copy();x,y,z,a=pose;end=np.array([x/1000,y/1000,(z-148)/1000,np.radians(a),jaw,jaw])
        for j in range(steps):
            t=(j+1)/steps;u=t*t*(3-2*t);self.d.ctrl[:]=start+(end-start)*u;mj.mj_step(self.m,self.d)
            if self.frame%40==0:self.sample()
            self.frame+=1
    def apply(self,action):
        typ=action['op'];arm=self.arm();jaw=float(self.d.ctrl[4])
        if typ=='observe':self.move(arm,0,200)
        elif typ=='pick':
            x,y,a=action['x'],action['y'],action['yaw']
            for z,g,t in [(50,0,650),(3,0,500),(3,.0128,330),(49,.0128,650)]:self.move([x,y,z,a],g,t)
        elif typ in ['carry','correct','retry']:
            if typ=='retry':self.move([*arm[:2],48,arm[3]],jaw,500)
            self.move([action['x'],action['y'],action.get('z',35),action['yaw']],jaw,640)
        elif typ=='insert':
            # Keep the grasp through insertion and allow retraction/retry before release.
            if self.r.get('recovery_challenge') and not (self.dir/'perturbed.flag').exists():
                # Single actuator-side XY positioning disturbance; the part remains constrained by finger contact alone.
                self.move([arm[0]+self.r['disturb_mm'],arm[1],arm[2],arm[3]],jaw,300)
                arm=self.arm();(self.dir/'perturbed.flag').touch()
            if self.r.get('recovery_challenge'):
                # Stop descending on contact at the pin tops, while the plate is still in the grasp.
                for level in np.linspace(arm[2],7.3,48)[1:]:
                    self.move([*arm[:2],level,arm[3]],jaw,16)
                    if abs(self.arm()[2]-level)>1.4 and level<18.5:break
                self.move([*arm[:2],self.arm()[2],arm[3]],jaw,120)
            else:
                self.move([*arm[:2],7.3,arm[3]],jaw,650);self.move([*arm[:2],7.3,arm[3]],jaw,220)
        elif typ=='release':
            self.move(arm,0,260);self.move([*arm[:2],59,arm[3]],0,520);self.move([*arm[:2],59,arm[3]],0,200)
        else:raise ValueError(typ)
    def finish(self):
        self.pipe.stdin.close()
        if self.pipe.wait():raise RuntimeError('ffmpeg')
        for c in ['eye','top']:
            self.ren.update_scene(self.d,camera=c);Image.fromarray(self.ren.render()).save(self.dir/f'{self.step:02}-{c}.png')
        self.ren.enable_depth_rendering();self.ren.update_scene(self.d,camera='eye');depth=self.ren.render()*1000;self.ren.disable_depth_rendering()
        np.save(self.dir/f'{self.step:02}-depth.npy',depth.astype('float32'))
        self.ren.close();state=np.empty(mj.mj_stateSize(self.m,mj.mjtState.mjSTATE_INTEGRATION));mj.mj_getState(self.m,self.d,state,mj.mjtState.mjSTATE_INTEGRATION);np.savez(self.dir/'state.npz',state=state)
        R=self.d.xmat[self.body].reshape(3,3);pos=self.d.xpos[self.body]*1000
        t=np.radians(self.r['ta']);u=np.array([np.cos(t),np.sin(t)])*self.r['pitch_mm']/2
        dif=pos[:2]-np.array([self.r['tx'],self.r['ty']]);v=R[:2,0]*self.r['pitch_mm']/2
        errs=[float(np.linalg.norm(dif+sign*(v-u))) for sign in [-1,1]]
        hits=self.contacts();stats=dict(t=float(self.d.time),arm=self.arm().tolist(),part=pos.tolist(),tilt=float(np.degrees(np.arccos(R[2,2].clip(-1,1)))),errors=errs,contacts=sorted(hits),trace=self.samples)
        stats['seat']=bool(max(errs)<=self.r['gap']+.15 and 6.6<pos[2]<7.5 and stats['tilt']<3)
        (self.dir/f'{self.step:02}.json').write_text(json.dumps(stats))
        return stats
def main():
    req=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8-sig'));c=Cell(req['scene'],Path(req['folder']),req['step'])
    c.apply(req['action']);s=c.finish();print(json.dumps({k:v for k,v in s.items() if k!='trace'}))
if __name__=='__main__':main()

