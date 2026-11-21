"""Grade all saved predictions and replay them in the same robosuite simulator."""
import json
import math
import os
import subprocess
from pathlib import Path
from statistics import mean
import ast

ROOT = Path(__file__).resolve().parent
source = (ROOT/"simulate.py").read_text(encoding="utf-8")
cases = next(ast.literal_eval(n.value) for n in ast.walk(ast.parse(source))
             if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=="cases" for t in n.targets))
models = ["gpt-6.2-sol","gpt-6.1-terra"]
def on_plane(pixel,z):
    a=math.radians(38)
    f=168/math.tan(math.radians(15))
    u,v=(pixel[0]-167.5)/f,(pixel[1]-167.5)/f
    distance=(350*math.cos(a)-z)/(math.cos(a)+v*math.sin(a))
    return u*distance,(math.sin(a)-v*math.cos(a))*distance

def motion(row,view,mode):
    if mode=="direct":
        return row["dx"],row["dy"]
    h,p=row["hole"],row["peg"]
    if view=="overhead":
        return (p[0]-h[0])*.5582274842,(h[1]-p[1])*.5582274842
    h,p=on_plane(h,34),on_plane(p,0)
    return p[0]-h[0],p[1]-h[1]

data=[]
tight = os.getenv("ASSEMBLY_TIGHT") == "1"
for i,(x,y) in enumerate(cases):
    sample={"id":i+1,"true_correction_mm":[-x,-y],"arms":{"no_action":[0,0],"exact":[-x,-y]}}
    views=[("tight","tight-")] if tight else [("overhead",""),("oblique","oblique-"),("oblique-noheight","oblique-noheight-")]
    for view,prefix in views:
        for model in (models[:1] if tight else models):
            for mode in (["direct"] if view=="oblique-noheight" else ["direct","landmarks"]):
                rows=json.loads((ROOT/f"{prefix}{model}-{mode}-{i//4+1}.json").read_text(encoding="utf-8"))
                row=next(r for r in rows if r["id"]==i+1)
                act=motion(row,"overhead" if tight else view,mode)
                sample["arms"][f"{view}/{model}/{mode}"]=[round(v,2) for v in act]
                if tight and mode=="landmarks":
                    # Back-project the two faces at their own optical depths.
                    f=168/math.tan(math.radians(15))
                    h,p=row["hole"],row["peg"]
                    sample["arms"]["tight/landmarks+two-planes"]=[round(sign*((p[j]-167.5)*374-(h[j]-167.5)*340)/f,2)
                                                                  for j,sign in enumerate([1,-1])]
    if tight:
        rows=json.loads((ROOT/f"tight-calibrated-gpt-6.2-sol-direct-{i//4+1}.json").read_text(encoding="utf-8"))
        row=next(r for r in rows if r["id"]==i+1)
        sample["arms"]["tight/calibrated-direct"]=list(motion(row,"tight","direct"))
    data.append(sample)
actions=json.dumps([list(s["arms"].values()) for s in data],separators=(',',':'))
remote="env PYTHONDONTWRITEBYTECODE=1 MUJOCO_GL=egl NUMBA_DISABLE_JIT=1 python3 - '"+actions+"'"
if tight:
    remote=remote.replace("env ","env ASSEMBLY_TIGHT=1 ",1)
cmd=["ssh","-o","BatchMode=yes","assembly-sim-a",remote]
r=subprocess.run(cmd,input=source.encode(),capture_output=True,check=True)
replays=iter(json.loads(r.stdout))
groups={}
for s in data:
    for key,act in list(s["arms"].items()):
        obs=next(replays)
        assert obs["id"]==s["id"] and obs["action"]==act
        dx,dy=(a-b for a,b in zip(act,s["true_correction_mm"]))
        out={"action_mm":act,"residual_mm":[round(dx,2),round(dy,2)],"norm_mm":round(math.hypot(dx,dy),2),
             "seated":obs["official"],"height_mm":obs["final_above_table_mm"]}
        s["arms"][key]=out
        groups.setdefault(key,[]).append(out)
summary={k:dict(seated=sum(o["seated"] for o in vals),n=len(vals),mean_error_mm=round(mean(o["norm_mm"] for o in vals),2),
                mean_abs_x_mm=round(mean(abs(o["residual_mm"][0]) for o in vals),2),
                mean_abs_y_mm=round(mean(abs(o["residual_mm"][1]) for o in vals),2),
                worst_mm=max(o["norm_mm"] for o in vals)) for k,vals in groups.items()}
(ROOT/("tight-results.json" if tight else "results.json")).write_text(json.dumps(dict(summary=summary,cases=data),indent=2),encoding="utf-8")
print(json.dumps(summary,indent=2))

