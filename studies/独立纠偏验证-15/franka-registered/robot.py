from station import *
class Bench:
    def __init__(self,k,video=None):
        self.m,self.d,self.c=make(k);self.log=[];self.video=video;self.frames=[];self.tick=0
        self.tmp=mj.MjData(self.m);self.ren=None
        self.latches=[0.,0.];self.active=-1
        self.turns=[self.m.joint('turn'+str(j)) for j in range(2)]
        self.cap=self.m.body('part'+str(len(self.c['parts'])-1)).id
        self.step(120)
    def snap(self,cam='top'):
        if self.ren is None:self.ren=mj.Renderer(self.m,height=360,width=480)
        self.ren.update_scene(self.d,camera=cam);return self.ren.render().copy()
    def step(self,n):
        for _ in range(n):
            clamp=0.
            for n,joint in enumerate(self.turns):
                if n!=self.active:
                    # Non-backdriving screw below the simulated breakaway torque.
                    idx=joint.dofadr[0];err=self.latches[n]-self.d.qpos[joint.qposadr[0]]
                    self.d.qfrc_applied[idx]=np.clip(.4*err-.012*self.d.qvel[idx],-1.1,1.1)
                over=max(0.,self.latches[n]-self.c['travel']*2*math.pi/self.c['pitch'])
                clamp+=min(16.,12.*over)
            self.d.xfrc_applied[self.cap,2]=-clamp
            mj.mj_step(self.m,self.d);self.tick+=1
            if self.video and self.tick%40==0:self.frames.append(self.snap('video'))
    def ik(self,point,site):
        m,d=self.m,self.tmp;d.qpos[:]=self.d.qpos;idx=m.site(site).id;desired=np.diag([1.,-1.,-1.]);limits=m.jnt_range[:7]
        for _ in range(110):
            mj.mj_forward(m,d);rot=d.site_xmat[idx].reshape(3,3)
            ang=sum(np.cross(rot[:,j],desired[:,j]) for j in range(3))*.5
            dx=np.r_[point-d.site_xpos[idx],ang]
            if np.linalg.norm(dx[:3])<.00012 and np.linalg.norm(ang)<.003:break
            jp=np.zeros((3,m.nv));jr=jp.copy();mj.mj_jacSite(m,d,jp,jr,idx)
            J=np.vstack([jp[:,:7],jr[:,:7]]);h=J.T@np.linalg.solve(J@J.T+np.eye(6)*.00012,dx)
            d.qpos[:7]=np.clip(d.qpos[:7]+np.clip(h,-.14,.14),limits[:,0]+.001,limits[:,1]-.001)
        return d.qpos[:7].copy()
    def move(self,point,grip,site='tcp',n=250):
        d=self.d;point=np.array(point);n=max(n,500);j=self.ik(point,site);start=d.ctrl[:7].copy();d.ctrl[7]=grip
        for k in range(n):
            t=(k+1)/n;d.ctrl[:7]=start+(j-start)*t*t*(3-2*t);self.step(1)
        self.step(220)
    def contact(self,j):
        g=self.m;hits=set()
        for v in self.d.contact:
            ns=[g.geom(i).name or '' for i in [v.geom1,v.geom2]]
            if any(n.startswith('piece'+str(j)+'-') for n in ns):
                for side in ('left','right'):
                    if any(n.startswith(side+'_finger') for n in ns):hits.add(side)
        return sorted(hits)
    def pos(self,j):return self.d.xpos[self.m.body('part'+str(j)).id].copy()
    def assembled(self,j):
        p=self.c['parts'][j];pos=self.pos(j);target=np.r_[np.array(self.c['target'])+[p['x'],p['y']],p['z']+p['h']/2]
        tilt=np.rad2deg(np.arccos(np.clip(self.d.xmat[self.m.body('part'+str(j)).id][8],-1,1)))
        return dict(xy_mm=float(np.linalg.norm(pos[:2]-target[:2])*1000),z_mm=float((pos[2]-target[2])*1000),tilt=float(tilt),seated=bool(np.linalg.norm(pos[:2]-target[:2])<.004 and abs(pos[2]-target[2])<.002 and tilt<4))
    def place(self,j,pick,target):
        p=self.c['parts'][j];z=p['h']/2
        self.move([*pick,.145],255);self.move([*pick,z+.001],255,n=340);self.closeval=max(0,(p['half_y']-.004)/.04*255);self.d.ctrl[7]=self.closeval;self.step(400)
        self.move([*pick,.13],self.closeval,n=340);lift=self.pos(j);l=self.contact(j)
        self.move([*target,.13],self.closeval,n=350);car=self.pos(j);g=self.contact(j)
        self.move([*target,p['z']+z+.003],self.closeval,n=360);release=min(255,(p['half_y']+.007)/.04*255);self.d.ctrl[7]=release;self.step(180);self.move([*target,.155],release);self.step(120)
        v=dict(component=p['name'],pick=list(pick),target=list(target),lift_mm=1000*lift[2],lift_contact=l,carry_contact=g,transport_mm=1000*np.linalg.norm(car[:2]-lift[:2]),**self.assembled(j))
        v['ok']=bool(len(l)==len(g)==2 and lift[2]>.065 and v['transport_mm']>35 and v['seated']);return v
    def tighten(self,n,xy,target_torque):
        d,m=self.d,self.m;c=self.c;last=c['parts'][-1];z=last['z']+last['h']+.006
        self.move([*xy,.14],255,'driver');self.move([*xy,z+.0005],255,'driver',340)
        ss=m.site('socket'+str(n)).id;bit=m.site('driver').id
        ang=m.joint('turn'+str(n));adv=m.joint('advance'+str(n));qa=ang.qposadr[0];qs=adv.qposadr[0];va=ang.dofadr[0]
        # Tool and shaft are coupled only when their axes coincide and the assembled flange
        # is over the matching boss. Opposing thread/head reaction is a constitutive surrogate.
        xbase=np.array(c['target'])+[c['bolts'][n],0];eng=False;trace=[];trip=False;valid=0
        self.active=n
        for t in range(2200):
            p=d.site_xpos[ss];bt=d.site_xpos[bit];er=np.linalg.norm(p[:2]-bt[:2]);errboss=np.linalg.norm(p[:2]-xbase)
            axial=bt[2]-p[2];align=bool(er<.004 and errboss<.004 and -.004<axial<.006 and self.assembled(len(c['parts'])-1)['seated'])
            a=float(d.qpos[qa]);travel=float(d.qpos[qs]);speed=float(d.qvel[va]);over=max(0,a-c['travel']*2*math.pi/c['pitch'])
            load=(.035 if a>.005 else 0)+.7*over
            if align:
                eng=True;u=min(1.15,max(0,.022*(20-speed)+load));d.qfrc_applied[va]=u-load
                if load>=target_torque:valid+=1
                else:valid=0
                if valid>=5:trip=True
            else:u=0.;d.qfrc_applied[va]=0
            if t%10==0 or trip:trace.append(dict(time=round(t*.002,4),angle_rad=a,depth_mm=1000*travel,reaction_Nm=load if align else 0.,drive_Nm=u,axis_error_mm=er*1000,engaged=align))
            if trip:break
            self.step(1)
        self.active=-1;self.latches[n]=float(d.qpos[qa]) if eng else 0.;d.qfrc_applied[va]=0;self.move([*xy,.15],255,'driver')
        return dict(bolt=n,engaged=eng,stop=trip,ok=bool(trip and trace[-1]['depth_mm']>=2.9),trace=trace)
    def savevideo(self,p):
        if self.frames:
            import cv2
            out=cv2.VideoWriter(str(p),cv2.VideoWriter_fourcc(*'mp4v'),12.5,(480,360))
            for im in self.frames:out.write(im[:,:,::-1])
            out.release()

