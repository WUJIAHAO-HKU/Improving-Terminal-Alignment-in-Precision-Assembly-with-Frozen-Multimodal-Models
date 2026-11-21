import math
import numpy as np
from scipy.spatial.transform import Rotation
def outline(r,clearance):
    k,L,rad=r['task'],r['size'],r['radius']
    if k=='blade':
        x=L/2+clearance;y=rad+clearance;return np.array([[-x,-y],[x,-y],[x,y],[-x,y]])
    n=48 if k=='dshaft' else 32
    a=np.arange(n)*2*np.pi/n;u=np.stack((np.cos(a),np.sin(a)),axis=1)
    if k=='dshaft':
        length=np.minimum(L/2+clearance,(.22*L+clearance)/np.maximum(u[:,0],1e-9))
        return u*length[:,None]
    return u*(rad+clearance)
def margin(r,end):
    theta=math.radians(r['ta']);co,si=math.cos(theta),math.sin(theta)
    target=np.array([[co,si],[-si,co]])
    quat=end['part_quat'];rot=Rotation.from_quat(quat[1:]+quat[:1]).as_matrix()[:2,:2]
    cs=([-r['size']/2,r['size']/2] if r['task'] in ('twin','connector') else [0.])
    hole=outline(r,r['gap']);edges=np.roll(hole,-1,axis=0)-hole
    margins=[]
    for c in cs:
        pins=(outline(r,0)+[c,0])@target+[r['tx'],r['ty']]
        rel=(pins-np.array(end['part_mm'][:2]))@rot-[c,0]
        dist=rel[None,:,:]-hole[:,None,:]
        det=edges[:,0,None]*dist[:,:,1]-edges[:,1,None]*dist[:,:,0]
        margins.append(np.min(det/np.hypot(edges[:,0],edges[:,1])[:,None]))
    return min(margins)
def dist(a,b,L,wrap):
    dyaw=a['yaw']-b['yaw']
    if wrap:dyaw=(dyaw+90)%180-90
    return math.dist([a['x'],a['y']],[b['x'],b['y']])+L/2*math.radians(abs(dyaw))
