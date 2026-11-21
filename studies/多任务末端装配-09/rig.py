"""Free-release insertion fixtures, lengths in mm outside the MuJoCo XML."""
import json, math, sys, hashlib, platform
from pathlib import Path
import xml.etree.ElementTree as X
import numpy as np
import mujoco as mj
D=Path(__file__).resolve().parent
TASKS=('twin','blade','dshaft')
def save(name,obj):
    (D/name).write_text(json.dumps(obj,indent=2,allow_nan=False),encoding='utf8')
def rot(a):
    t=np.radians(a);return np.array([[np.cos(t),-np.sin(t)],[np.sin(t),np.cos(t)]])
def attr(vals):return ' '.join(f'{v:.10g}' for v in vals)
def spec(task):
    if task=='twin':return [(-16,0),(16,0)],(32,12)
    return [(0,0)],(26,13)
def contour(task,c):
    a=np.arange(32)*2*np.pi/32
    if task=='blade':return np.array([[-18-c,-3-c],[18+c,-3-c],[18+c,3+c],[-18-c,3+c]])
    u=np.stack((np.cos(a),np.sin(a)),axis=1)
    if task=='twin':return u*(5+c)
    # Flat is located on the positive local x side of the D-shaped shaft.
    return u*np.minimum(11+c,(5.5+c)/np.maximum(u[:,0],1.e-9))[:,None]
def rig(r):
    task=r['task']; centers,extent=spec(task)
    xml=X.Element('mujoco');X.SubElement(xml,'compiler',angle='degree')
    X.SubElement(xml,'option',timestep='.001',integrator='implicitfast',iterations='80')
    vis=X.SubElement(xml,'visual');X.SubElement(vis,'map',znear='.005');X.SubElement(vis,'global',offwidth='360',offheight='360')
    defs=X.SubElement(xml,'default');X.SubElement(defs,'geom',friction='.6 .01 .001',solref='.004 1',margin='0')
    asset=X.SubElement(xml,'asset');world=X.SubElement(xml,'worldbody')
    X.SubElement(world,'light',pos='.05 -.08 .18',dir='0 0 -1',diffuse='.85 .85 .85')
    X.SubElement(world,'geom',type='plane',size='.14 .14 .005',rgba='.28 .32 .34 1')
    moving=X.SubElement(world,'body',name='part');X.SubElement(moving,'freejoint')
    X.SubElement(moving,'inertial',pos='0 0 0',mass='.06',diaginertia='.000009 .000025 .00003')
    def mesh(body,poly,z0,z1,col):
        name='v'+str(len(asset));vv=[[x/1000,y/1000,z/1000] for z in (z0,z1) for x,y in poly]
        X.SubElement(asset,'mesh',name=name,vertex=attr(np.ravel(vv)));X.SubElement(body,'geom',type='mesh',mesh=name,rgba=col)
    for idx,(cx,cy) in enumerate(centers):
        center=np.array([cx,cy]); half=np.array([16,12]) if task=='twin' else np.array(extent)
        inner=contour(task,r['gap'])
        # Add corner rays to tile the rectangular envelope without clipping its corners.
        corner=np.array([[-1,-1],[1,-1],[1,1],[-1,1]])*half
        angles=np.unique(np.round(np.mod(np.arctan2(np.r_[inner[:,1],corner[:,1]],np.r_[inner[:,0],corner[:,0]]),2*np.pi),10))
        inner2=[];outer=[]
        for a in angles:
            u=np.array([np.cos(a),np.sin(a)]);cross=lambda p,q:p[0]*q[1]-p[1]*q[0]
            hits=[]
            for v,w in zip(inner,np.roll(inner,-1,axis=0)):
                edge=w-v;den=cross(u,edge)
                if abs(den)>1e-10:
                    t=cross(v,edge)/den; h=cross(v,u)/den
                    if t>0 and -1e-7<=h<=1+1e-7:hits.append(t)
            inner2.append(center+u*min(hits));outer.append(center+u*min(half/np.maximum(np.abs(u),1e-12)))
        for j in range(len(outer)):
            k=(j+1)%len(outer)
            mesh(moving,[inner2[j],outer[j],outer[k],inner2[k]],-2,2,'.43 .57 .65 1')
        mesh(world,contour(task,0)+center,0,14,'.85 .57 .22 1')
    # Two visible fiducials per body, on known axes, symmetrically placed about its origin.
    for body,dist,z,col in [(world,44,.24,'1 .08 .03 1'),(moving,extent[0]-2,2.15,'.06 1 .18 1')]:
        for sign in (-1,1):
            X.SubElement(body,'geom',type='cylinder',pos=attr((sign*dist/1000,0,z/1000)),size='.00135 .00015',rgba=col,contype='0',conaffinity='0',mass='0')
    for name,p in [('rgb',r['pitch']),('top',0)]:
        a=np.radians(p);X.SubElement(world,'camera',name=name,pos=attr([0,-.170*np.sin(a),.009+.170*np.cos(a)]),xyaxes=attr([1,0,0,0,np.cos(a),np.sin(a)]),fovy='40')
    model=mj.MjModel.from_xml_string(X.tostring(xml,encoding='unicode'));return model,mj.MjData(model)
def pose(model,data,r,action):
    mj.mj_resetData(model,data);x,y,a=action;theta=np.radians(r['yaw']+a)/2
    data.qpos[:]=[(r['x']+x)/1000,(r['y']+y)/1000,r['z']/1000,np.cos(theta),0,0,np.sin(theta)];mj.mj_forward(model,data)
def run(model,data,r,action):
    pose(model,data,r,action);mj.mj_step(model,data,nstep=550);prev=data.qpos[:3].copy();mj.mj_step(model,data,nstep=50)
    pos=data.qpos[:3]*1000;R=data.xmat[1].reshape(3,3);tilt=np.degrees(np.arccos(R[2,2].clip(-1,1)))
    drift=1000*np.linalg.norm(prev-data.qpos[:3]);yaw=np.degrees(np.arctan2(R[1,0],R[0,0]))
    # Strict final seating includes pose and clearance; evaluate both ends/features in the part frame.
    centers,_=spec(r['task']);hole=contour(r['task'],r['gap']);b=contour(r['task'],0);edges=np.roll(hole,-1,axis=0)-hole
    margins=[]
    for c in centers:
        vertices=(b+np.array(c)-pos[:2])@rot(yaw)-np.array(c);dif=vertices[None,:,:]-hole[:,None,:]
        margins.append(float(np.min((edges[:,None,0]*dif[:,:,1]-edges[:,None,1]*dif[:,:,0])/np.linalg.norm(edges,axis=1)[:,None])))
    ok=bool(1.5<=pos[2]<=2.6 and tilt<3 and drift<.3 and min(margins)>=-.15)
    return dict(ok=ok,height_mm=float(pos[2]),tilt_deg=float(tilt),drift_mm=float(drift),feature_margin_mm=margins)
def main():
    if sys.argv[1]=='prepare':
        from PIL import Image
        (D/'frames').mkdir(exist_ok=True); rows=[]
        rng=np.random.default_rng(2026112109)
        for batch in range(6):
            for j in range(5):
                i=5*batch+j;task=TASKS[i%3]
                rows.append(dict(id=f'P{i:03d}',task=task,batch=batch,gap=[.5,1.,2.][(i//3+i%3)%3],pitch=int(rng.choice([15,25,35])),x=float(rng.uniform(-8,8)),y=float(rng.uniform(-8,8)),yaw=float(rng.choice([-1,1])*rng.uniform(4,23)),z=float(rng.uniform(21,32))))
        for r in rows:
            m,d=rig(r);pose(m,d,r,[0]*3)
            with mj.Renderer(m,360,360) as ren:
                for cam in ['rgb','top']:
                    ren.update_scene(d,camera=cam);Image.fromarray(ren.render()).save(D/'frames'/f"{r['id']}-{cam}.png")
            r['oracle']=run(m,d,r,[-r['x'],-r['y'],-r['yaw']]);r['zero']=run(m,d,r,[0,0,0])
        save('scenes.json',rows);save('runtime.json',dict(mujoco=mj.__version__,platform=platform.platform()))
    else:
        acts=json.loads((D/'actions.json').read_text(encoding='utf-8-sig'));rows=json.loads((D/'scenes.json').read_text());out=[]
        for r in rows:
            m,d=rig(r);out.append(dict(id=r['id'],**{k:run(m,d,r,v) for k,v in acts[r['id']].items()}))
        save('scores.json',out)
if __name__=='__main__':main()

