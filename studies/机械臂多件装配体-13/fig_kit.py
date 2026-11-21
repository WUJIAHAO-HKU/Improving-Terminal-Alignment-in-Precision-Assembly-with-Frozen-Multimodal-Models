from pathlib import Path
from report13 import D,P,MODELS,read
import numpy as np
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
from catalog import RECIPES
from PIL import Image
def main():
    fig,axes=plt.subplots(1,3,figsize=(9.5,3.35),layout='constrained',gridspec_kw={'width_ratios':[1,1.1,1]})
    sets={m:read(D/(m+'-summary.json')) for m in MODELS}
    for m,c in zip(MODELS,['#126562','#b65736']):
        name=m.split('-')[-1].capitalize();t=sets[m]['totals'];xx=[60,80,100];yy=[t[f'overhead_{k}_gate'] for k in (3,4,5)]
        axes[0].plot(xx,yy,'o-',color=c,label=name,lw=1.8)
        for x,y in zip(xx,yy):axes[0].annotate(str(y),(x,y),xytext=(0,6),textcoords='offset points',ha='center',fontsize=8,color=c)
        rows=sets[m]['rows'];groups=[[v for v in rows if len(RECIPES[v['recipe']]) in sizes] for sizes in [(2,),(3,),(4,),(5,6,7)]]
        rate=[100*sum(v['overhead_4_gate'] for v in grp)/len(grp) for grp in groups]
        x=np.arange(4)+( -.17 if m==MODELS[0] else .17);axes[1].bar(x,rate,.33,color=c)
    axes[0].set(xlabel='Kits remeasured (%)',ylabel='Complete kits (out of 100)',xticks=[60,80,100],ylim=(0,104));axes[0].set_title('Sensing budget',fontsize=11);axes[0].legend(frameon=False)
    axes[1].set(xticks=np.arange(4),xticklabels=['2','3','4','5–7'],xlabel='Moving pieces per kit',ylabel='Whole-kit success (%)',ylim=(0,104));axes[1].set_title('80% overhead budget',fontsize=11)
    for a in axes[:2]:
        a.spines[['top','right']].set_visible(False);a.grid(axis='y',alpha=.15)
    rec=D/'recordings'/'selected.json'
    if rec.exists():
        v=read(rec)[0];folder=D/'recordings'/(v['model']+'-'+v['id']);p=sorted(folder.glob('stage-*.png'))[-1];im=Image.open(p)
        axes[2].imshow(im);axes[2].set_title('Robot camera after release',fontsize=11);axes[2].set_xlabel(f"{v['model'].split('-')[-1].capitalize()} • {v['id']}\n{v['recipe'][3:]}",fontsize=9)
    else:
        im=Image.open(D/'observations'/'K19-0'/'initial-eye.jpg');axes[2].imshow(im);axes[2].set_title('Seven-piece bill of materials',fontsize=10);axes[2].set_xlabel('K19-0 • before the first grasp',fontsize=9)
    axes[2].set_xticks([]);axes[2].set_yticks([])
    fig.savefig(P/'figures/fig10-kits.pdf',bbox_inches='tight');plt.close(fig)
    p=P/'robot-kits.tex';s=p.read_text(encoding='utf8')
    if 'fig10-kits' not in s:
        s+=r'''\paperfig{fig10-kits.pdf}{Complete multi-component assemblies with overhead sensing. Left, all budget levels use the same 100 scenes. Middle, at 80\% coverage the four groups contain 20, 35, 20 and 25 scenes in order of the number of moving pieces. Changes across groups also reflect their interface geometries. Right, an actual robot-camera view of a kit.}{kitsBudget}
'''
        p.write_text(s,encoding='utf8')
if __name__=='__main__':main()
