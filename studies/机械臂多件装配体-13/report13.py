"""Generate the whole-assembly report and checks from completed, paired robot rollouts."""
from pathlib import Path
from collections import Counter
import json
from catalog import RECIPES
from decide13 import D,read
P=D.parent/'JMS论文'
MODELS=['gpt-6.2-sol','gpt-6.1-terra']
def name(m):return m.split('-')[-1].capitalize()
def fail(v):
    for j,e in enumerate(v['events']):
        if not e['lift']:return j,'grasp or lift'
        if not e['carry']:return j,'bilateral transport'
        if not e['ok']:return j,'released alignment or stability'
    for j,y in enumerate(v['final']):
        if not y:return j,'final stack alignment'
    return None,'complete'
def main():
    import matplotlib as mpl
    mpl.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    from PIL import Image
    scenes=read(D/'scenes.json');sets={m:read(D/(m+'-summary.json')) for m in MODELS}
    assert len(scenes)==100 and len(RECIPES)==20
    detail=[];execs=[];failure=[];mechanisms=[];qa=read(D/'commission-layout2.json')
    assert all(len(v['final'])==len(RECIPES[k]) and all(v['final']) and all(w['ok'] for w in v['components']) for k,v in qa.items())
    for m in MODELS:
        ch=read(D/(m+'-choices.json'))
        for r in scenes:
            i=r['id'];rr=read(D/'runs'/m/i/'results.json');c=ch[i]
            for mode in rr:
                v=rr[mode];j,why=fail(v)
                assert (j is None)==v['complete'],(i,m,mode)
                detail.append(dict(model=m,id=i,recipe=r['recipe'],mode=mode,complete=v['complete'],attempts=len(v['events']),planned=len(v['final']),individually_completed=sum(x['ok'] for x in v['events']),first_failure=j,reason=why))
            chosen='overhead' if c['rank']<=4 and c['accept']['overhead'] else 'first'
            v=rr[chosen];j,why=fail(v)
            if j is not None:failure.append(dict(model=m,id=i,recipe=r['recipe'],chosen=chosen,stage=j+1,component=RECIPES[r['recipe']][j].label,reason=why,first_event=v['events'][0],last_observed=v['events'][-1],final=v['final']))
            twin=rr['overhead']['complete']-rr['first']['complete']
            mechanisms.append(dict(id=i,model=m,rank=c['rank'],gated=c['accept']['overhead'],gain_switch=twin))
        for mode in ['first','repeat','depth','overhead','geometry','geometry_top','geometry_depth']:
            s=[a for a in detail if a['model']==m and a['mode']==mode]
            execs.append(dict(model=m,mode=mode,successful=sum(x['complete'] for x in s),attempted_components=sum(x['attempts'] for x in s),completed_components=sum(x['individually_completed'] for x in s),first_failure=dict(Counter(x['reason'] for x in s))))
    report=dict(unique_assemblies=100,num_recipes=20,models=MODELS,branches=detail,component_counts=execs,failures=failure,allocation=mechanisms)
    (D/'kit-report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    tex=r'''\section{Model-commanded multi-component assemblies}
The four fixtures test a single release. A partially assembled product makes an earlier error consequential for later operations. We therefore evaluated 20 slip-fit recipes on a common gantry. Each recipe has a fixed base and two to seven loose components. Single-post recipes stack spacers, washers or keyed plates. The remaining recipes introduce two mating columns, bridges supported by earlier components and upper retainers. These designs share a modular part library. An independent commissioning scene for each recipe passed with exact-pose commands. All subsequent results use model commands on five fresh scenes per recipe, with randomized staging, dimensions and fixture poses.

The model received the bill of materials, assembly order, approximate nest locations, camera calibration and an unmarked oblique image. Its first call identified the grasps and the mating frame for the first component. The controller executed that component, released it and acquired a new image. A second model call used this image to command the remaining placements as a sequence. Each grasp, lift, translation, insertion and release used joint actuators and two frictional fingers. A failed lift or transport stopped the sequence. Pose error after release could persist to later components. The model had one scheduled visual update between components. Longer recipes therefore examine execution of an action sequence after that update; the per-insertion feedback retry was tested separately in the two-pin pilot.

We held the first component and its post-release physical state fixed across alternative commands. The geometric comparison inherits both the model's first placement and its predicted grasps, then uses a calibrated contour estimate for the remaining placement frame. The three model arms shared the same sensing budget and available first proposal. Each new information request provided initial and live views in the selected modality, whereas the repeated-RGB arm supplied the same images again. At 80\% coverage this costs 280 logical model calls per 100 kits in each model arm. The geometric placement comparison uses 100 common first-component calls. Budget fractions count optional requests per kit. An assembly passed only when each component had been lifted with both fingers, carried, released and individually seated and all prescribed interfaces still passed at the end. The complete assembly is the unit of analysis.

'''
    tex+=r'''\begin{table}[!htbp]\centering\small
\caption{Complete assemblies out of 100. Each extra-call modality has 80 requests. Switch executes the second action when requested. Gate permits retention. Geom80 provides the geometry controller with the corresponding measurements, using the common model grasps and first placement.}\label{tab:kitmechanism}
\begin{tabular}{@{}llrrrr@{}}\toprule Model & Optional input & First & Switch & Gate & Geom80\\\midrule
'''
    for m in MODELS:
        t=sets[m]['totals']
        for mod,disp in [('repeat','Repeated RGB'),('depth','Registered depth'),('overhead','Overhead RGB')]:
            tex+=f"{name(m)} & {disp} & {t['direct']} & {t[mod+'_4_switch']} & {t[mod+'_4_gate']} & {t[mod+'_4_geo']}"+r'\\'+'\n'
    tex+=r'\bottomrule\end{tabular}\end{table}'+'\n\n'
    tex+=r'''Table~\ref{tab:kitrecipe} reports whole-product yields for all recipes. Five variants per recipe support descriptive comparisons. The paired primary analysis pools the 100 scenes in the 20 prespecified batches. It uses the four-task confidence rule and a separate family of comparisons. '''
    for m in MODELS:
        t=sets[m]['totals']
        for k in [4,3]:
            v=sets[m]['paired'][f'overhead_{k}_gate']
            tex+=f"{name(m)} at {100-20*k}\\% saving completed {t[f'overhead_{k}_gate']}/100 versus {t['overhead_5_gate']}/100 under full overhead sensing (difference {v['diff']:+.1f} pp, lower limit {v['lower']:.2f} pp, {v['decision']}). "
    tex+='\n\n'+r'''\begin{table}[!htbp]\centering\small
\caption{Held-out multi-component assemblies. $p$ is the number of moving pieces. The fixed base adds one component. Each cell counts whole assemblies out of five. F, G, 80 and 100 denote first RGB, oblique RGB geometry, 80\% gated overhead, and full gated overhead.}\label{tab:kitrecipe}
\begin{tabular}{@{}lr rrrr rrrr@{}}\toprule & &\multicolumn{4}{c}{Sol}&\multicolumn{4}{c}{Terra}\\\cmidrule(lr){3-6}\cmidrule(l){7-10}
Assembly recipe & $p$ & F&G&80&100&F&G&80&100\\\midrule
'''
    for recipe,parts in RECIPES.items():
        nums=[]
        for m in MODELS:
            s=[r for r in sets[m]['rows'] if r['recipe']==recipe];assert len(s)==5
            nums.extend(sum(r[k] for r in s) for k in ['direct','geo','overhead_4_gate','overhead_5_gate'])
        tex+=recipe[3:]+' & '+str(len(parts))+' & '+' & '.join(map(str,nums))+r'\\'+'\n'
    tex+=r'\bottomrule\end{tabular}\end{table}'+'\n\n'
    for m in MODELS:
        c=next(x for x in execs if x['model']==m and x['mode']=='first');s=[x for x in failure if x['model']==m]
        tex+=f"Across first-action runs, {name(m)} individually completed {c['completed_components']} of {c['attempted_components']} attempted component operations. The 100 recipes scheduled {sum(len(RECIPES[x['recipe']]) for x in scenes)} operations before early stops. "
        if s:
            v=max(s,key=lambda a:(a['stage'],len(a['final']),a['id']));tex+=f"In {v['id']} ({v['recipe'][3:]}), the earliest failed check under the 80\\% overhead policy occurred at component {v['stage']}, the {v['component']}, during {v['reason']}. "
    tex+=r'''The archive provides each component's bilateral contact trace and post-release measurements, including later displacement of a previously placed component. The protocol measures seating in simulated slip-fit assemblies. Torque, electrical function, and long-term retention require additional tests.
'''
    (P/'robot-kits.tex').write_text(tex,encoding='utf8')
    p=P/'deployment-results.tex';s=p.read_text(encoding='utf8')
    if r'\input{robot-kits}' not in s:p.write_text(s.replace(r'\section{Conclusion}',r'\input{robot-kits}'+'\n'+r'\section{Conclusion}'),encoding='utf8')
if __name__=='__main__':main()
