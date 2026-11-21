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
def skeleton(scene):

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
    for name,cam,aim,fov in [('eye',(6,-205,239),(0,0,5),38),('top',(0,0,294),(0,0,0),37),('video',(168,-300,195),(0,0,55),38)]:
        back=np.array(cam,dtype=float)-aim;back/=np.linalg.norm(back)
        right=np.cross([0,0,1],back);right=right/np.linalg.norm(right) if np.linalg.norm(right)>1e-8 else np.array([1.,0,0])
        up=np.cross(back,right);add(world,'camera',name=name,pos=pt(cam),xyaxes=val([*right,*up]),fovy=fov)
    return root
