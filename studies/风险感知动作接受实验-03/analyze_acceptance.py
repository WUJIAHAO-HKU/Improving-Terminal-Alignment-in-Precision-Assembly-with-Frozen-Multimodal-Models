"""Evaluate frozen rules on complete paired simulator outcomes."""
from collections import Counter
import json
import math
from pathlib import Path
import numpy as np
from scipy.stats import t
from policy import HERE, read, after, forecast

def write(name, value):
    (HERE/name).write_text(json.dumps(value,ensure_ascii=False,indent=2, allow_nan=False),encoding='utf8')

def paired(a,b):
    pairs=(a-b).reshape(30,10)
    means=pairs.mean(1)*100
    diff=float(means.mean())
    se=float(means.std(ddof=1)/np.sqrt(30))
    lower=diff-t.ppf(.95,29)*se
    bootstrap=means[np.random.default_rng(91322).integers(0,30,(50000,30))].mean(1)
    return dict(diff=diff, wins=int((pairs>0).sum()), losses=int((pairs<0).sum()),
                lower=float(lower),bootstrap_lower=float(np.quantile(bootstrap,.05)),
                ci=[float(diff-t.ppf(.975,29)*se),float(diff+t.ppf(.975,29)*se)],
                p_noninferior=float(t.sf((diff+5)/se,29)) if se>0 else None,
                exceeds_margin=bool(se>0 and lower > -5))
def main():
    rows=sorted(read(HERE/'manifest.json'),key=lambda r:(r['batch'],r['k']))
    lock=read(HERE/'policy-lock.json')
    acts=read(HERE/'actions.json')
    sc=read(HERE/'scores.json')
    scores={(v['id'],v['mode']):v for v in sc}
    assert len(scores)==len(sc)==3*len(rows)==900 and len(acts)==300
    old=HERE.parent/'独立公差实验-01'/'validated'
    earlier=read(old/'manifest.json')+read(old/'stress-manifest.json')+read(HERE.parent/'独立测量策略实验-02'/'manifest.json')
    for key in ['seed','angle']:
        assert not ({r[key] for r in rows} & {r[key] for r in earlier}),key
    for r in rows:
        key=r['id']
        case=lock['cases'][key]
        r['ranks']=case['ranks']
        x=after(r,case['q'],acts[key]['direct'],acts[key]['always'])
        r['gain']=float(forecast(lock['acceptance_model'],x))
        r['accept']=r['gain']>0
        r['scores']={m:dict(scores[key,m],action=a) for m,a in acts[key].items()}
    d,m,o=[np.array([r['scores'][name]['success'] for r in rows],int) for name in ('direct','always','oracle')]
    accept=np.array([r['accept'] for r in rows])
    ranks={name:np.array([r['ranks'][name] for r in rows]) for name in ('risk','clearance','view')}
    gated=np.where(accept,m,d)
    summary=dict(n=300,batches=30,direct=int(d.sum()),always=int(m.sum()),oracle=int(o.sum()),both_fail=int(((d==0)&(m==0)).sum()),
                 full_gate=int(gated.sum()),any_works=int(np.maximum(m,d).sum()),measurement_alone=paired(m,d),
                 full_gate_vs_always=paired(gated,m),budgets={})
    for k in range(11):
        selected=ranks['risk']<=k
        assert np.all(selected.reshape(30,10).sum(1)==k)
        unconditional=np.where(selected,m,d)
        final=np.where(selected,gated,d)
        kept=selected&~accept
        by_task={}
        for task in ['square','round','dual']:
            mask=np.array([r['task']==task for r in rows])
            by_task[task]=dict(n=int(mask.sum()),always=int(m[mask].sum()),policy=int(final[mask].sum()),measured=int(selected[mask].sum()))
        b=dict(measured=int(selected.sum()),kept=int(kept.sum()),accepted=int((accept&selected).sum()),
            rescued=int((kept&(d>m)).sum()),wrong_reject=int((kept&(m>d)).sum()),
            harmful_accept=int((selected&accept&(d>m)).sum()),beneficial_accept=int((selected&accept&(m>d)).sum()),
            skip_harm=int((~selected&(m>d)).sum()),skip_gain=int((~selected&(d>m)).sum()),
            gated=int(final.sum()),unconditional=int(unconditional.sum()),
            clearance=int(np.where(ranks['clearance']<=k,m,d).sum()),view=int(np.where(ranks['view']<=k,m,d).sum()),
            vs_always=paired(final,m),vs_full_gate=paired(final,gated),vs_unconditional=paired(final,unconditional),by_task=by_task)
        assert b['gated']-b['unconditional']==b['rescued']-b['wrong_reject']
        summary['budgets'][str(k)]=b
    enabled=True
    for k in ['8','6']:
        b=summary['budgets'][k]
        b['confirmatory']='通过' if enabled and b['vs_always']['exceeds_margin'] else '未通过' if enabled else '仅描述'
        enabled=enabled and b['vs_always']['exceeds_margin']
    # Deterministic first eligible ID for each decision at K=6. No cherry-picked magnitudes.
    used=set()
    choices=[]
    for name,mask in [('挽回原动作',(ranks['risk']<=6)&~accept&(d>m)),
        ('误拒补测动作',(ranks['risk']<=6)&~accept&(m>d)),('接受后反而失败',(ranks['risk']<=6)&accept&(d>m)),
        ('漏测导致失败',(ranks['risk']>6)&(m>d)),('两种动作都失败',(d==0)&(m==0)&(o==1))]:
        idx=next((i for i in np.flatnonzero(mask) if rows[i]['id'] not in used),None)
        if idx is None:continue
        r=rows[idx];used.add(r['id'])
        for mode in ['direct','always']:
            choices.append(dict(id=r['id'],task=r['task'],gap=r['gap'],mode=mode,category=name,action=acts[r['id']][mode]))
    write('summary.json',summary);write('case-outcomes.json',rows);write('to_capture.json',choices)
if __name__=='__main__': main()
