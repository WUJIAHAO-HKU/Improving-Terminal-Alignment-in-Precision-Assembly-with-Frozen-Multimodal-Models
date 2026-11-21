"""Generate manuscript evidence panels from archived paired simulation outcomes."""
from pathlib import Path
import json,shutil
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image
D=Path(__file__).resolve().parent
P=D.parent;O=D/'figures'
def rd(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def folder(k):return next(P.glob('*'+k))
def summary(k):return rd(folder(k)/'summary.json')
blue='#3d6890';teal='#19756a';gold='#a46228';slate='#52616d'
plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42})
def finish(fig,name):
    fig.savefig(O/(name+'.pdf'),bbox_inches='tight',pad_inches=.07,dpi=180);plt.close(fig)
def clearance():
    data=rd(folder('01')/'validated'/'test-outcomes.json');gaps=[4,2,1,.5,.25]
    f,axs=plt.subplots(2,3,figsize=(9,4.4),layout='constrained',sharex=True,height_ratios=[1,1])
    for j,(task,lab) in enumerate(zip(['square','round','dual'],['Square bore','Round bore','Held pair'])):
        top,bottom=axs[:,j]
        for mode,color,marker in [('direct',slate,'o'),('always',teal,'s')]:
            n=[sum(v['outcomes'][mode]['success'] for v in data if v['task']==task and v['gap']==g) for g in gaps]
            top.plot(range(5),n,color=color,marker=marker,label='RGB only' if mode=='direct' else 'RGB-D')
        for k,g in enumerate(gaps):
            rows=[v for v in data if v['task']==task and v['gap']==g]
            for h,r in enumerate(rows):
                u=r['outcomes']['direct'];bottom.scatter(k+(h-3.5)*.055,np.linalg.norm(u['residual_xy_mm']),s=13,facecolor=teal if u['success'] else 'none',edgecolor=teal if u['success'] else gold,linewidth=.8)
        top.set_title(lab);top.set_ylim(-.35,8.6);top.set_yticks([0,2,4,6,8]);bottom.set_ylim(bottom=0);bottom.set_xticks(range(5),['4','2','1','0.5','0.25']);bottom.set_xlabel('One-sided clearance (mm)')
        top.grid(axis='y',alpha=.2);bottom.grid(axis='y',alpha=.2)
    ylim=max(a.get_ylim()[1] for a in axs[1]);[a.set_ylim(0,ylim) for a in axs[1]]
    axs[0,0].legend(fontsize=8,loc='lower left');axs[0,0].set_ylabel('Seated / 8');axs[1,0].set_ylabel('RGB residual (mm)')
    finish(f,'fig3-clearance')
def budgets():
    ranked=summary('04')['budgets'];s=summary('05')['budgets'];f,(ax,b)=plt.subplots(1,2,figsize=(9,3.3),layout='constrained',width_ratios=[1.15,1])
    x=np.arange(11);ax.plot(10*x,[ranked[str(i)]['ours']/4 for i in x],'-o',color=slate,ms=4,label='Batch ranking (400)')
    ax.plot([0,60,80,100],[198/3,235/3,238/3,242/3],'--s',color=teal,label='Natural stream (300)')
    ax.set(xlabel='Parts measured (%)',ylabel='First-pass seating (%)',ylim=(59,86));ax.grid(alpha=.2);ax.legend(fontsize=8)
    for pos,(k,st,col) in enumerate([('8','ranking',slate),('6','ranking',slate),('8','stream',teal),('6','stream',teal)]):
        v=ranked[k]['vs_strong'] if st=='ranking' else s[k]['stream_natural']['vs_strong']
        b.plot([v['lower'],v['diff']],[pos,pos],color=col,lw=2);b.plot(v['lower'],pos,'|',color=col,ms=10);b.plot(v['diff'],pos,'o',color=col)
    b.axvline(-5,color=gold,ls='--',label='NI margin');b.axvline(0,color='#bbb',lw=1);b.set_ylim(3.6,-.6)
    b.set_yticks(range(4),['Ranking · 20% saved','Ranking · 40% saved','Stream · 20% saved','Stream · 40% saved']);b.set_xlabel('Budget minus full measurement (pp)');b.grid(axis='x',alpha=.2);b.legend(fontsize=8,loc='upper left',bbox_to_anchor=(0,1.18))
    finish(f,'fig4-budget')
def cases():
    geom=folder('07'); data=rd(geom/'case-outcomes.json');items=rd(geom/'to_capture.json')
    f,ax=plt.subplots(3,4,figsize=(8.9,5.7),layout='constrained'); index=['E01P02','E00P05','E00P01']
    for j,i in enumerate(index):
        v=data[i];dec=v['decisions']['8'];mode=dec['modes'];img=Image.open(folder('05')/'frames'/(i+'.jpg'));p=v['localization'][mode['cv']]
        ax[j,0].imshow(img);ax[j,0].plot(*p['hole_uv'],'o',mfc='none',mec='#00e9cb',ms=7);ax[j,0].plot(*p['peg_uv'],'+',color='#ff8d12',ms=9)
        ax[j,0].set_ylabel(i+'\n'+v['task']+' · '+str(v['gap'])+' mm',fontsize=9)
        for k,m in enumerate(['cv','sol']):
            n=next(l for l,x in enumerate(items) if x['id']==i and x['method']==m)
            ax[j,k+1].imshow(Image.open(geom/'failure_views'/f'{n:02d}.jpg').crop((240,0,480,240)))
            ok=v['outcomes'][mode[m]]['success'];ax[j,k+1].text(.03,.96,'Seated' if ok else 'Failed',va='top',transform=ax[j,k+1].transAxes,color='white',fontsize=8,bbox=dict(facecolor=teal if ok else gold,edgecolor='none',pad=2))
        if i=='E00P01':
            ax[j,3].imshow(Image.open(O/'e00p01-rgb-endpoint.jpg').crop((240,0,480,240)))
            ax[j,3].text(.03,.96,'Seated',va='top',transform=ax[j,3].transAxes,color='white',fontsize=8,bbox=dict(facecolor=teal,edgecolor='none',pad=2))
        else:
            label='RGB already executed' if not dec['measured'] else 'First action: '+('seated' if v['outcomes']['sol_rgb']['success'] else 'failed')
            ax[j,3].text(.5,.5,label,ha='center',va='center',fontsize=9,color=slate,transform=ax[j,3].transAxes)
    for a in ax.flat:a.set_xticks([]);a.set_yticks([]);[s.set_visible(False) for s in a.spines.values()]
    for a,s in zip(ax[0],['Input + fitted centers','Geometry endpoint','Sol policy endpoint','Sol RGB alternative']):a.set_title(s,fontsize=9)
    finish(f,'fig5-paired-cases')
if __name__=='__main__':
    clearance();budgets();cases();shutil.copyfile(folder('08')/'output'/'deployment-frontier.pdf',O/'fig6-deployment.pdf')

