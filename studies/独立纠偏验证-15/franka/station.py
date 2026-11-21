"""Simulated Panda modular fixture and captive-fastener bench. All pickup parts have free joints."""
from pathlib import Path
import xml.etree.ElementTree as E
import json, math
import numpy as np
import mujoco as mj
D=Path(__file__).resolve().parent
def fmt(a):return ' '.join(str(float(x)) for x in a)
def elem(b,tag,**kw):return E.SubElement(b,tag,{k:(fmt(v) if isinstance(v,(tuple,list,np.ndarray)) else str(v)) for k,v in kw.items()})
def box(b,n,p,h,col):return elem(b,'geom',name=n,type='box',pos=p,size=h,rgba=col,friction='1.3 .01 .0003',solref='.004 1',solimp='.97 .995 .0001',density=1300)
steel='.58 .62 .65 1';dark='.32 .37 .41 1'
# Separate physical lower components in each product; first two columns are stage stack locations.
recipes=[
 ('Single-post bearing retainer',[('bearing cartridge',0,0,.014),('end flange',0,0,.010)],[-.025,.025]),
 ('Shimmed valve bonnet',[('valve seat',0,0,.010),('spacer ring',0,0,.008),('bonnet',0,0,.010)],[-.026,.026]),
 ('Twin support bridge',[('rear foot',0,.019,.012),('front foot',0,-.019,.012),('bridge',0,0,.010)],[-.027,.027]),
 ('Stepped bearing housing',[('rear spacer',0,.019,.007),('rear race',0,.019,.007),('front bearing',0,-.019,.014),('retainer',0,0,.011)],[-.028,.028]),
 ('Double-deck guide frame',[('rear guide',0,.019,.010),('front guide',0,-.019,.010),('middle bridge',0,0,.008),('top keeper',0,0,.010)],[-.028,.028])]
def config(k):
    title,bom,bolts=recipes[k];rng=np.random.default_rng(20270341+31*k);target=np.array([.50,.085])+rng.uniform(-.004,.004,2)
    bins=np.array([[.38,-.135],[.49,-.14],[.62,-.13],[.64,.005]])+rng.uniform(-.002,.002,(4,2))
    order=rng.permutation(4)[:len(bom)];single=k<2;heights={0.:.008,.019:.008,-.019:.008};parts=[]
    for j,(name,dx,dy,h) in enumerate(bom):
        wide=(j==len(bom)-1 or k==4 and j==2);z=max(heights.values()) if wide else heights[dy]
        if wide:
            for key in heights:heights[key]=z+h
        else:heights[dy]+=h
        parts.append(dict(name=name,x=dx,y=dy,h=h,z=z,src=bins[order[j]].tolist(),wide=wide,last=j==len(bom)-1,half_y=.018 if single else (.034 if wide else .011)))
    return dict(task=k,title=title,target=target.tolist(),parts=parts,bolts=bolts,pitch=.001,travel=.003,target_torque=.8)
def make(k):
    c=config(k);r=E.parse(D/'template.xml').getroot();r.find('compiler').set('meshdir','assets');r.find('option').set('timestep','.002')
    for bd in r.findall('.//worldbody//body'):bd.set('gravcomp','1')
    finger=r.find(".//general[@name='actuator8']");finger.set('gainprm','.25 0 0');finger.set('biasprm','0 -1593.75 -15')
    w=r.find('worldbody');elem(w,'light',pos='.5 -.4 1.2',dir='0 .3 -1');elem(w,'light',pos='.2 .6 1',dir='0 -.2 -1')
    elem(w,'geom',type='plane',size='1 1 .02',rgba='.25 .29 .32 1',friction='1.3 .01 .0003')
    elem(w,'camera',name='top',pos='.50 0 .85',xyaxes='1 0 0 0 1 0',fovy='34')
    cam=np.array([.95,-.77,.68]);aim=np.array([.43,0,.18]);back=cam-aim;back/=np.linalg.norm(back);right=np.cross([0,0,1],back);right/=np.linalg.norm(right);elem(w,'camera',name='video',pos=cam,xyaxes=[*right,*np.cross(back,right)],fovy='37')
    hand=r.find(".//body[@name='hand']");elem(hand,'site',name='tcp',pos='0 0 .104',size='.001',rgba='0 0 0 0');elem(hand,'site',name='driver',pos='.064 0 .104',size='.001',rgba='0 0 0 0')
    elem(hand,'geom',name='driver_housing',type='cylinder',pos='.064 0 .058',size='.009 .027',contype=0,conaffinity=0,rgba='.18 .23 .25 1',mass='.07');elem(hand,'geom',name='bit',type='cylinder',pos='.064 0 .094',size='.002 .010',mass='.003',contype=0,conaffinity=0,rgba=steel)
    for finger in ['left_finger','right_finger']:
        for j,g in enumerate(r.find(".//body[@name='"+finger+"']").findall('geom')):
            g.set('name',finger+str(j));g.set('friction','2 .02 .001')
    for side in ('left','right'):
        body=r.find(".//body[@name='"+side+"_finger']")
        for g in list(body.findall('geom')):
            if g.get('mesh'):
                g.set('contype','0');g.set('conaffinity','0')
            else:body.remove(g)
        elem(body,'geom',name=side+'_finger_pad',type='box',pos='0 .002 .043',size='.009 .002 .004',mass='.007',rgba='.1 .1 .1 1',friction='2 .02 .001',solref='.004 1',solimp='.97 .995 .0001',priority=1,condim=4)
    tx,ty=c['target'];base=elem(w,'body',name='fixture',pos=[tx,ty,0]);box(base,'base',[0,0,.004],[.046,.046,.004],dark)
    zc=c['parts'][-1]['z']
    for idx,x in enumerate(c['bolts']):
        # Female bosses under the flange. The screw engagement is represented by the pitch constraint.
        elem(base,'geom',name='boss'+str(idx),type='cylinder',pos=[x,0,(zc+.008)/2],size=[.005,max(.0002,(zc-.008)/2)],rgba=dark)
    for j,p in enumerate(c['parts']):
        b=elem(w,'body',name='part'+str(j),pos=[*p['src'],p['h']/2+.0001]);elem(b,'freejoint');hx=.037 if p['last'] else .014 if not p['wide'] else .016;hy=p['half_y'];h=p['h']/2
        # Machined central pass-through window on each module, split rails on the final flange for bolt clearance.
        cut=.005
        for s in [-1,1]:
            box(b,f'piece{j}-end{s}',[0,s*(hy+cut)/2,0],[hx,(hy-cut)/2,h],steel)
        intervals=[(-hx,-cut),(cut,hx)]
        if p['last']:
            intervals=[]
            for lo,hi,x in [(-hx,-cut,c['bolts'][0]),(cut,hx,c['bolts'][1])]:intervals.extend([(lo,x-.003),(x+.003,hi)])
        for n,(lo,hi) in enumerate(intervals):box(b,f'piece{j}-web{n}',[(lo+hi)/2,0,0],[(hi-lo)/2,cut,h],steel)
        if p['last']:
            for n,x in enumerate(c['bolts']):
                tag=str(n);shaft=elem(b,'body',name='screw'+tag,gravcomp=1,pos=[x,0,h+.004])
                elem(shaft,'joint',name='turn'+tag,type='hinge',axis='0 0 -1',damping='.0001',armature='.00008')
                elem(shaft,'joint',name='advance'+tag,type='slide',axis='0 0 -1',limited='true',range='-.0001 .004',armature='.002',damping='1')
                elem(shaft,'geom',name='head'+tag,type='cylinder',size='.004 .002',mass='.004',rgba='.41 .43 .46 1',contype=0,conaffinity=0)
                elem(shaft,'geom',name='thread'+tag,type='cylinder',pos='0 0 -.006',size='.0023 .005',mass='.003',rgba=dark,contype=0,conaffinity=0)
                elem(shaft,'site',name='socket'+tag,pos='0 0 .002',size='.001',rgba='0 0 0 0')
                elem(r.find('equality'),'joint',joint1='advance'+tag,joint2='turn'+tag,polycoef=[0,c['pitch']/(2*math.pi),0,0,0],solref='.002 1',solimp='.999 .9999 .00001')
    m=mj.MjModel.from_xml_string(E.tostring(r,encoding='unicode'),assets={p.name:p.read_bytes() for p in (D/'assets').iterdir()});d=mj.MjData(m)
    d.qpos[:9]=[0,-.35,0,-2.15,0,1.82,.78,.04,.04];d.ctrl[:]=[*d.qpos[:7],255];mj.mj_forward(m,d)
    return m,d,c


