from pathlib import Path
import json,hashlib,sys,shutil
from collections import defaultdict
from policy15 import *
D=Path(__file__).resolve().parent;R=D.parent;A=R/'机械臂四任务独立验证-12';B=R/'机械臂多件装配体-13'
sys.path.insert(0,str(B))
from recipe_info import spec
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,v):p.write_text(json.dumps(v,indent=2),encoding='utf8')
def main():
    out={};audit=[]
    for dest,old,kit,files in [('four',A,False,['design.py','gantry.py','profiles.py','server.py','collect12.py','policy.py']),('kits',B,True,['scenes13.py','render_kit.py','frame.py','kit.py','geometry13.py','catalog.py','camera.py','recipe_info.py','collect13.py','decide13.py'])]:
        p=D/dest
        for n in files:shutil.copyfile(old/n,p/n)
        ss=p/('scenes13.py' if kit else 'design.py');s=ss.read_text(encoding='utf-8-sig');s=s.replace('8382642','334071097').replace('f"K','f"N') if kit else s.replace('764310211','519823073').replace("f'B","f'H")
        ss.write_text(s,encoding='utf8');shutil.copyfile(D/'policy15.py',p/'policy15.py')
        for m in ['gpt-6.2-sol','gpt-6.1-terra']:
            choices=read(old/(m+'-choices.json'));acts=read(old/(m+('-plans.json' if kit else '-evaluate.json')))
            gr=defaultdict(list)
            for r in read(old/'scenes.json'):
                i=r['id'];cat,L,shift=features(r,kit,spec);ch=choices[i];y=read(old/('runs' if kit else 'sim')/m/i/('results.json' if kit else 'outcomes.json'));ok='complete' if kit else 'ok'
                if kit:
                    from decide13 import geometry
                    a=[read(old/'responses'/m/(i+'-'+k+'.json'))['anchor'] for k in ('first','overhead')];ref,valid=geometry(r,'top','overhead')
                    if not valid:ref,_=geometry(r,'eye','first');shift=0
                else:a=[vec(acts[i][k]) for k in ('first','overhead')];ref=vec(acts[i]['geometry_top'])
                new=gate(*a,ref,L,shift);delta=int(y['overhead'][ok])-int(y['first'][ok]);gr[cat].append(delta*new)
                if not kit and ((m.endswith('sol') and ch['rank']<=4 and not ch['accept']['overhead'] and delta==1) or (m.endswith('terra') and ch['rank']>=4 and ch['accept']['overhead'] and delta)):
                    audit.append(dict(model=m,id=i,task=cat,gap=r['gap'],rank=ch['rank'],old_pre=ch['pre'],first_distance=metric(a[0],ref,L),top_distance=metric(a[1],ref,L),first_height=y['first']['height'],top_height=y['overhead']['height'],gain=delta,revised_accept=new))
            mean=sum(map(sum,gr.values()))/sum(map(len,gr.values()))
            out[dest+'_'+m]={k:(sum(v)+8*mean)/(len(v)+8) for k,v in gr.items()}
        (p/'gain.json').write_text(json.dumps({k:v for k,v in out.items() if k.startswith(dest)},indent=2))
    write(D/'development-cases.json',audit)
    desc="Matched previous two cohorts as development only. New 100 four-fixture and 100 kit episodes, 5 per BOM. Two visual models, first and overhead from same state. Old and new allocations and gates evaluated on same candidates. Primary compare revised overhead+gate at 80 and 60 to revised 100. 20 blocks of 5 per cohort; one-sided 97.5% lower paired batch t > -5pp, zero variance inconclusive; 80 before 60 per model, cohorts separate. Report first-pass endpoints including early failures. Difficulty mix and robot unchanged; four-task port is the order-selection fixture. New rules estimate net benefit by public shape family and model; additive group smoothing of strength 8, bounded pre-disagreement as tiebreaker; D-profile top reference offset follows nominal CAD. No endpoint, true pose, new cohort feedback or future optional inputs used in selection."
    for p in (D/'four',D/'kits'):
        names=sorted(list(p.glob('*.py'))+[p/'gain.json']);write(p/'lock.json',dict(protocol=desc,sha256={n.name:hashlib.sha256(n.read_bytes()).hexdigest() for n in names}))
if __name__=='__main__':main()
