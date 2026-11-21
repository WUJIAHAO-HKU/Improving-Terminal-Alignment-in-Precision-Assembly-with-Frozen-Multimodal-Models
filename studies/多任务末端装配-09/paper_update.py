from pathlib import Path
import json
D=Path(__file__).resolve().parent;P=D.parent/'JMS论文'
s=json.loads((D/'summary.json').read_text());tot=s['total']
p=P/'manuscript.tex';t=p.read_text(encoding='utf8')
t=t.replace(r'\newcommand{\cOne}{Selective measurement}',r'''\newcommand{\cData}{Paired terminal-alignment dataset}
\newcommand{\cOne}{Selective measurement}''')
t=t.replace('First, \\emph{selective measurement}',r'We organize 1,450 simulation conditions across six fixture geometries into a paired terminal-alignment dataset. First, \emph{selective measurement}')
t=t.replace('These considerations motivate three contributions.', 'Studying these decisions requires outcomes for both available actions on a common initial state. We make four contributions.')
t=t.replace(r'\item \textbf{\cOne.',r'''\item \textbf{\cData.} We assemble initial observations, optional measurements, model proposals and their separate simulator outcomes across six fixture geometries. Three orientation-sensitive fixtures form an exploratory extension to the translation cohorts.
\item \textbf{\cOne.''')
t=t.replace(r'\section{Related Work}',r'''\section{Related Work}
\subsection{\cData}
Contact-rich assembly simulation makes large numbers of terminal states accessible for evaluation~\cite{factory}. To evaluate selective sensing, the initial state alone is insufficient. The evaluator must also know whether a second action would have rescued a failed insertion or spoiled a successful one. We therefore retain the two simulated endpoints even when the deployed policy would observe only its chosen outcome.''')
t=t.replace('We consider a stream of parts whose initial orientations',r'''\subsection{\cData}
Our dataset uses the starting condition as the record key. Each record links an RGB image and its process prompt to an optional observation. A separate evaluator file stores the frozen model's candidate translations or poses and the strict seating outcome of each replay. The 1,450 records comprise 120 clearance-sweep conditions on 24 seeds, 600 development parts, the 400- and 300-part evaluation cohorts, and 30 exploratory orientation conditions. The equal-call and time studies join existing records by identifier. The historical test results are known, and the internal edition exposes the labels for audit. A new blind evaluation would require held-back conditions. Sensor types and action dimensions are recorded explicitly.

For the primary translation studies, we consider a stream of parts whose initial orientations''')
t=t.replace('The release terms for the full observation and model-response archive await author confirmation.', 'The internal v0.1 dataset contains paired observations and outcomes for 1,450 conditions. Release terms for the dataset and full model-response archive await author confirmation.')
p.write_text(t,encoding='utf8')
p=P/'deployment-results.tex';t=p.read_text(encoding='utf8').replace('The experiments isolate horizontal terminal alignment','The primary cohorts isolate horizontal terminal alignment').replace('Finally, the equal-call experiment evaluates','In the primary mixed-model cohort, the equal-call experiment evaluates').replace('It does not cover a second viewpoint, execution feedback or a model explicitly critiquing its first answer.','The separate orientation pilot evaluates a second viewpoint with a different controller. Neither experiment supplies post-execution feedback or asks the model to critique its first answer.')
t=t.replace(r'\section{Conclusion}',r'\input{orientation-pilot}'+'\n'+r'\section{Conclusion}')
p.write_text(t,encoding='utf8')
table=[]
for k,label in [('twin','Twin dowels'),('blade','Blade and slot'),('dshaft','D-flat shaft'),('total','All fixtures')]:
    row=s[k];table.append(label+' & '+' & '.join(str(row[v]) for v in ['n','rgb','repeat4','view4','view4gate','view3gate','allgate','geo'])+r'\\')
fail=s['failure_examples']; f=next((r for r in fail if r['task']=='twin'),None)
example=''
if f is not None:
    example=(' For twin-dowel case '+f['id']+', the RGB proposal left a final plate-center height of '+format(f['rgb']['height_mm'],'.2f')+r'\,mm. The second-view proposal reached '+format(f['view']['height_mm'],'.2f')+r'\,mm on the same initialized fixture; the nominal seated height was 2\,mm.')
pilot=r'''\section{Exploratory extension to orientation-sensitive insertion}
The translation studies hold initial orientation fixed. We next gave the frozen model a third action component, a yaw correction about the moving part center. In the twin-dowel fixture a single translation can center the cover while leaving the two holes on opposite sides of their respective pin axes. In the blade fixture, slot width restricts transverse motion more tightly than travel along the slot. In the D-shaped coupling the flat fixes the mating direction. Figure~\ref{fig:orientation} shows the first and optional overhead views.
\paperfig{fig7-orientation.pdf}{MuJoCo views of the three orientation fixtures. Two red fixed marks and two green moving marks have known spacing. The images in each column show the same initial pose.}{orientation}
We generated ten conditions per geometry, mixed into six batches of five. Each part started with a random horizontal offset up to 8\,mm per axis, an absolute yaw of 4--23 degrees, and a one-sided clearance of 0.5, 1 or 2\,mm. Every candidate was applied from its original state, followed by 600 one-millisecond free-release steps in MuJoCo 3.8.1. The plate center had to finish at 1.5--2.6\,mm, tilt below 3 degrees, and drift below 0.3\,mm over the last 50 steps. A final planar containment test allowed 0.15\,mm numerical tolerance and checked both pins separately. Ideal pose corrections seated 30/30; zero correction seated 1/30.

The pilot tested a separately locked, geometry-assisted decision rule. Connected components located both pairs of colored marks. Back-projection under the known marker spacings estimated the planar translation and yaw. Before measurement, the rule ranked disagreement between this estimate and the first model action, divided by clearance. The disagreement adds translation distance and the yaw error in radians times the fixture radius (16, 18 and 11\,mm, respectively). It selected the top four or three parts per five-part batch. After acquisition, it kept whichever candidate better agreed with the overhead geometric estimate. A failed overhead estimate fell back to the original geometric estimate, and ties retained the first action. A missing initial estimate received first priority. Every model call was independent. Candidate collection cost 90 valid replies; a deployed four-of-five policy uses 54 logical calls, compared with 60 under full acquisition.

\begin{table}[!htbp]\centering\small
\caption{Strict seating counts under pilot policies. Repeat and View use 24 identical selections and always switch. Gate4 and Gate3 allow retention with 24 and 18 acquisitions. Full measures all 30 and allows retention. Geom directly executes the single-view geometric correction.}\label{tab:orientation}
\begin{tabular}{@{}lrrrrrrrr@{}}\toprule
Fixture & $n$ & RGB & Repeat & View & Gate4 & Gate3 & Full & Geom\\\midrule
'''+ '\n'.join(table)+r'''
\bottomrule\end{tabular}\end{table}

'''+f"Across the 30 conditions, compulsory switching on the selected parts seated {tot['repeat4']} with repeated RGB and {tot['view4']} with the additional overhead view. Allowing retention on that same list seated {tot['view4gate']}. Direct execution of the overhead geometric estimate on all parts seated {tot['geo_top']}/30."+example+r''' These are descriptive counts. The fixtures have engineered visual references, and the policy uses calibrated geometry for selection. The comparison therefore characterizes a marked-fixture system. Ten cases per geometry do not establish a new budget guarantee or transfer of the earlier depth-based predictors.
'''
(P/'orientation-pilot.tex').write_text(pilot,encoding='utf8')

