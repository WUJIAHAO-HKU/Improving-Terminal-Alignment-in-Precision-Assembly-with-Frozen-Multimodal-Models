from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
import hashlib,json,re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image
D=Path(__file__).resolve().parent;P=D.parent/'JMS论文'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def main():
    rows=read(D/'pilot-summary.json');assert len(rows)==12
    fig,axes=plt.subplots(2,4,figsize=(7.3,3.55),layout='constrained')
    import cv2
    for axrow,model in zip(axes,('gpt-6.2-sol','gpt-6.1-terra')):
        folder=D/'runs'/(model+'-R01');cap=cv2.VideoCapture(str(folder/'execution.mp4'));stages=[]
        for p in sorted(folder.glob('req*.json')):
            j=int(p.stem[3:]);stages.append((read(p)['action']['op'],len(read(folder/f'{j:02}.json')['trace'])))
        ends=[];total=0
        for name,n in stages:total+=n;ends.append((name,total-1))
        idx=[next(t for a,t in ends if a==name) for name in ('pick','insert','retry','release')]
        for ax,t,title in zip(axrow,idx,('Lift','First insertion','Retract and correct','After release')):
            cap.set(cv2.CAP_PROP_POS_FRAMES,t);ok,im=cap.read();assert ok;ax.imshow(cv2.cvtColor(im,cv2.COLOR_BGR2RGB));ax.set_xticks([]);ax.set_yticks([])
            if model=='gpt-6.2-sol':ax.set_title(title,fontsize=9)
        cap.release();axrow[0].set_ylabel('Sol' if model=='gpt-6.2-sol' else 'Terra')
    fig.savefig(P/'figures/fig8-gantry.pdf');plt.close(fig)
    tex=r'''\section{Closed-loop manipulation of an unmarked two-pin cover}
The preceding experiments apply a proposed part displacement directly. We separately tested a Cartesian robot with three independently actuated linear axes, a yaw wrist and two opposed friction fingers in MuJoCo 3.8.1. Each model located the loose cover in a calibrated oblique image and commanded a grasp by its two hole centers. The low-level controller converted pixels to metric setpoints, closed the jaws and lifted. The model then located the pin pair, commanded transport and chose whether to request an overhead view. From the live view it either retained the transport pose or issued a relative correction. After insertion it decided whether to release or retract and retry using the image and wrist tracking error. Part motion throughout the episode resulted from gravity and contact. Only robot actuators received commands. An episode counted as successful if bilateral contact lifted the cover above 25\,mm, persisted during transport, and after release both pin residuals were within the per-side clearance plus 0.15\,mm, height was 6.6--7.5\,mm, tilt was below 3 degrees and final drift below 0.35\,mm.

Four unmarked scenes shared by Sol and Terra varied staging pose, pin spacing and clearance. Both models completed 4/4 assemblies after release. Both requested overhead sensing on all four. Sol retained the original alignment on all four; Terra retained three. These small paired counts demonstrate closed-loop execution but provide no evidence of sensing savings. We separately injected a single actuator-side lateral disturbance during insertion on two additional scenes. Both models retracted and retried once on each. Sol recovered 2/2 and Terra recovered 1/2. These deliberately induced incidents have a separate denominator from the four nominal scenes.

\paperfig{fig8-gantry.pdf}{Frames from continuous simulation recordings on the same disturbed scene R01. Both models commanded a retraction. After release the Sol cover rested on the support and the Terra cover remained on the pin tops. Motion between frames was simulated with actuator and contact dynamics.}{gantry}
On R01 the actuator disturbance was $-5$\,mm. Sol retained its transport pose before the disturbance; Terra had already revised its pose by $-2$\,mm along $X$. Each model later compensated the encoder displacement by about $+5$\,mm. The resulting Sol pin residuals were 0.70 and 0.56\,mm, with a 7.00\,mm final height. Terra's residuals were 2.33 and 2.27\,mm, with a stable but incomplete 17.00\,mm final height. Correcting the actuator error therefore left a pre-existing alignment error in the Terra trajectory. The experiment provides an end-to-end example; it does not isolate the causal effect of the earlier revision on that scene.
'''
    (P/'closed-loop-pilot.tex').write_text(tex,encoding='utf8')
    p=P/'deployment-results.tex';s=p.read_text(encoding='utf8')
    if 'closed-loop-pilot' not in s:p.write_text(s.replace(r'\section{Conclusion}',r'\input{closed-loop-pilot}'+'\n'+r'\section{Conclusion}'),encoding='utf8')
    p=P/'manuscript.tex';s=p.read_text(encoding='utf8')
    if 'separate robot-trajectory' not in s:p.write_text(s.replace('Release terms for the dataset','A separate robot-trajectory supplement contains the twelve closed-loop episodes, per-stage commands, contact traces and continuous recordings; its four nominal and two recovery scenes are paired across models. Release terms for the dataset'),encoding='utf8')
    with ZipFile(P/'output/closed-loop-robot-trajectories.zip','w',ZIP_DEFLATED) as z:
        for n in ['cell.py','cell_recovery.py','controller.py','recovery_controller.py','pilot-lock.json','pilot-scenes.json','recovery-scenes.json','pilot-summary.json','report_pilot.py']:z.write(D/n,n)
        for folder in sorted((D/'runs').iterdir()):
            for p in sorted(folder.iterdir()):
                if p.suffix in ('.json','.png','.mp4','.jpg'):z.write(p,p.relative_to(D).as_posix())
        z.writestr('README.txt','Unmarked twin-pin cover. 4 shared nominal scenes (A), 2 separate injected disturbance scenes (R), 2 requested models. Each result includes a continuous 25 fps video. reqNN are robot commands and include evaluator scene configuration. NN.json contains privileged outcome/contact traces. Model prompts, received observations and replies are separate. Do not expose evaluator state in deployment. MuJoCo 3.8.1. XYZ-yaw Cartesian gantry with friction jaws. Episode files are useful for audit; historical server paths must be adapted to rerun the client.')
if __name__=='__main__':main()

