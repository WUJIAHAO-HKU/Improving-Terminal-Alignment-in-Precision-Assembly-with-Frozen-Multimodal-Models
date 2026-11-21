from pathlib import Path
import json
from zipfile import ZipFile,ZIP_DEFLATED
from decide13 import D,read
from report13 import P,MODELS
O=P/'output';F=D.parent/'机械臂四任务独立验证-12';K=D.parent/'机械键位连接器验证-14'
def keyreport():
    qa=read(K/'key-commission.json')['outcomes']
    tx=r'''\subsection{Connector with mechanical mistake-proofing}
The paired dual-port fixture above tests selection by order. To test a physical interlock we enlarged one pin on the incompatible port to 2.15 times its nominal radius. Compatible and incompatible sides varied across new scenes. On an independent commissioning scene a correctly grasped connector seated at '''+f"{qa['compatible']['height']:.2f}"+r''' mm at the compatible port. The same centered approach at the incompatible port stopped at '''+f"{qa['incompatible']['height']:.2f}"+r''' mm and '''+f"{qa['incompatible']['tilt']:.1f}"+r''' degrees of tilt. We then froze the same placement rule and ran 25 new keyed connectors in five blocks with each model. This supplemental cohort is separate from the 100-scene primary test.

\begin{table}[!htbp]\centering\small\caption{Physically keyed connector. Whole assemblies seated out of 25. Repeat, Depth, Top and GeomTop use the same 20 selected parts. Top15 measures 15, Full measures 25. All model sensing arms permit retention.}\label{tab:key14}
\begin{tabular}{@{}lrrrrrrr@{}}\toprule Model & First & Repeat & Depth & Top & GeomTop & Top15 & Full\\\midrule
'''
    for m in MODELS:
        v=read(K/(m+'-summary.json'))['totals'];tx+=m.split('-')[-1].capitalize()+' & '+' & '.join(str(v[k]) for k in ['direct','repeat_4_gate','depth_4_gate','overhead_4_gate','overhead_4_geo','overhead_3_gate','overhead_5_gate'])+r'\\'+'\n'
    tx+=r'\bottomrule\end{tabular}\end{table}'+'\n\n'
    tx+='The two keyed-port results are descriptive because the separate cohort has only five batches. The mechanical interlock can block a wrong insertion while the end-to-end task still fails to deliver a seated part at the correct port.\n'
    (P/'robot-keyed.tex').write_text(tx,encoding='utf8')
def edit():
    p=P/'manuscript.tex';s=p.read_text(encoding='utf8')
    a=s.index('\\noindent\\textbf{Abstract.}');b=s.index('\\par\\medskip\\noindent\\textbf{Keywords}',a)
    Y=[read(D/(m+'-summary.json'))['totals']['overhead_4_gate'] for m in MODELS]
    abstract=r'''\noindent\textbf{Abstract.}
Precision assembly requires deciding when another observation justifies its cost and when the resulting action should replace the first. We evaluate frozen multimodal models on 1,450 simulated terminal-alignment conditions and a separate contact-driven robot benchmark. \emph{Selective measurement} allocates a fixed sensing budget using clearance and the first proposal. In an independent four-fixture robot test, Sol seated 67 of 100 parts with 80 overhead requests and 68 with 100. The adjusted lower confidence limit was $-4.69$ percentage points against a five-point noninferiority margin. Terra seated 42 and 48, respectively, and missed the margin. \emph{Action acceptance} retained a first RGB correction when an additional observation gave insufficient support for a change. On 300 terminal-alignment instances, adding depth at equal call count gained 10.0 percentage points over repeated RGB under compulsory replacement. Retention added 4.7 points. On the four robot fixtures, retention after overhead sensing cost Sol six successes and gained Terra one. The robot benchmark includes 20 multi-component recipes executed by a friction gripper. With 80 overhead requests per 100 kits, Sol and Terra completed '''+f'{Y[0]} and {Y[1]}'+r''' whole assemblies, respectively. \emph{Workstation time per qualified part} links these tradeoffs to rework. On 240 terminal-alignment cases, full-measurement Sol and calibrated RGB geometry crossed at an estimated 41.7 minutes of blocking rework per failure under equal setup. This last comparison uses simulated outcomes and recorded inference delays.
'''
    s=s[:a]+abstract+s[b:]
    s=s.replace('Three orientation-sensitive fixtures form an exploratory extension to the translation cohorts.', 'We extend these records with model-commanded grasp, transport, release and feedback, including a 100-scene test across four unmarked fixtures, a mechanically keyed connector cohort, and 100 whole assemblies across 20 recipes.')
    s=s.replace('The internal v0.1 dataset contains paired observations and outcomes for 1,450 conditions.', 'The internal v0.1 dataset contains paired observations and outcomes for 1,450 terminal-alignment conditions. The v0.2 robot supplement adds 231 distinct simulated scenes across its four strata (6, 100, 100 and 25), paired across the two models. The separate ideal-action commissioning episodes are excluded. Logical requests, observation files, component-level trajectories, choice ranks, whole-product outcomes and integrity hashes are included.')
    p.write_text(s,encoding='utf8')
    p=P/'deployment-results.tex';s=p.read_text(encoding='utf8')
    if r'\input{robot-keyed}' not in s:s=s.replace(r'\input{robot-kits}',r'\input{robot-keyed}'+'\n'+r'\input{robot-kits}')
    a=s.index('The paired dataset also extends evaluation');b=s.index('The practical return depends',a)
    s=s[:a]+r'''With a simulated friction gripper and four unmarked fixtures, Sol also met the margin at 20\% fewer overhead requests. Terra did not. Neither model established a 40\% saving on those fixtures. On Sol the gated overhead policy at 80\% coverage lost six successes relative to compulsory replacement on the same selected parts. The calibrated acceptance rule therefore transferred less reliably than the overhead observation itself. The 20-recipe study measures the accumulated cost of these decisions when a final product depends on several released parts. Its independent unit is the completed assembly.
    
'''+s[b:]
    p.write_text(s,encoding='utf8')
def src():
    out=O/'JMS-draft-source.zip';tmp=out.with_suffix('.new')
    items={p.name:p for p in P.glob('*.tex') if p.name!='outline.tex'}
    for n in ['fig8-gantry.pdf','fig9-robot-budgets.pdf','fig10-kits.pdf']:
        if (P/'figures'/n).exists():items['figures/'+n]=P/'figures'/n
    for d,k in [(F,'four'),(D,'kits'),(K,'keyed')]:
        for n in ('lock.json','gpt-6.2-sol-summary.json','gpt-6.1-terra-summary.json'):
            items['evidence/'+k+'/'+n]=d/n
    items['evidence/four/four-audit.json']=F/'four-audit.json'
    items['evidence/keyed/key-commission.json']=K/'key-commission.json'
    with ZipFile(out) as old,ZipFile(tmp,'w',ZIP_DEFLATED) as z:
        for n in old.namelist():
            if n not in items:z.writestr(n,old.read(n))
        for n,p in items.items():z.write(p,n)
    with ZipFile(tmp) as z:assert z.testzip() is None and len(set(z.namelist()))==len(z.namelist())
    tmp.replace(out)
if __name__=='__main__':keyreport();edit();src()
