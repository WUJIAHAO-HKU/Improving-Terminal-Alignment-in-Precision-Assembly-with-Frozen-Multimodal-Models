"""Numerical sensitivity at the two tightest square clearances, all independently inferred actions."""
import numpy as np
from server import Rig,samples,read,dump
out=[];actions=read('actions.json')
for gap in (.5,.25):
    rig=Rig('square',gap)
    original=float(rig.s.model.opt.timestep)
    rig.s.model.opt.timestep=original/2
    for r in samples():
        if r['task']!='square' or r['gap']!=gap:continue
        for mode,a in actions[r['id']].items():
            rig.pose(r,*a)
            for _ in range(800):rig.s.step()
            prior=rig.s.data.body_xpos[rig.hid].copy()
            for _ in range(100):rig.s.step()
            stable=np.linalg.norm(rig.s.data.body_xpos[rig.hid]-prior)<.001
            ok,h,lat,tilt=rig.geometry()
            out.append(dict(id=r['id'],gap=gap,mode=mode,dt=original/2,
                success=bool(ok and stable),height=float(h),lateral=float(lat),tilt=float(tilt)))
    rig.e.close()
dump('square-refined.json',out)
