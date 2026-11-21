import numpy as np
from gantry import *
def profile(r,gap):
    k=r['task'];L=r['size']; c=gap
    if k in ('twin','connector'):
        a=np.linspace(0,2*np.pi,32,endpoint=False)
        return np.c_[np.cos(a),np.sin(a)]*(r['radius']+c)
    if k=='blade':
        lx=L/2+c;ly=r['radius']+c
        return np.array([[-lx,-ly],[lx,-ly],[lx,ly],[-lx,ly]])
    a=np.linspace(0,2*np.pi,48,endpoint=False);u=np.c_[np.cos(a),np.sin(a)]
    return u*np.minimum(L/2+c,(L*.22+c)/np.maximum(u[:,0],1e-9))[:,None]
def centers(r):
    return [-r['size']/2,r['size']/2] if r['task'] in ('twin','connector') else [0.]
def shapegeom(asset,body,name,poly,z0,z1,color):
    pts=[[x,y,z] for z in (z0,z1) for x,y in poly];add(asset,'mesh',name=name,vertex=pt(np.ravel(pts)))
    add(body,'geom',name=name,type='mesh',mesh=name,rgba=color)
def attach(root,r):
    asset=root.find('asset');world=root.find('worldbody');fixed=world.find("body[@name='fixture']");part=world.find("body[@name='cover']")
    for g in list(asset):asset.remove(g)
    for g in list(part.findall('geom')):part.remove(g)
    for g in list(fixed.findall('geom')):fixed.remove(g)
    L=r['size'];cs=centers(r);hx=L/2 if len(cs)>1 else L/2+6;hy=r['width']/2
    sockets=[(0.,'primary')] if r['task']!='connector' else [(0.,'primary'),(r['other_y'],'other')]
    for dy,label in sockets:
        box(fixed,'base_'+label,(0,dy,2),(hx*len(cs)+2,hy+2,2),MET)
        for j,c in enumerate(cs):shapegeom(asset,fixed,f'pin_{label}_{j}',profile(r,0)*(2.15 if label=='other' and j==1 else 1.0)+[c,dy],4,14,GOLD)
    hole=profile(r,r['gap'])
    for idx,c in enumerate(cs):
        corner=np.array([[-hx,-hy],[hx,-hy],[hx,hy],[-hx,hy]])
        allv=np.vstack([corner,hole]);ang=np.unique(np.round(np.mod(np.arctan2(allv[:,1],allv[:,0]),2*np.pi),8))
        inner=[];outer=[]
        for a in ang:
            u=np.array([np.cos(a),np.sin(a)]);hits=[]
            for x,y in zip(hole,np.roll(hole,-1,axis=0)):
                e=y-x;den=u[0]*e[1]-u[1]*e[0]
                if abs(den)<1e-9:continue
                t=(x[0]*e[1]-x[1]*e[0])/den;b=(x[0]*u[1]-x[1]*u[0])/den
                if t>0 and -1e-6<=b<=1+1e-6:hits.append(t)
            inner.append(u*min(hits)+[c,0]);outer.append(u*min(np.array([hx,hy])/np.maximum(abs(u),1e-10))+[c,0])
        for j in range(len(ang)):
            k=(j+1)%len(ang);shapegeom(asset,part,f'cover_{idx}_{j}',[inner[j],outer[j],outer[k],inner[k]],-3,3,AL)
    # Fixed foreground strut: visible to both calibrated cameras according to projection, outside the working volume.
    box(world,'guard',(r['occ_x'],-60,69),(r['occ_w']/2,1.5,14),'.25 .27 .29 1',contype='0',conaffinity='0')
def score(r,pos,R):
    th=np.radians(r['ta']);T=np.array([[np.cos(th),-np.sin(th)],[np.sin(th),np.cos(th)]])
    hole=profile(r,r['gap']);pins=profile(r,0);e=np.roll(hole,-1,axis=0)-hole;values=[]
    for c in centers(r):
        fixed=(pins+[c,0])@T.T+[r['tx'],r['ty']]
        q=(fixed-pos[:2])@R[:2,:2]-[c,0];u=q[None,:,:]-hole[:,None,:]
        values.append(float(((e[:,None,0]*u[:,:,1]-e[:,None,1]*u[:,:,0])/np.linalg.norm(e,axis=1)[:,None]).min()))
    return values

