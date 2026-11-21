"""Render paired budget curves and actual robot endpoint images for two disagreement types."""
from pathlib import Path
import json
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image
D=Path(__file__).resolve().parent;P=D.parent/'JMS论文'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def main():
    fig=plt.figure(figsize=(10.2,5.25),layout='constrained')
    gs=fig.add_gridspec(2,5,width_ratios=[1.4,.24,1,1,1])
    ax=fig.add_subplot(gs[:,0:2]);ax.set(xlabel='Parts remeasured (%)',ylabel='Successful assemblies (out of 100)',xlim=(55,105),ylim=(30,75))
    for model,color in [('gpt-6.2-sol','#126562'),('gpt-6.1-terra','#b65736')]:
        t=read(D/(model+'-summary.json'))['totals'];y=[t[f'overhead_{k}_gate'] for k in [3,4,5]]
        ax.plot([60,80,100],y,'o-',lw=2,c=color,label=model.split('-')[-1].capitalize())
        for x,a in zip([60,80,100],y):ax.annotate(str(a),(x,a),xytext=(0,7),textcoords='offset points',ha='center',fontsize=9)
    ax.spines[['top','right']].set_visible(False);ax.grid(axis='y',alpha=.18);ax.legend(frameon=False,loc='lower right');ax.set_title('Overhead view with action acceptance',fontsize=11)
    for j,(i,name) in enumerate([('B013','Missed measurement'),('B010','Rejected correction')]):
        folder=D/'sim/gpt-6.2-sol'/i
        for k,(path,title) in enumerate([(D/'initial'/i/'00-eye.png','Before grasp'),(folder/'branch-first/02-eye.png','First action'),(folder/'branch-overhead/02-eye.png','Overhead action')]):
            a=fig.add_subplot(gs[j,k+2]);a.imshow(Image.open(path));a.set_xticks([]);a.set_yticks([])
            for sp in a.spines.values():sp.set_color('#c3cbca')
            if j==0:a.set_title(title,fontsize=10)
            if k==0:a.set_xlabel(f'{i} • '+name,fontsize=8)
            else:
                v=read(folder/'outcomes.json')['first' if k==1 else 'overhead'];a.set_xlabel(('Seated' if v['ok'] else 'Failed')+f" • {v['height']:.1f} mm",fontsize=8)
    fig.savefig(P/'figures/fig9-robot-budgets.pdf',bbox_inches='tight');plt.close(fig)
    f=P/'robot-four.tex';s=f.read_text(encoding='utf8')
    if 'fig9-robot-budgets' not in s:
        s+=r'''
\paperfig{fig9-robot-budgets.pdf}{Overhead measurement budgets and paired endpoints in the four-fixture cohort. Each line follows the same 100 scenes. Right, each row begins from the same Sol grasp and compares the two placement commands after release. Height is the center height of the released part above the table.}{robotBudgets}
In B013 the narrow-slot part ranked fifth in its batch. At 80\% sensing it received the first action and failed. The full policy measured it, accepted the overhead action and seated it. B010 isolates a separate failure on a D-flat shaft. It ranked first, so the budget supplied the overhead image. The overhead action seated the part under compulsory replacement, but the acceptance rule retained a first action that failed. The first failure concerns the allocation of an observation. The second concerns how the station acts on information it already acquired.
'''
        f.write_text(s,encoding='utf8')
if __name__=='__main__':main()
