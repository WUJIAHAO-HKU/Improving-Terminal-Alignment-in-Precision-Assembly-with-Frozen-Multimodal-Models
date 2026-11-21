"""Secondary paired diagnostic at 1 mm: initial part angle, external occlusion and orientation correction."""
import json,sys,math
import numpy as np
from PIL import Image,ImageDraw
from server import Rig,TASKS,dump,read,D
from robosuite.utils.transform_utils import quat_multiply
def rows():
    out=[]
    for task in TASKS:
        for k in range(4):
            seed=523987+149*TASKS.index(task)+k+(87011 if task=='round' else 0);rng=np.random.default_rng(seed)
            x,y=rng.uniform(-14,14,2);pitch=float(rng.choice([0,20,32]));cx,cy=rng.uniform(-15,15,2);h=float(rng.uniform(16,32))
            angle=float(rng.choice([-1,1])*rng.uniform(8,14));yaw=float(rng.choice([-1,1])*rng.uniform(8,16)) if task=='square' else 0.
            for cond in ['aligned','tilted','occluded','tilted_occluded']:
                out.append(dict(id=f'stress-{task}-{k}-{cond}',split='stress',task=task,k=k,gap=1,seed=seed,angle=pitch,camx=cx,camy=cy,height=h,x=x,y=y,
                                tilt=angle if 'tilted' in cond else 0,yaw=yaw if 'tilted' in cond else 0,occ='occluded' in cond,condition=cond))
    return out
def orient(rig,r,roll,yaw):
    cr,sr=math.cos(math.radians(roll)/2),math.sin(math.radians(roll)/2)
    cz,sz=math.cos(math.radians(yaw)/2),math.sin(math.radians(yaw)/2)
    q=[cz*cr,cz*sr,sz*sr,sz*cr]
    if rig.dual:
        rig.s.data.mocap_quat[rig.hm]=q;rig.s.forward()
        rot=rig.s.data.body_xmat[rig.hid].reshape(3,3)
        rig.s.data.mocap_pos[rig.hm]+=[.11,0,0]-rot@np.array([.11,0,0])
    else:
        j=rig.nut.joints[0];pose=rig.s.data.get_joint_qpos(j).copy();pose[3:]=q;rig.s.data.set_joint_qpos(j,pose)
    rig.s.forward()
def main():
    mode=sys.argv[1];rr=rows();output=[]
    if mode=='score':acts=read('stress-actions.json')
    for task in TASKS:
        rig=Rig(task,1)
        for r in rr:
            if r['task']!=task:continue
            if mode=='render':
                rig.pose(r);orient(rig,r,r['tilt'],r['yaw'])
                img=Image.fromarray(rig.s.render(width=320,height=320,camera_name=rig.cam_name)[::-1].copy())
                if r['occ']:
                    draw=ImageDraw.Draw(img);draw.rectangle((140,34,175,285),fill=(57,60,64))
                img.save(D/'frames'/(r['id']+'.jpg'),quality=93)
            else:
                for model,a in acts[r['id']].items():
                    dx,dy,roll,yaw=a;rig.pose(r,dx,dy);orient(rig,r,r['tilt']+roll,r['yaw']+yaw)
                    if rig.dual:
                        # Use a plate-frame cross-section bound plus a finite plate thickness term.
                        res=np.array([r['x']+dx,r['y']+dy]);err=math.radians(r['tilt']+roll)
                        passable=max(abs(res[0]),abs(res[1])+10*abs(math.tan(err))+49*(1/max(.01,math.cos(err))-1))<=1.
                        rig.s.data.mocap_pos[rig.hm,2]-=(r['height']+(32 if passable else -10))/1000;rig.s.forward();stable=True
                    else:
                        for _ in range(400):rig.s.step()
                        prev=rig.s.data.body_xpos[rig.hid].copy()
                        for _ in range(50):rig.s.step()
                        stable=float(np.linalg.norm(prev-rig.s.data.body_xpos[rig.hid]))<.001
                    ok,z,lat,tilt=rig.geometry()
                    output.append(dict(id=r['id'],model=model,action=a,strict=bool(ok and stable),final_height=z,final_lateral=lat,final_tilt=tilt))
        rig.e.close()
    dump('stress-manifest.json' if mode=='render' else 'stress-scores.json',rr if mode=='render' else output)
if __name__=='__main__':main()

