"""Build independent free bodies from each assembly BOM and audit them on the common base."""
from frame import *
from catalog import RECIPES
def R(a):
    t=np.radians(a);return np.array([[np.cos(t),-np.sin(t)],[np.sin(t),np.cos(t)]])
def poly(kind,c,scale):
    a=np.arange(20)*2*np.pi/20;u=np.stack((np.cos(a),np.sin(a)),axis=1)
    radius=3.9*scale
    if kind=='slot':
        hx,hy=5.25*scale+c,2.45*scale+c;return np.array([[-hx,-hy],[hx,-hy],[hx,hy],[-hx,hy]])
    if kind=='dflat':return u*np.minimum(radius+c,(.48*radius+c)/np.maximum(u[:,0],1e-9))[:,None]
    return u*(radius+c)
def mesh(asset,body,n,vertices,h0,h1,col):
    add(asset,'mesh',name=n,vertex=pt(np.ravel([[x,y,z] for z in (h0,h1) for x,y in vertices])))
    add(body,'geom',type='mesh',mesh=n,name=n,rgba=col)
def surround(asset,body,n,shape,center,limits,thick):
    xmin,xmax,ymin,ymax=limits
    corner=np.array([[xmin,ymin],[xmax,ymin],[xmax,ymax],[xmin,ymax]])
    pts=np.vstack((shape,corner));angles=np.unique(np.round(np.mod(np.arctan2(pts[:,1],pts[:,0]),2*np.pi),8))
    inside=[];outside=[]
    for a in angles:
        u=np.array([np.cos(a),np.sin(a)]);dist=[]
        for p,q in zip(shape,np.roll(shape,-1,axis=0)):
            e=q-p;den=u[0]*e[1]-u[1]*e[0]
            if abs(den)>1e-8:
                t=(p[0]*e[1]-p[1]*e[0])/den;f=(p[0]*u[1]-p[1]*u[0])/den
                if t>0 and -1e-6<=f<=1+1e-6:dist.append(t)
        inside.append(u*min(dist)+center)
        tx=(xmax if u[0]>=0 else xmin)/(u[0] if abs(u[0])>1e-10 else 1e-10)
        ty=(ymax if u[1]>=0 else ymin)/(u[1] if abs(u[1])>1e-10 else 1e-10)
        outside.append(u*min(abs(tx),abs(ty))+center)
    for j in range(len(angles)):
        k=(j+1)%len(angles);mesh(asset,body,n+'_'+str(j),[inside[j],outside[j],outside[k],inside[k]],-thick/2,thick/2,AL)
def design(r):
    parts=RECIPES[r['recipe']];span=r['span'];stacks={'M':4,'L':4,'R':4};kinds={}
    for p in parts:
        if p.profile=='bridge':continue
        if p.column not in kinds or p.profile in ('dflat','slot','double'):kinds[p.column]=p.profile
    def pc(col):return {'M':0,'L':-span/2,'R':span/2}[col]
    steps=[]
    for j,p in enumerate(parts):
        cols=['L','R'] if p.profile=='bridge' else [p.column];bottom=stacks[cols[0]]
        assert all(stacks[col]==bottom for col in cols)
        for col in cols:stacks[col]+=p.thickness
        mid=np.mean([pc(col) for col in cols]);interfaces=[]
        for col in cols:
            kind=kinds.get(col,'round');pt=pc(col)
            if kind=='double':
                for sign in (-1,1):interfaces.append((pt+sign*span/2,'round','round'))
            else:
                bore=kind if p.profile=='bridge' else p.profile
                # A circular keeper on a D pin clears the full circular envelope.
                interfaces.append((pt,kind,bore))
        steps.append(dict(label=p.label,profile=p.profile,column=p.column,thickness=p.thickness,bottom=bottom,mid=mid,interfaces=interfaces))
    return steps,stacks
def make(r):
    steps,stacks=design(r);root=skeleton(r);asset=root.find('asset');world=root.find('worldbody')
    base=add(world,'body',name='fixture',pos=pt([r['tx'],r['ty'],0]),euler=val([0,0,r['ta']]))
    box(base,'base',(0,0,2),(28,15,2),MET)
    pins={}
    for s in steps:
        for x,k,b in s['interfaces']:
            col=s['column'] if s['column']!='LR' else ('L' if x<0 else 'R')
            pins[x]=(k,stacks[col]+1.5)
    for j,(x,(k,z)) in enumerate(pins.items()):mesh(asset,base,'pin'+str(j),poly(k,0,r['scale'])+[x,0],4,z,GOLD)
    for j,s in enumerate(steps):
        th=s['thickness'];x,y,a=r['staging'][j]
        body=add(world,'body',name='part'+str(j),pos=pt([x,y,th/2+.05]),euler=val([0,0,a]))
        add(body,'freejoint',name='free'+str(j));add(body,'inertial',pos='0 0 0',mass='.035',diaginertia='.000002 .000006 .000007')
        for h,(p,k,bore) in enumerate(s['interfaces']):
            hx=r['span']/2 if len(s['interfaces'])==2 else 10
            surround(asset,body,f'piece{j}_{h}',poly(bore,r['gap'],r['scale']),np.array([p-s['mid'],0]),(-hx,hx,-10,10),th)
    add(world,'camera',name='worktop',pos='0 0 .292',xyaxes='1 0 0 0 1 0',fovy='43')
    m=mj.MjModel.from_xml_string(E.tostring(root,encoding='unicode'));return m,mj.MjData(m),steps
def judge(m,d,r,s,j):
    body=m.body('part'+str(j)).id;pos=d.xpos[body]*1000;rot=d.xmat[body].reshape(3,3)
    margins=[]
    for x,k,b in s['interfaces']:
        world=(poly(k,0,r['scale'])+[x,0])@R(r['ta']).T+[r['tx'],r['ty']]
        verts=(world-pos[:2])@rot[:2,:2]-[x-s['mid'],0];hole=poly(b,r['gap'],r['scale']);edges=np.roll(hole,-1,axis=0)-hole
        rel=verts[None,:,:]-hole[:,None,:];margins.append(float(((edges[:,None,0]*rel[:,:,1]-edges[:,None,1]*rel[:,:,0])/np.linalg.norm(edges,axis=1)[:,None]).min()))
    tilt=float(np.degrees(np.arccos(rot[2,2].clip(-1,1))));height=float(pos[2]);ok=min(margins)>=-.15 and tilt<3 and abs(height-(s['bottom']+s['thickness']/2))<.55
    return dict(seat=bool(ok),height=height,tilt=tilt,margins=margins)

