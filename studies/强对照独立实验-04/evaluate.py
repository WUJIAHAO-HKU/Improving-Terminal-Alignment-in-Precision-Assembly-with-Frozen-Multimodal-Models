"""Paired evaluation against full-budget measurement with identical action acceptance."""
import numpy as np
from scipy.stats import t
from rules4 import D,read,save,sha

def compare(a,b):
    v=(a-b).reshape(40,10).mean(1)*100
    mean=float(v.mean());se=float(v.std(ddof=1)/np.sqrt(40))
    lower=float(mean-se*t.ppf(.95,39))
    rng=np.random.default_rng(411059)
    boot=v[rng.integers(0,40,(50000,40))].mean(1)
    return dict(diff=mean,lower=lower,ci=[float(mean-se*t.ppf(.975,39)),float(mean+se*t.ppf(.975,39))],
               boot=float(np.quantile(boot,.05)),p=float(t.sf((mean+5)/se,39)) if se>0 else None,
               wins=int((a>b).sum()),losses=int((a<b).sum()),cross=bool(se>0 and lower>-5))
def main():
    for n,h in read(D/'before-replay.json').items(): assert sha(D/n)==h
    rows=sorted(read(D/'manifest.json'),key=lambda r:(r['batch'],r['k']))
    dec=read(D/'decisions.json');raw=read(D/'scores.json');acts=read(D/'actions.json')
    scores={(v['id'],v['mode']):v for v in raw}
    assert len(scores)==len(raw)==1200
    sources=list((D/'isolated-responses').glob('*.json'));assert len(sources)==800
    for p in sources:
        r=read(p); measured=r['mode']=='measured'
        assert ('Additional rendered RGB-D measurement' in r['prompt'])==measured
        assert r['model']=='gpt-6.2-sol' and r['action']==acts[r['id']]['always' if measured else 'direct']
    for r in rows:
        key=r['id'];r.update(dec[key])
        r['scores']={mode:dict(scores[key,mode],action=action) for mode,action in acts[key].items()}
    d,m,o=[np.array([r['scores'][mode]['success'] for r in rows],int) for mode in ('direct','always','oracle')]
    accepted,oldaccepted=[np.array([r[k] for r in rows],bool) for k in ['accept','oldaccept']]
    rank,oldrank=[np.array([r[k] for r in rows]) for k in ['rank','oldrank']]
    full=np.where(accepted,m,d); oldfull=np.where(oldaccepted,m,d)
    res=dict(n=len(rows),direct=int(d.sum()),always=int(m.sum()),strong=int(full.sum()),oldstrong=int(oldfull.sum()),oracle=int(o.sum()),
             strong_change=compare(full,oldfull),budgets={})
    for k in range(11):
        use=rank<=k;old=oldrank<=k
        assert np.all(use.reshape(40,10).sum(1)==k)
        policy=np.where(use,full,d)
        oldpolicy=np.where(old,oldfull,d)
        mixed=np.where(old,full,d)
        b=dict(measured=40*k,ours=int(policy.sum()),old=int(oldpolicy.sum()),oldrank_newgate=int(mixed.sum()),
            vs_strong=compare(policy,full),vs_old=compare(policy,oldpolicy),old_vs_oldstrong=compare(oldpolicy,oldfull),
            rank_effect=compare(policy,mixed),accepted=int((use&accepted).sum()),kept=int((use&~accepted).sum()),
            good_keep=int((use&~accepted&(d>m)).sum()),wrong_reject=int((use&~accepted&(m>d)).sum()),
            skip_potential=int((~use&(m>d)).sum()),skip_shared_reject=int((~use&~accepted&(m>d)).sum()),
            skip_relative_loss=int((~use&accepted&(m>d)).sum()),skip_relative_gain=int((~use&accepted&(d>m)).sum()),by_task={})
        assert b['skip_relative_loss']==b['vs_strong']['losses'] and b['skip_relative_gain']==b['vs_strong']['wins']
        for task in ['square','round','dual']:
            mask=np.array([r['task']==task for r in rows])
            b['by_task'][task]=dict(n=int(mask.sum()),strong=int(full[mask].sum()),ours=int(policy[mask].sum()),selected=int(use[mask].sum()),skip_loss=int((~use&mask&(full>d)).sum()))
        res['budgets'][str(k)]=b
    eligible=True
    for k in ['8','6']:
        b=res['budgets'][k];b['status']='通过' if eligible and b['vs_strong']['cross'] else '未通过' if eligible else '仅描述'
        eligible=eligible and b['vs_strong']['cross']
    examples=[]
    use=rank<=6
    categories=[('漏测，强对照成功',~use&(full>d)),('已测，误拒有效修正',use&~accepted&(m>d)),
        ('保留原动作挽回成功',use&~accepted&(d>m)),('接受修正后失败',use&accepted&(d>m)),('两种动作均失败',(d==0)&(m==0)&(o==1))]
    for label,mask in categories:
        ix=np.flatnonzero(mask)
        if not len(ix):continue
        r=rows[int(ix[0])]
        for mode in ('direct','always'):
            examples.append(dict(id=r['id'],task=r['task'],gap=r['gap'],category=label,mode=mode,action=r['scores'][mode]['action']))
    save('case-outcomes.json',rows);save('summary.json',res);save('to_capture.json',examples)
if __name__=='__main__': main()
