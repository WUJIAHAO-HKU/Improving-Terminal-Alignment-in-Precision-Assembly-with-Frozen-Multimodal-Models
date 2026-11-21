"""Locked pose estimates from deployable color markers and camera calibration."""
import numpy as np
import cv2
def estimate(rgb,pitch,task,red=False):
    R,G,B=rgb.astype(float).transpose(2,0,1)
    mask=((R>1.6*G)&(R>1.6*B)&(R>25)) if red else ((G>1.6*R)&(G>1.6*B)&(G>25))
    _,labels,stats,xy=cv2.connectedComponentsWithStats(mask.astype('uint8'))
    pts=sorted((pt for pt,st in zip(xy[1:],stats[1:]) if st[4]>=4),key=lambda p:p[0])
    if len(pts)!=2:return None
    a=np.radians(pitch);f=180/np.tan(np.radians(20));cam=np.array([0,-170*np.sin(a),9+170*np.cos(a)])
    rays=[]
    for x,y in pts:
        v=(179.5-y)/f;rays.append([(x-179.5)/f,np.sin(a)+v*np.cos(a),-np.cos(a)+v*np.sin(a)])
    rays=np.asarray(rays);xy_per_height=rays[:,:2]/(-rays[:,2,None])
    sep=88 if red else (60 if task=='twin' else 48)
    coords=cam[:2]+xy_per_height*(sep/np.linalg.norm(xy_per_height[1]-xy_per_height[0]))
    v=coords[1]-coords[0];return [*coords.mean(axis=0),np.degrees(np.arctan2(v[1],v[0]))]
def target(rgb,pitch,task):
    fixed=estimate(rgb,pitch,task,True);plate=estimate(rgb,pitch,task)
    if fixed is None or plate is None:return None
    return (np.array(fixed)-plate).tolist()
def err(a,g,task):
    if g is None:return float('inf')
    radius={'twin':16,'blade':18,'dshaft':11}[task]
    return float(np.linalg.norm(np.array(a[:2])-g[:2])+radius*np.radians(abs(a[2]-g[2])))

