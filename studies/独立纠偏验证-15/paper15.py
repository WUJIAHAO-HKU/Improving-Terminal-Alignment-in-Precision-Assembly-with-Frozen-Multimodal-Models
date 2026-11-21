from analysis15 import *
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
from zipfile import ZipFile,ZIP_DEFLATED
P=D.parent/'JMS论文';O=P/'output'
names=['Single-post bearing retainer','Shimmed valve bonnet','Twin support bridge','Stepped bearing housing','Double-deck guide frame']
def short(m):return m.split('-')[-1].capitalize()
def verdict(x):
    return ('descriptive' if not x['formal'] else 'pass' if x['pass_margin'] else 'inconclusive' if not x['positive_variance'] else 'not demonstrated')
def main():
    result=rd(D/'independent-results.json');cases=rd(D/'development-cases.json')
    tex=r'''\section{Failure-guided revision on independent robot scenes}
The paired endpoints in Figure~\ref{fig:robotBudgets} make two errors distinguishable. A missed measurement deprives a part of a useful observation. A rejected correction occurs after that observation is available. On the previous Sol cohort all seven harmful rejections at 80\% coverage were D-flat sleeves (B010, B018, B034, B038, B046, B050 and B098). Every overhead candidate seated at 7.0\,mm. The retained first actions ended at 14.0--16.4\,mm. The top contour's bounding-box midpoint shifts toward the round side of a truncated cylinder. Its discrepancy from the evaluator's axis was 1.76--3.15\,mm in those seven cases. The erroneous reference made a physically better correction appear worse. Geometry here is diagnostic: a visual approximation can systematically favor an incorrect action.

Terra's seven missed gains at 80\% coverage were all narrow-slot parts (B013, B021, B029, B053, B073, B077 and B093). They ranked fifth in their five-part batches. Clearances were 1.1 or 1.5\,mm. The initial and oblique-contour estimates agreed closely enough relative to clearance to suppress sensing; the retained parts stopped at 13.3--15.0\,mm. Measuring all parts also harmed one twin-pin case (B096), accounting for the net gap of six. Reducing coverage to 60\% additionally skipped a helpful connector (B059) and avoided a harmful D-flat correction (B050). A single aggregate count obscures these offsetting changes.

\subsection{Locked measurement and acceptance rules}
A nominal D-flat cross section extends from $-L/2$ to $0.22L$ along the truncation axis. The center of that interval is $-0.14L$. We translate the overhead reference $0.14L$ toward the flat; the equivalent shift for an isolated keyed kit post is $0.26$ of its nominal radius. We leave the two-post midpoint unchanged. The seven historical reference errors fell to 0.14--0.56\,mm and all seven revisions would have been accepted. This is a development-set check.

For each model and observed shape family, we use the historical net seating gain of measuring under the revised gate. The estimate shrinks toward the corresponding cohort mean with eight pseudo-observations. Its batch priority adds $0.035\min(d/c,10)/10$, where $d$ is disagreement with the initial oblique estimate and $c$ is clearance. Thus a large disagreement cannot by itself monopolize the quota. Calibration uses previous runs only. We locked the code, gain tables, batch allocation and test design before generating 100 new four-fixture scenes and 100 new kit scenes (five per recipe). Each model issued a fresh grasp or first-component command, received live feedback and proposed a first and an overhead action. Both proposals were executed from the same post-grasp or post-first-component state. Old and new rules use the same candidate pair on each scene. At 80\% coverage a policy uses 100 common grasp or first-component calls, 100 first proposals and 80 optional calls. The complete candidate archive uses 300 calls per model per cohort. We retain the previous family-wise comparison within each cohort: one-sided 97.5\% paired batch lower bound, five-point margin, 80\% before 60\%, and an inconclusive decision at zero observed batch variance.

\begin{table}[!htbp]\centering\small\caption{Fresh robot scenes. Counts are assemblies out of 100. The lower confidence limits (pp) compare each revised policy against its own full-sensing gate. Old80 uses the original allocation and gate on the same fresh candidates.}\label{tab:rule15}
\begin{tabular}{@{}llrrrrrrr@{}}\toprule Cohort & Model & Old80 & New80 & New60 & Full & Lower80 & Lower60 & First\\\midrule
'''
    for k in ['four','kits']:
        for m in M:
            v=result[k][m];t=v['totals'];a,b=v['primary']
            tex+=' & '.join([k.capitalize(),short(m),*[str(t[x]) for x in ('old_old_4','new_new_4','new_new_3','new_new_5')],f"{a['lower_pp']:.2f}",f"{b['lower_pp']:.2f}",str(t['first'])])+r'\\'+'\n'
    tex+=r'\bottomrule\end{tabular}\end{table}'+'\n\n'
    for k in ['four','kits']:
        for m in M:
            v=result[k][m];a,b=v['primary'];t=v['totals']
            tex+=f"{k.capitalize()}, {short(m)}: at 20\\% saving the decision was {verdict(a)} (difference {a['diff_pp']:+.1f} pp); at 40\\% saving it was {verdict(b)} ({b['diff_pp']:+.1f} pp). "
    tex+='\n\n'+r'''Holding the allocation or gate fixed separates their influence on these paired candidates. At 80\% coverage the following entries give old allocation with new gate, then new allocation with old gate: '''
    tex+=', '.join(f"{k} {short(m)} {result[k][m]['totals']['old_new_4']}/{result[k][m]['totals']['new_old_4']}" for k in ['four','kits'] for m in M)+'. '
    examples=[]
    for m in M:
        rows=result['four'][m]['rows']
        improved=[a for a in rows if a['new_new_4']>a['old_old_4'] and (a['family']=='dshaft' if m==M[0] else a['family']=='blade')]
        losses=[a for a in rows if a['new_new_4']<a['old_old_4']]
        for sub in [improved,losses]:
            if not sub:continue
            a=sub[0];i=a['id'];v=rd(D/'four/sim'/m/i/'outcomes.json')
            examples.append(dict(model=m,id=i,**{x:a[x] for x in ('family','old_rank','new_rank','old_accept','new_accept','old_old_4','new_new_4')},endpoints=v))
            if 'height' in v['first'] and 'height' in v['overhead']:
                tex+=f"For {short(m)} {i} ({a['family']}), rank changed from {a['old_rank']} to {a['new_rank']}, and the 80\\% endpoint changed from {'seated' if a['old_old_4'] else 'failed'} to {'seated' if a['new_new_4'] else 'failed'}. First and overhead commands ended at {v['first']['height']:.2f} and {v['overhead']['height']:.2f}\\,mm. "
    (D/'new-cases.json').write_text(json.dumps(examples,indent=2),encoding='utf8')
    fig,axes=plt.subplots(1,2,figsize=(7.4,3.0),layout='constrained')
    for ax,k,title in zip(axes,['four','kits'],['Four fixtures','Twenty assembly recipes']):
        for m,color in zip(M,['#056d67','#b24b32']):
            vals=result[k][m]['totals'];ax.plot([60,80,100],[vals[f'new_new_{j}'] for j in (3,4,5)],'o-',label=short(m),color=color)
        ax.set(xlabel='Kits or parts remeasured (%)',ylabel='Seated out of 100',xticks=[60,80,100],ylim=(0,100),title=title);ax.grid(axis='y',alpha=.2);ax.spines[['top','right']].set_visible(False);ax.legend(frameon=False)
    fig.savefig(P/'figures/fig11-revised-budgets.pdf');plt.close(fig)
    tex+=r'''\paperfig{fig11-revised-budgets.pdf}{Revised overhead policy on two independently seeded cohorts. Each line joins the same 100 paired scenes. Intervals for the primary contrasts are in Table~\ref{tab:rule15}.}{revised15}
\section{Articulated-arm simulation with captive fasteners}
A seven-joint Franka Panda from the MuJoCo Menagerie (model source and license in the supplement) carries a parallel-jaw gripper and an offset driver. Five assemblies use two to four loose components, a fixed base and two captive screws. At each step Sol or Terra receives a current camera image and a work order, then selects a pick and placement target or a screw head. Inverse kinematics and joint servos execute the selected operation. Bilateral lift, transport, individual seating, final stack geometry and both driver stops must all pass to credit a whole assembly.

We evaluated two interfaces. Direct vision asks for pixel coordinates of the loose part, base and screw heads. A separate exploratory registered-station run supplies stock-to-nest inventory and surveyed nest and fixture frames; the model selects the nest and driver channel, and the controller uses the corresponding targets. The registered runs use a second placement seed for each recipe. The interface comparison is consequently descriptive, with one episode per model, recipe and interface. The same nominal component order and driver recipe are supplied in both.

The driver engages only if the head and boss align, the bit lies in the engagement window, and the final flange meets its seating criteria. The simulated screw has coupled hinge and slide joints at 1\,mm pitch. After 3\,mm of take-up a rotational spring increases the reaction torque. A holding law resists backdriving and an axial reaction loads the flange after tightening. The controller stops following five consecutive integration steps at or above 0.8\,Nm. These prescribed parameters describe a reduced-order screw joint; torque and travel are simulator outputs. Neither preload accuracy, thread stripping, nor release strength was experimentally validated.
\begin{table}[!htbp]\centering\small\caption{Franka simulation. Each cell lists individually placed components, qualified screws and whole-assembly success (0/1). Every episode has two captive screws. The registered conditions include an inventory and surveyed target coordinates.}\label{tab:panda15}
\begin{tabular}{@{}lrllll@{}}\toprule Assembly & Parts & Vision Sol & Vision Terra & Registered Sol & Registered Terra\\\midrule
'''
    for k,n in enumerate(names):
        vals=[next(x for x in result[w] if x['model']==m and x['task']==k) for w in ['franka','registered'] for m in M];tex+=n+' & '+str(vals[0]['nparts'])+' & '+' & '.join(f"{v['placed']}, {v['tightened']}, {int(v['complete'])}" for v in vals)+r'\\'+'\n'
    tex+=r'\bottomrule\end{tabular}\end{table}'+'\n\n'
    for w,lab in [('franka','Direct visual control'),('registered','Registered commands')]:
        rows=result[w];q=[b for v in rows for b in v['bolts'] if b['stop']]
        tex+=f"{lab} completed {sum(v['complete'] for v in rows)}/10 assemblies and {len(q)}/20 fasteners. "
        if q:tex+=f"The qualified traces terminated at {np.median([b['reaction_Nm'] for b in q]):.3f}\\,Nm, {np.median([b['angle_rad'] for b in q])/(2*np.pi):.2f} turns and {np.median([b['depth_mm'] for b in q]):.2f}\\,mm of screw travel (medians). "
    ex=rd(D/'franka/runs/gpt-6.2-sol-0/out-01.json')
    tex+=f"In the directly localized bearing retainer, Sol transported the flange with both fingers. Its released center missed the target by {ex['xy_mm']:.2f}\\,mm, exceeding the 4\\,mm criterion, and both fastening attempts failed. "
    tex+='All attempted operations and failed engagements are retained, including ten uninterrupted simulator replays per interface. These counts characterize the stated fixtures and skill interfaces in simulation.\n'
    fig,ax=plt.subplots(1,2,figsize=(7.6,3.0),layout='constrained');succ=next((v for v in result['registered'] if v['complete']),None)
    if succ:
        folder=D/'franka-registered/runs'/(succ['model']+'-'+str(succ['task']));raw=rd(sorted(folder.glob('out-*.json'))[-1])['trace'];ax[0].plot([x['angle_rad']/(2*np.pi) for x in raw],[x['reaction_Nm'] for x in raw],color='#126562');ax[0].axhline(.8,color='#a34b3a',ls='--');ax[0].set(xlabel='Screw rotation (turns)',ylabel='Simulated reaction torque (Nm)',title='Registered driver engagement')
        import cv2
        v=cv2.VideoCapture(str(folder/'execution.mp4'));v.set(cv2.CAP_PROP_POS_FRAMES,int(v.get(7)*.78));ok,im=v.read();v.release()
        if ok:ax[1].imshow(im[:,:,::-1]);ax[1].axis('off')
        fig.savefig(P/'figures/fig12-panda-fastener.pdf');tex+=r'\paperfig{fig12-panda-fastener.pdf}{A torque--turn trace from the reduced-order joint and an execution frame of the registered Franka interface. The dashed line marks the stop threshold.}{pandaFastener}'+'\n'
    plt.close(fig)
    (P/'independent-rules-panda.tex').write_text(tex,encoding='utf8')
    p=P/'deployment-results.tex';s=p.read_text(encoding='utf8')
    if 'independent-rules-panda' not in s:s=s.replace(r'\section{Conclusion}',r'\input{independent-rules-panda}'+'\n'+r'\FloatBarrier'+'\n'+r'\section{Conclusion}');p.write_text(s,encoding='utf8')
if __name__=='__main__':main()
