"""CAD edge registration and occlusion-aware peg fitting. All distances are millimetres."""
import math
import cv2
import numpy as np
from scipy.optimize import least_squares, minimize
cv2.setNumThreads(1)
FOCAL=160/math.tan(math.radians(15))
C=159.5
def project(xy,h,cs,sn):
    x,y=np.asarray(xy).T
    optical=y*sn+h*cs
    return np.column_stack([C+FOCAL*x/optical,C+FOCAL*(h*sn-y*cs)/optical])
def ray(uv,cs,sn):
    u,v=(np.asarray(uv)-C)/FOCAL
    return np.array([u, sn-v*cs])/(cs+v*sn)
def polygon(x,y,hx,hy,rotation=0):
    corners=np.array([[-hx,-hy],[hx,-hy],[hx,hy],[-hx,hy]])
    a=math.radians(rotation); mat=np.array([[math.cos(a),-math.sin(a)],[math.sin(a),math.cos(a)]])
    return corners@mat.T+[x,y]
def parts(task):
    if task=='square':
        return [polygon(i*33.25,0,10.5,43.75) for i in [-1,1]]+[polygon(0,i*33.25,31.25,10.5) for i in [-1,1]]+[polygon(54,0,25.25,15.875)]
    return ([polygon(i*42.45,0,11.25,22.5) for i in [-1,1]]+
            [polygon(0,i*42.45,22.5,11.25) for i in [-1,1]]+
            [polygon(30*i,30*j,11.25,22.5,-45*i*j) for i in [-1,1] for j in [-1,1]]+
            [polygon(60,0,25.25,15.875)])
def aperture(task,radius=None):
    rad=(22.75 if task=='square' else 31.1764) if radius is None else radius
    if task=='square': return polygon(0,0,rad,rad)
    n=8 if radius is None else 64
    a=np.arange(n)*2*np.pi/n+(np.pi/8 if n==8 else 0)
    return rad*np.column_stack([np.cos(a),np.sin(a)])/(np.cos(np.pi/8) if n==8 else 1)
def color_classes(bgr,task):
    b,g,r=cv2.split(cv2.GaussianBlur(bgr,(3,3),.75).astype(np.float32))
    if task=='square':
        colored=(r-b>21)&(r-g>6)
        upper=colored&(r>100)&(r-b>54)
        side=colored&(r<=104)
    else:
        steel=(b-r>-4)&(abs(g-b)<17)&(abs(r-g)<19)
        upper=steel&(g>105)&(g<223)
        side=steel&(g<=108)
    return upper.astype('uint8'),side.astype('uint8')
def points_on(poly,spacing=2.5):
    return np.concatenate([np.linspace(a,b,max(3,round(np.linalg.norm(a-b)/spacing)),endpoint=False) for a,b in zip(poly,np.roll(poly,-1,axis=0))])
def fit_hole(top,task,angle):
    cs,sn=np.cos(angle),np.sin(angle); nominal=360*cs-80
    # Rectify onto one horizontal reference plane; true plane height becomes an unknown uniform scale.
    grid=np.arange(-155,156,dtype=np.float32)
    xx,yy=np.meshgrid(grid,grid[::-1]);uv=project(np.c_[xx.ravel(),yy.ravel()+nominal*sn/cs],nominal,cs,sn).reshape(311,311,2).astype('float32')
    rect=cv2.remap(top.astype('float32'),uv[:,:,0],uv[:,:,1],cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT,borderValue=.5)
    shape=parts(task)
    best=None
    for scale in np.linspace(.72,1.48,33):
        ras=np.zeros((181,221),np.uint8)
        center=np.array([88,90])
        for poly in shape:
            cv2.fillConvexPoly(ras,np.rint(center+scale*poly*[1,-1]).astype('int32'),1)
        # Weight narrow strips on either side of visible CAD top edges.
        kernel=np.ones((7,7),np.uint8);inner=ras-cv2.erode(ras,kernel);outer=cv2.dilate(ras,kernel)-ras
        template=(inner/inner.sum()-outer/outer.sum()).astype('float32')
        # padding allows object to be clipped at image borders
        corr=cv2.matchTemplate(cv2.copyMakeBorder(rect,90,90,88,132,cv2.BORDER_CONSTANT,value=.5),template,cv2.TM_CCORR)
        _,score,_,(x,y)=cv2.minMaxLoc(corr)
        if best is None or score>best[0]:best=(score,x-155,155-y,scale)
    score,x,y,scale=best
    h=nominal/scale
    pos=np.array([x/scale,(y+nominal*sn/cs)/scale])
    # Subpixel refinement on the inner and outer top contour in original RGB.
    outline=np.zeros((285,320),np.uint8);origin=np.array([122,142])
    for poly in shape:cv2.fillConvexPoly(outline,np.rint(origin+2*poly).astype('int32'),1)
    cs0,_=cv2.findContours(outline,cv2.RETR_LIST,cv2.CHAIN_APPROX_NONE)
    points=np.concatenate([(c.reshape(-1,2)[::5]-origin)/2 for c in cs0 if len(c)>35])
    edge=cv2.morphologyEx(top,cv2.MORPH_GRADIENT,np.ones((3,3),np.uint8));dist=cv2.distanceTransform(1-edge,cv2.DIST_L2,5)
    def residual(p):
        uv=project(points+p[:2],p[2],cs,sn)
        return cv2.remap(dist,uv[:,0].astype('float32')[:,None],uv[:,1].astype('float32')[:,None],cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT,borderValue=0).ravel().astype(float)
    start=np.r_[pos,h]
    # Use finite differences larger than the OpenCV interpolation step.
    def jac(p):
        return np.stack([(residual(p+e)-residual(p-e))/(2*np.linalg.norm(e)) for e in np.diag([.13,.13,.26])],axis=1)
    opt=least_squares(residual,start,jac=jac,bounds=(start-[12,15,15],start+[12,15,15]),loss='soft_l1',f_scale=1.2,max_nfev=45)
    return opt.x,float(score)
def occluder(task,hole,cs,sn):
    mask=np.zeros((320,320),np.uint8)
    for poly in parts(task):
        v=np.concatenate([project(poly+hole[:2],hole[2]+dz,cs,sn) for dz in [0,20]])
        cv2.fillConvexPoly(mask,cv2.convexHull(np.rint(v).astype('int32')),1)
    return cv2.dilate(mask,np.ones((3,3),np.uint8))
def fit_peg(top,side,task,gap,angle,hole,prior_dz,depth):
    cs,sn=np.cos(angle),np.sin(angle);rad=(22.75 if task=='square' else 31.1764)-gap
    rim=aperture(task,rad)
    occ=occluder(task,hole,cs,sn)
    # Only score an image region around the physically admissible peg position.
    h0=hole[2]+prior_dz
    if depth is not None:
        # Estimate surface-to-surface separation; discard implausible two-peak splits.
        sep=depth['far']-depth['near']
        if 33<=sep<=79 and abs(depth['near']-hole[2])<18:h0=hole[2]+sep
    pc=project(hole[None,:2],h0,cs,sn)[0]
    yy,xx=np.indices(top.shape)
    roi=(abs(xx-pc[0])<FOCAL*(rad+28)/max(h0,120))&(yy>pc[1]-FOCAL*(rad+26)/max(h0,120))&(yy<pc[1]+120)
    obs=np.zeros_like(top);obs[side>0]=1;obs[top>0]=2
    def engine(factor):
        size=320//factor
        visible=cv2.resize((roi&(occ==0)).astype('uint8'),(size,size),interpolation=cv2.INTER_NEAREST_EXACT).astype(bool)
        target=cv2.resize(obs,(size,size),interpolation=cv2.INTER_NEAREST_EXACT)
        # Crop only the search window and cap penalties of matching the remote backdrop.
        ys,xs=np.where(visible); x0,x1=int(xs.min()),int(xs.max()+1);y0,y1=int(ys.min()),int(ys.max()+1)
        visible=visible[y0:y1,x0:x1];target=target[y0:y1,x0:x1]
        def objective(p):
            dx,dy,dh=p;h=h0+dh;pos=hole[:2]+[dx,dy]
            verts=[(project(rim+pos,h+off,cs,sn)+.5)/factor-.5-[x0,y0] for off in (0,220)]
            vs=[np.rint(z*16).astype('int32') for z in verts]
            pred=np.zeros_like(target);cv2.fillConvexPoly(pred,cv2.convexHull(np.concatenate(vs)),1,shift=4);cv2.fillConvexPoly(pred,vs[0],2,shift=4)
            # Match the exposed top face and side silhouette. Prior stabilizes a fully hidden cap.
            mismatch=np.count_nonzero((pred!=target)&visible)
            return float(mismatch*factor**2 + (dh/5)**2*3 + .005*(dx*dx+dy*dy))
        return objective
    if not np.any(roi&(occ==0)):raise ValueError('peg ROI fully occluded')
    loss=engine(3)
    seed=min(([x,y,0.] for x in range(-18,19,6) for y in range(-18,19,6)),key=loss)
    p=np.asarray(seed,float)
    for factor,steps in [(3,[3,1.5]),(1,[2,1,.5,.25])]:
        loss=engine(factor)
        for step in steps:
            for _ in range(12):
                cand=[p]+[p+step*np.array(z) for z in [(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1),(0,sn,cs),(0,-sn,-cs)]]
                possible=[z for z in cand if abs(z[2])<=18 and max(abs(z[:2]))<40]
                other=min(possible,key=loss)
                if np.array_equal(p,other):break
                p=other
    peg=np.r_[hole[:2]+p[:2],h0+p[2]]
    return peg,float(loss(p)),float(np.count_nonzero((obs==2)&(occ==0)&roi))
def estimate(bgr,task,gap,pitch,depth,prior_dz):
    angle=math.radians(pitch);cs,sn=np.cos(angle),np.sin(angle)
    top,side=color_classes(bgr,task)
    hole,match=fit_hole(top,task,angle)
    uv_h=project(hole[None,:2],hole[2],cs,sn)[0]
    out={}
    for mode,extra in [('rgb',None),('rgbd',depth)]:
        try:
            peg,loss,toparea=fit_peg(top,side,task,gap,angle,hole,prior_dz,extra)
            uv_p=project(peg[None,:2],peg[2],cs,sn)[0]
            action=ray(uv_p,cs,sn)*peg[2]-ray(uv_h,cs,sn)*hole[2]
            out[mode]=dict(action=action.tolist(),hole_uv=uv_h.tolist(),peg_uv=uv_p.tolist(),hole_h=float(hole[2]),peg_h=float(peg[2]),match=match,loss=loss,top_evidence=toparea,localized=bool(match>.14))
            if not out[mode]['localized']:out[mode]['action']=[0.,0.]
        except ValueError:
            out[mode]=dict(action=[0.,0.],localized=False,match=match,hole_uv=uv_h.tolist(),peg_uv=None)
    return out
