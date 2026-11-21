"""Pre-specified, batch-paired analysis; scored terminal outcomes are never used by a selector."""
import json,math,csv
from pathlib import Path
import numpy as np
from scipy.stats import t as student
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from rules import METHODS,BUDGETS
D=Path(__file__).resolve().parent
def read(n):return json.loads((D/n).read_text(encoding='utf-8-sig'))
def save(n,v):(D/n).write_text(json.dumps(v,indent=2,ensure_ascii=False),encoding='utf-8')
def diffstat(a,b):
    x=(a-b).mean(axis=1)
    mu=np.mean(x);se=np.std(x,ddof=1)/np.sqrt(len(x));df=len(x)-1
    p=student.sf(mu/se,df) if se>0 else float(1 if mu<=0 else 0)
    return dict(diff_pp=100*mu,ci_pp=[100*(mu-student.ppf(.975,df)*se),100*(mu+student.ppf(.975,df)*se)],one_sided_p=float(p),lower95_pp=100*(mu-student.ppf(.95,df)*se),wins=int((a>b).sum()),losses=int((a<b).sum()))
def etest(j,al,k):
    d=(j-al).mean(axis=1);q=(10-k)/10
    assert np.all(np.abs(d)<=q+1e-8)
    lam=np.array([.25,.5,.75,.99])/(q-.05)
    return float(np.exp(np.log(1+lam[:,None]*(d[None,:]+.05)).sum(axis=1)).mean())
def main():
    r=sorted(read('manifest.json'),key=lambda v:(v['batch'],v['k']))
    rank={v['id']:v for v in read('locked-ranks.json')};sc={(v['id'],v['mode']):v for v in read('scores.json')};actions=read('actions.json')
    assert len(sc)==900 and len({v['seed'] for v in r})==300
    for v in r:
        v['ranks']=rank[v['id']]['ranks'];v['rgb_quality']=rank[v['id']]['quality'];v['scores']={m:dict(sc[v['id'],m],action=actions[v['id']][m]) for m in ['direct','always','oracle']}
    a={m:np.array([v['scores'][m]['success'] for v in r],int).reshape(30,10) for m in ['direct','always','oracle']}
    ranks={m:np.array([v['ranks'][m] for v in r]).reshape(30,10) for m in METHODS}
    by={};stopped=False
    for k in BUDGETS:
        ys={m:np.where(ranks[m]<=k,a['always'],a['direct']) for m in METHODS}
        assert all(np.all((ranks[m]<=k).sum(axis=1)==k) for m in METHODS)
        comparisons={m:diffstat(ys['joint'],ys[m]) for m in METHODS if m!='joint'}
        stats=diffstat(ys['joint'],a['always']);e=etest(ys['joint'],a['always'],k)
        eligible=not stopped;passed=eligible and e>=20
        if not passed:stopped=True
        by[str(k)]=dict(counts={m:int(y.sum()) for m,y in ys.items()},comparisons=comparisons,vs_always=stats,e=e,eligible=eligible,ni_pass=passed)
    base=by['6']['comparisons'];ordered=sorted(['clearance','view'],key=lambda m:base[m]['one_sided_p']);prev=0
    for i,m in enumerate(ordered):
        prev=max(prev,min(1,(2-i)*base[m]['one_sided_p']));base[m]['holm_p']=prev
    sub={}
    for t in ['square','round','dual']:
        rr=[v for v in r if v['task']==t]
        sub[t]=dict(n=len(rr),always=sum(v['scores']['always']['success'] for v in rr),direct=sum(v['scores']['direct']['success'] for v in rr))
        sub[t].update({m:sum(v['scores']['always' if v['ranks'][m]<=6 else 'direct']['success'] for v in rr) for m in METHODS})
    save('summary.json',dict(baselines={m:int(y.sum()) for m,y in a.items()},budgets=by,by_task=sub))
    save('case-outcomes.json',r)
    with (D/'budget-results.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.writer(f);w.writerow(['measured per 10','measured total','saved %',*METHODS,'always','joint-always pp','one-sided e','eligible','NI passed'])
        for k in BUDGETS:
            b=by[str(k)];w.writerow([k,30*k,(10-k)*10,*[b['counts'][m] for m in METHODS],int(a['always'].sum()),round(b['vs_always']['diff_pp'],3),round(b['e'],5),b['eligible'],b['ni_pass']])
    def isp(v,m):return v['ranks'][m]<=6
    def succ(v,m):return v['scores'][m]['success']
    choices=[
        ('joint_skip_harms',lambda v:not isp(v,'joint') and succ(v,'always') and not succ(v,'direct')),
        ('joint_measures_harms',lambda v:isp(v,'joint') and succ(v,'direct') and not succ(v,'always')),
        ('joint_beats_simple',lambda v:isp(v,'joint') and not(isp(v,'clearance') and isp(v,'view')) and succ(v,'always') and not succ(v,'direct')),
        ('simple_rescues_joint_skip',lambda v:not isp(v,'joint') and (isp(v,'clearance') or isp(v,'view')) and succ(v,'always') and not succ(v,'direct')),
        ('both_actions_fail',lambda v:not succ(v,'direct') and not succ(v,'always') and succ(v,'oracle'))]
    pick=[];taken=set()
    for lab,predicate in choices:
        options=[v for v in r if predicate(v) and v['id'] not in taken]
        if not options:continue
        v=sorted(options,key=lambda w:(w['task']=='dual',w['id']))[0];taken.add(v['id'])
        for m in ['direct','always']:pick.append(dict(id=v['id'],task=v['task'],gap=v['gap'],category=lab,mode=m,action=v['scores'][m]['action']))
    save('to_capture.json',pick)
    fig,ax=plt.subplots(figsize=(7.8,4.6));colors=['#985844','#557998','#176851']
    for m,label,c in zip(METHODS[:3],['Clearance only','View only','Joint'],colors):
        ax.plot([10*k for k in reversed(BUDGETS)],[by[str(k)]['counts'][m]/3 for k in reversed(BUDGETS)],marker='o',color=c,label=label)
    ax.axhline(a['always'].mean()*100,color='#242424',linestyle='--',label='Always measure');ax.set_xlabel('Extra measurements per 100 cases');ax.set_ylabel('Strict seating success (%)')
    ax.set_title('Held-out assembly · 30 independent batches of 10');ax.legend(ncol=2,frameon=False);ax.grid(axis='y',alpha=.2);fig.tight_layout();fig.savefig(D/'budget-frontier.png',dpi=190);plt.close(fig)
if __name__=='__main__':main()

