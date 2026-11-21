from collections import Counter
import numpy as np
from scipy.stats import t
from experiment import D,P,read,save,sha,SOL,TARGETS

def stats(x):
    x=np.asarray(x);means=x.reshape(30,10).mean(1)*100
    delta=means.mean();se=means.std(ddof=1)/np.sqrt(30)
    return dict(diff=float(delta),ci=[float(delta-t.ppf(.975,29)*se),float(delta+t.ppf(.975,29)*se)],
        wins=int((x>0).sum()),losses=int((x<0).sum()),super_p=float(t.sf(delta/se,29)) if se else None,
        lower95=float(delta-t.ppf(.95,29)*se),lower975=float(delta-t.ppf(.975,29)*se),
        ni_p=float(t.sf((delta+5)/se,29)) if se else None,valid=bool(se>0))
def main():
    before=read(D/'locked-before-replay.json');assert all(sha(D/n)==v for n,v in before.items())
    acts=read(D/'actions.json');v=read(D/'gates.json');masks=read(D/'masks.json');ids=sorted(acts)
    raw=read(D/'scores.json');sc={(r['id'],r['mode']):r for r in raw}
    assert len(raw)==len(sc)==2040 and set(sc)=={(i,m) for i in ids for m in acts[i]}
    prev=read(P/'scores.json');baseline={(r['id'],r['mode']):r for r in prev}
    for i in ids:
        for new,old in [('original','direct'),('depth','always')]:
            assert all(sc[i,new][key]==baseline[i,old][key] for key in ('success','height','tilt','lateral','stable','official'))
    meta={r['id']:r for r in read(P/'manifest.json')};selected={i for b in read(D/'lock.json')['selected'] for i in b}
    prior=read(P/'decisions.json');shared6={i for b in prior['batches'] for i in b['selections']['6']['stream_natural']}
    pick=np.array([i in selected for i in ids]);y=lambda i,m:int(sc[i,m]['success'])
    def counter(m):return np.array([y(i,m) for i in ids])
    d=counter('original');dep=counter('depth')
    choices={'direct':d,'rgb_switch':np.array([y(i,'repeat') if i in selected else y(i,'original') for i in ids]),
      'rgb_gate':np.array([y(i,'repeat') if i in selected and v[i]['rgb_accept'] else y(i,'original') for i in ids]),
      'depth_switch':np.where(pick,dep,d),'depth_gate':np.array([y(i,'depth') if i in selected and v[i]['depth_accept'] else y(i,'original') for i in ids]),
      'depth_shared':np.array([y(i,'depth') if i in selected and v[i]['shared_depth_accept'] else y(i,'original') for i in ids])}
    summary={'sol':{},'sol_comparisons':{},'transfer':{},'n':len(ids),'verified_old_rollouts':600}
    for name,a in choices.items():
        accepted=0 if name=='direct' else len(selected) if 'switch' in name else sum(v[i][{'rgb_gate':'rgb_accept','depth_gate':'depth_accept','depth_shared':'shared_depth_accept'}[name]] for i in selected)
        summary['sol'][name]=dict(ok=int(a.sum()),onlist=int(a[pick].sum()),accepted=accepted,
                                    by_task={task:int(a[[meta[i]['task']==task for i in ids]].sum()) for task in ('square','round','dual')})
    for a,b in [('depth_switch','rgb_switch'),('rgb_switch','direct'),('depth_switch','direct'),('rgb_gate','rgb_switch'),
        ('depth_gate','depth_switch'),('depth_shared','rgb_gate'),('depth_gate','rgb_gate'),('depth_gate','direct'),('rgb_gate','direct')]:
        summary['sol_comparisons'][a+'-'+b]=stats(choices[a]-choices[b])
    summary['gate_interaction']=stats((choices['depth_gate']-choices['depth_switch'])-(choices['rgb_gate']-choices['rgb_switch']))
    outputs={i:dict(id=i,batch=meta[i]['batch'],task=meta[i]['task'],gap=meta[i]['gap'],angle=meta[i]['angle'],
        selected_sol=i in selected,sol={k:int(a[j]) for k,a in choices.items()},gates=v[i],candidates={
          m:dict(sc[i,m],action=act) for m,act in acts[i].items()}) for j,i in enumerate(ids)}
    for m in TARGETS:
        direct=counter(m+'_d');measured=counter(m+'_m')
        accept=np.array([v[i][m]['accept'] for i in ids]);strong=np.where(accept,measured,direct)
        sm=dict(direct=int(direct.sum()),always_switch=int(measured.sum()),strong=int(strong.sum()),
            accepted=int(accept.sum()),vs_direct=stats(strong-direct),by_task={},budgets={});eligible=True
        for task in ['square','round','dual']:
            mask=[meta[i]['task']==task for i in ids]
            sm['by_task'][task]=dict(n=sum(mask),direct=int(direct[mask].sum()),strong=int(strong[mask].sum()))
        for k in ['8','6']:
            use={i for group in masks[m][k] for i in group};assert len(use)==int(k)*30
            mask=np.array([i in use for i in ids]);out=np.where(mask,strong,direct)
            fixed=selected if k=='8' else shared6
            share=np.where([i in fixed for i in ids],strong,direct)
            diff=stats(out-strong)
            ok=eligible and diff['valid'] and diff['lower975']>-5
            b=dict(ok=int(out.sum()),calls=300+len(use),overlap=len(use&fixed),same_sol_list=int(share.sum()),vs_strong=diff,
                vs_direct=stats(out-direct),status='通过' if ok else '未通过' if eligible else '仅描述',by_task={})
            for task in ['square','round','dual']:
                ix=np.array([meta[i]['task']==task for i in ids]);b['by_task'][task]=int(out[ix].sum())
            sm['budgets'][k]=b;eligible=ok
            for j,i in enumerate(ids):
                outputs[i].setdefault('transfer',{}).setdefault(m,{})[k]=dict(measured=bool(mask[j]),ok=int(out[j]),direct=int(direct[j]),strong=int(strong[j]))
        summary['transfer'][m]=sm
    a=choices['rgb_switch'];b=choices['depth_switch']
    summary['rgb_repeat_identical']=sum(acts[i]['original']==acts[i]['repeat'] for i in selected)
    for mask,key in [((b>a)&pick,'depth_only'),((a>b)&pick,'rgb_only'),((choices['rgb_gate']>a)&pick,'rgb_keep_rescue'),((choices['rgb_gate']<a)&pick,'rgb_keep_harm')]:
        examples=[i for j,i in enumerate(ids) if mask[j]];summary.setdefault('examples',{})[key]=examples[:1]
    files=list((D/'responses').glob('*.json'));attempts=Counter()
    for p in files:
        r=read(p);attempts[r['model']]+=r['attempts']
    summary['new_attempts']=dict(attempts)
    summary['sol_attempts_540']={mode:sum(read(P/'responses'/f'{i}--{SOL}--direct.json')['attempts'] for i in ids)+sum(
        read((D if mode=='repeat' else P)/'responses'/f'{i}--{SOL}--{mode}.json')['attempts'] for i in selected) for mode in ['repeat','measured']}
    save('summary.json',summary);save('case-outcomes.json',list(outputs.values()))
if __name__=='__main__':main()
