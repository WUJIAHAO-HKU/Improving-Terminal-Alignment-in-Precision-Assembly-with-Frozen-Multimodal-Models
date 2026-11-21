"""Compile verified data from the locked four-task study, with task-level and paired failure counts."""
from pathlib import Path
import json,hashlib,csv,io
from zipfile import ZipFile,ZIP_DEFLATED
from collections import defaultdict,Counter
import numpy as np
from PIL import Image
from analyze import main as analyze
D=Path(__file__).resolve().parent;P=D.parent/'JMS论文'
MODELS=['gpt-6.2-sol','gpt-6.1-terra'];TASKS=['twin','blade','dshaft','connector']
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def main():
    rows=read(D/'scenes.json')
    coverage=[];counts=[];cases=[];audit={};alltr=[]
    for model in MODELS:
        analyze(model);summary=read(D/(model+'-summary.json'));decisions=read(D/(model+'-choices.json'));actions=read(D/(model+'-evaluate.json'))
        tr=summary['cases'];assert len({r['id'] for r in tr})==100
        for r in tr:
            i=r['id'];out=read(D/'sim'/model/i/'outcomes.json');grip=read(D/'sim'/model/i/'grip.json')
            choices=decisions[i];meta=next(v for v in rows if v['id']==i)
            alltr.append(dict(model=model,**r))
            for label in ['first','repeat','depth','overhead','geometry','geometry_top']:
                y=out[label]
                if not y['ok']:
                    cases.append(dict(model=model,id=i,task=r['task'],mode=label,reason=y['reason'],height_mm=y.get('height'),signed_margin_mm=y.get('margin'),bilateral=grip['bilateral'],rank=choices['rank'],action=actions[i][label],gap=meta['gap']))
        for task in TASKS+['all']:
            sub=[v for v in tr if task=='all' or task==v['task']]
            counts.append(dict(model=model,task=task,n=len(sub),**{key:sum(v[key] for v in sub) for key in ('direct','geo','repeat_4_gate','depth_4_gate','overhead_4_gate','overhead_3_gate','overhead_5_gate','overhead_4_switch','depth_4_switch','repeat_4_switch','overhead_4_geo','depth_4_geo')}))
        for k in [4,3]:
            audit[model+str(k)]=summary['NI'][f'overhead_{k}_gate']
    (D/'combined.json').write_text(json.dumps(dict(counts=counts,noninferiority=audit,failures=cases),indent=2),encoding='utf8')
    table=[]
    for x in counts:
        name=('Sol' if x['model']==MODELS[0] else 'Terra')+' / '+dict(twin='two pins',blade='slot',dshaft='D-flat',connector='two ports',all='all')[x['task']]
        table.append(name+' & '+' & '.join(str(x[k]) for k in ['n','direct','geo','repeat_4_gate','depth_4_gate','overhead_4_gate','overhead_3_gate','overhead_5_gate'])+r'\\')
    lines=[]
    for m in MODELS:
        for k in [4,3]:
            a=audit[m+str(k)]
            lines.append(f"At {20 if k==4 else 40}\\% saving, {'Sol' if m==MODELS[0] else 'Terra'} seated {a['ok']}/100 versus {a['full']}/100, with a difference of {a['diff_pp']:.1f} pp and a one-sided 97.5\\% lower limit of {a['lower_pp']:.2f} pp ({a['decision']}).")
    failtxt=[]
    for m in MODELS:
        off=[v for v in cases if v['model']==m and v['mode']=='overhead' and v['signed_margin_mm'] is not None]
        if off:
            q=off[0]
            failtxt.append(f"For {m.split('-')[-1].capitalize()} case {q['id']} ({q['task']}), the overhead candidate finished at {q['height_mm']:.2f}\\,mm with a minimum containment margin of {min(q['signed_margin_mm']):.2f}\\,mm. The nominal seated height is 7\\,mm.")
    tex=r'''\section{Unmarked robot placement under a sensing budget}
We next locked a four-task comparison before generating a fresh cohort of 100 scenes in 20 independent five-part batches. Each fixture occurred 25 times. A foreground guard and new mating dimensions were used in every scene. In the dual-port fixture both sockets can receive the part. The instruction identifies the near or far port, and only containment at that port credits the episode. Both models commanded the grasp. After lifting, each placement proposal conditioned on the initial image and a live post-lift image. An additional call either repeated these inputs, added a registered depth image, or added an overhead RGB view. A placement command authorized transport, lowering and release through the actuator controller. Every alternative started from the same measured post-grasp robot state for that model. Endpoint scoring incorporated verified transport, release, stability, physical height, tilt and shape-specific containment. A failed grasp counted against all alternatives.

A frozen ranker compared the first model action with an RGB geometric estimate, normalized by clearance. The geometry estimator used natural brass contours and camera calibration. The two-slot comparison ranked pairs using the order's near/far specification. The acceptance rule retained the action closer to the geometry estimate available in the respective observation condition. Geometry-only placement used the same model-commanded grasp, sensing list and camera, then executed the contour estimate without a placement-model call. Under an 80\% budget each model arm uses 100 grasp decisions, 100 initial proposals and 80 additional calls. Geometry uses the 100 shared grasp calls. All query and simulation alternatives were acquired offline for pairing.

\begin{table}[!htbp]\centering\small
\caption{Successful released robot assemblies. Repeat, Depth and Top use the same 80 additional observations or calls per 100 parts and allow retention. Top60 and Full use 60 and 100 overhead observations. Geom uses RGB for placement.}\label{tab:robot4}
\begin{tabular}{@{}lrrrrrrrr@{}}\toprule
Model / fixture & $n$ & First & Geom & Repeat & Depth & Top & Top60 & Full\\\midrule
'''+ '\n'.join(table)+r'''
\bottomrule\end{tabular}\end{table}

The primary contrast uses the overhead modality and a paired five-point noninferiority margin. We adjusted for the two models and tested 20\% saving first within model. Insufficient evidence at 20\% leaves its 40\% comparison descriptive. A zero observed paired variance is inconclusive under the locked rule. '''+' '.join(lines)+'\n\n'+' '.join(failtxt)+r''' The per-family sample sizes support descriptive counts. No per-family noninferiority guarantee was tested.
'''
    (P/'robot-four.tex').write_text(tex,encoding='utf8')
    p=P/'deployment-results.tex';s=p.read_text(encoding='utf8')
    if r'\input{robot-four}' not in s:p.write_text(s.replace(r'\section{Conclusion}',r'\input{robot-four}'+'\n'+r'\section{Conclusion}'),encoding='utf8')
    with ZipFile(P/'output/robot-four-task-records.zip','w',ZIP_DEFLATED,compresslevel=2) as z:
        for p in D.iterdir():
            if p.is_file() and p.suffix in ('.py','.json'):z.write(p,p.name)
        for name in ['responses','sim','initial']:
            for p in (D/name).rglob('*'):
                if p.is_file():z.write(p,p.relative_to(D).as_posix())
        z.writestr('README.txt','Study 12. Four unmarked physical robot tasks, 100 unique scenes, two requested models sharing the scenes. Grasp under model control and all alternative placements physically replayed. See lock.json and combined.json. Model observations and hidden outcome/scene data must be kept separate during evaluation.')
if __name__=='__main__':main()

