"""Repeat selected fully physical release trials at half time step for the smallest gap."""
from server import *
out=[]
for task in ['square','round']:
    rig=Rig(task,.25)
    original=float(rig.s.model.opt.timestep)
    rows=[r for r in samples() if r['task']==task and r['gap']==.25 and r['split']=='test']
    for r in rows:
        for err in [0,.2,.4,.8,2,6,12]:
            dx,dy=-r['x']+err,-r['y']
            for factor in [1,2]:
                rig.s.model.opt.timestep=original/factor
                result=rig.rollout(r,dx,dy,450*factor)
                out.append(dict(id=r['id'],task=task,error_mm=err,dt=original/factor,**result))
    rig.e.close()
dump('timestep-check.json',out)

