"""Continuous-state, multi-free-body closed-loop kit assembly. Only joint actuator targets move parts."""
from geometry13 import *
from PIL import Image
def scene(id,recipe,seed):
    rng=np.random.default_rng(seed);n=len(RECIPES[recipe])
    # Two columns of staging nests. The wider bridge parts occupy alternating rows.
    layout=[[-83,-47],[-30,-47],[-83,0],[-30,0],[-83,47],[-30,47],[42,-50],[42,50]]
    slots=rng.permutation(8)
    staging=[[float(layout[i][0]+rng.uniform(-1.5,1.5)),float(layout[i][1]+rng.uniform(-1.5,1.5)),float(rng.uniform(-8,8))] for i in slots[:n]]
    return dict(id=id,recipe=recipe,seed=seed,span=float(rng.uniform(20,23)),scale=float(rng.uniform(.92,1.13)),gap=float(rng.choice([.75,1.15,1.55])),ta=float(rng.uniform(-8,8)),tx=float(rng.uniform(39,48)),ty=float(rng.uniform(-7,11)),staging=staging,trays=[int(i) for i in slots[:n]])
def init(m,d):
    d.qpos[:6]=[.065,-.054,-.063,0,0,0];d.ctrl[:]=d.qpos[:6];mj.mj_forward(m,d);mj.mj_step(m,d,nstep=200)
def arm(d):return np.r_[d.qpos[:2]*1000,148+d.qpos[2]*1000,np.degrees(d.qpos[3])]
def move(m,d,pose,jaw,steps,log=None,idx=None):
    start=d.ctrl.copy();x,y,z,a=pose;end=np.array([x/1000,y/1000,(z-148)/1000,np.radians(a),jaw,jaw])
    assert -106<x<106 and -65<y<65 and 0<z<115 and abs(a)<=86,(x,y,z,a)
    for j in range(steps):
        t=(j+1)/steps;d.ctrl[:]=start+(end-start)*t*t*(3-2*t);mj.mj_step(m,d)
        if log is not None and j%40==0:
            contacts=set();pref='piece'+str(idx)+'_'
            for c in d.contact:
                a=m.geom(c.geom1).name;b=m.geom(c.geom2).name
                if a.startswith(pref):contacts.add(b)
                if b.startswith(pref):contacts.add(a)
            log.append(dict(t=round(d.time,3),grip=bool({'leftpad','rightpad'}<=contacts),w=arm(d).round(2).tolist(),p=(d.xpos[m.body('part'+str(idx)).id]*1000).round(2).tolist()))
def perform(m,d,r,j,pick,place,steps):
    s=steps[j];trace=[];th=s['thickness'];grip=.0158
    xx,yy,ang=pick;tx,ty,ta=place;zgoal=s['bottom']+th/2+.12
    w=arm(d);move(m,d,[*w[:2],72,w[3]],0,300)
    for x,y,z,a,g,t in [(xx,yy,72,ang,0,450),(xx,yy,th/2+.35,ang,0,520),(xx,yy,th/2+.35,ang,grip,320),(xx,yy,68,ang,grip,650),(tx,ty,64,ta,grip,700),(tx,ty,zgoal,ta,grip,690),(tx,ty,zgoal,ta,0,220),(tx,ty,68,ta,0,520)]:
        move(m,d,[x,y,z,a],g,t,trace,j)
    mj.mj_step(m,d,nstep=180)
    verified=judge(m,d,r,s,j);stable0=d.xpos[m.body('part'+str(j)).id].copy();mj.mj_step(m,d,nstep=60)
    verified['drift']=float(1000*np.linalg.norm(d.xpos[m.body('part'+str(j)).id]-stable0))
    verified['lift']=bool(any(q['grip'] and q['p'][2]>35 for q in trace))
    verified['carry']=bool(any(q['grip'] and np.linalg.norm(np.subtract(q['p'][:2],[xx,yy]))>18 and q['p'][2]>38 for q in trace))
    verified['ok']=bool(verified['seat'] and verified['lift'] and verified['carry'] and verified['drift']<.35)
    return verified,trace
def ideal(r,m,d,steps,j):
    s=steps[j];b=m.body('part'+str(j)).id;p=d.xpos[b]*1000;rot=d.xmat[b].reshape(3,3);yaw=np.degrees(np.arctan2(rot[1,0],rot[0,0]))
    target=np.array([r['tx'],r['ty']])+R(r['ta'])@[s['mid'],0]
    return [*p[:2],yaw],[*target,r['ta']]
def qa(arg):
    i,k=arg;r=scene('QA'+str(i),k,11767+i);m,d,steps=make(r);init(m,d);out=[]
    for j,s in enumerate(steps):
        p,a=ideal(r,m,d,steps,j)
        if abs(p[0])>104 or abs(p[1])>63:out.append(dict(ok=False,detail='unreachable staging after prior contact',p=p));break
        p[2]=(p[2]+90)%180-90
        try:v,_=perform(m,d,r,j,p,a,steps)
        except AssertionError as ex:out.append(dict(ok=False,detail=str(ex)));break
        out.append(v)
    return k,out,[judge(m,d,r,s,i)['seat'] for i,s in enumerate(steps)]
if __name__=='__main__':
    import multiprocessing as mp
    results={}
    with mp.get_context('spawn').Pool(4) as pool:
        for k,out,final in pool.imap_unordered(qa,enumerate(RECIPES)):
            results[k]={'components':out,'final':final};print(k,[r['ok'] for r in out],final,flush=True)
            Path('commission.json').write_text(json.dumps(results,indent=2))

