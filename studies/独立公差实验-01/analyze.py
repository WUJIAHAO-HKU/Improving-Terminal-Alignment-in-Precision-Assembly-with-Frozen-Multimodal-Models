"""Paired inference and figure generation from retained physical outcomes."""
import json, math
from pathlib import Path
from collections import Counter
import numpy as np
from scipy.stats import beta
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
D=Path(__file__).resolve().parent
def load(name):return json.loads((D/name).read_text())
def save(name,data):(D/name).write_text(json.dumps(data,indent=2),encoding='utf-8')
tasks=['square','round','dual'];gaps=[4,2,1,.5,.25]
modes=['direct','always','on_demand','terra','oracle']
truth={r['id']:r for r in load('manifest.json') if r['split']=='test'}
policy=load('locked-gate.json');actions=load('actions.json')
l=load('scores.json');idx={(r['id'],r['mode']):r for r in l}
assert len(idx)==len(l)==len(truth)*5
runs=[]
for key,r in truth.items():
    state=dict(r);state['trigger']=r['gap']<=policy[r['task']]
    state['outcomes']={m:dict(idx[key,m],action=actions[key][m]) for m in modes}
    for m in modes:
        rez=state['outcomes'][m];a=rez['action']
        rez['residual_xy_mm']=[round(a[0]+r['x'],3),round(a[1]+r['y'],3)]
        assert math.isfinite(rez['height']) and math.isfinite(rez['lateral'])
    assert state['outcomes']['on_demand']['success']==state['outcomes']['always' if state['trigger'] else 'direct']['success']
    runs.append(state)
def summary(rows):
    return {**{m:sum(r['outcomes'][m]['success'] for r in rows) for m in modes},'measure':sum(r['trigger'] for r in rows),'n':len(rows)}
by_gap={str(g):summary([r for r in runs if r['gap']==g]) for g in gaps}
by_task={t:{str(g):summary([r for r in runs if r['gap']==g and r['task']==t]) for g in gaps} for t in tasks}
rng=np.random.default_rng(4191)
arr=np.array([[[int(next(r for r in runs if (r['task'],r['gap'],r['k'])==(t,g,k))['outcomes'][m]['success']) for m in modes] for g in gaps] for t in tasks for k in range(8)]).reshape(3,8,5,5)
def paired_boot(sub):
    draws=rng.integers(0,8,size=(12000,len(sub),8))
    selected=np.stack([sub[i][draws[:,i,:]] for i in range(len(sub))],axis=1)
    delta=(selected[...,2]-selected[...,1]).mean(axis=(1,2,3))*100
    return np.quantile(delta,[.025,.975]).tolist()
harm_seed=int(((arr[:,:,:,1]>arr[:,:,:,2]).any(axis=2)).sum())
harm_upper=float(beta.ppf(.95,harm_seed+1,24-harm_seed)) if harm_seed<24 else 1
fx=load('fixtures.json')
out=dict(gate=policy,all=summary(runs),by_gap=by_gap,by_task=by_task,paired_boot_CI_pp=paired_boot(arr),
         nut_only=summary([r for r in runs if r['task']!='dual']),nut_only_CI=paired_boot(arr[:2]),
         harmful_seed_count=harm_seed,upper95_chance_seed_has_harm=harm_upper,
         fixture_correct=sum(z['expected']==z['strict'] for z in fx),fixture_official=sum(z['expected']==z['official'] for z in fx),
         paired_harm=sum(r['outcomes']['always']['success'] and not r['outcomes']['on_demand']['success'] for r in runs),
         paired_gain=sum(r['outcomes']['on_demand']['success'] and not r['outcomes']['always']['success'] for r in runs))
save('summary.json',out);save('test-outcomes.json',runs)
print(json.dumps(out))
# Full candidate list and a deterministic set of contrasting cases, based on observed outcomes.
picked=[]
for tag,pred in [
    ('skipped_measurement_failed',lambda r:not r['trigger'] and not r['outcomes']['direct']['success'] and r['outcomes']['always']['success']),
    ('measurement_recovered',lambda r:r['trigger'] and not r['outcomes']['direct']['success'] and r['outcomes']['always']['success']),
    ('measurement_hurt',lambda r:r['outcomes']['direct']['success'] and not r['outcomes']['always']['success']),
    ('both_failed',lambda r:not r['outcomes']['direct']['success'] and not r['outcomes']['always']['success'])]:
    options=[r for r in runs if pred(r) and r['outcomes']['oracle']['success']]
    options.sort(key=lambda r:(r['task']=='dual',abs(r['gap']-1),r['id']))
    if options:
        r=options[0]
        for m in ['direct','always']:picked.append(dict(id=r['id'],gap=r['gap'],task=r['task'],category=tag,mode=m,action=r['outcomes'][m]['action']))
save('to_capture.json',picked)
fig,axs=plt.subplots(1,3,figsize=(12,4.15),sharey=True)
for j,(ax,t) in enumerate(zip(axs,tasks)):
    for m,label,col,mark in [('direct','Sol direct','#49516b','o'),('always','Always measure','#cf8030','s'),('on_demand','On demand','#268478','^')]:
        ys=[100*by_task[t][str(g)][m]/8 for g in gaps]
        ax.plot(range(5),ys,label=label,color=col,linestyle='--' if m=='on_demand' else '-',marker=mark,markersize=6,alpha=.88)
    ax.set_xticks(range(5),[str(g) for g in gaps]);ax.set_ylim(-4,105);ax.set_title(['Square nut','Round nut','Held plate / pin fixture'][j]);ax.set_xlabel('One-sided clearance (mm)');ax.grid(axis='y',alpha=.2);ax.spines[['right','top']].set_visible(False)
axs[0].set_ylabel('Strict seating success (%)');handles,labels=axs[0].get_legend_handles_labels();fig.legend(handles,labels,loc='lower center',ncol=3,frameon=False)
fig.suptitle('Paired held-out clearance sweep · 8 independent scene seeds per task',fontsize=13)
fig.tight_layout(rect=[0,.09,1,.93]);fig.savefig(D/'clearance-results.png',dpi=190);plt.close(fig)

