"""Analyze paired quality, same-budget manufacturing rules, and serial workstation scenarios."""
from pathlib import Path
import numpy as np
from scipy.stats import t
from rules4 import D,read,save,sha

METHODS=['full','random','gap','strat','abrank','abboth','stream_natural','stream_first','stream_last','strong','strong_ab','direct']
COSTS=[0,30,120,300,600,1800,3600]
def stats(diffs):
    x=np.asarray(diffs,dtype=float)*100;mu=float(x.mean());se=float(x.std(ddof=1)/np.sqrt(len(x)))
    q=t.ppf(.975,len(x)-1);lower=mu-t.ppf(.95,len(x)-1)*se
    return dict(diff=mu,ci=[float(mu-q*se),float(mu+q*se)],lower=float(lower),ni_p=float(t.sf((mu+5)/se,len(x)-1)) if se else None,
                p=float(t.sf(mu/se,len(x)-1)) if se else 1.,meets=bool(se and lower>-5))
def metrics(x):
    return dict(mean=float(np.mean(x)),median=float(np.median(x)),p90=float(np.quantile(x,.90)))
def queue(records,method,spacing,r):
    clock=0.;wait=[];flow=[];busy=0.;index=0
    for group in records:
        batch=(method not in ['strong','strong_ab','direct'] and not method.startswith('stream'))
        starts={};ends={}
        for row in group:
            arrival=index*spacing;index+=1
            clock=max(arrival,clock);starts[row['id']]=clock
            clock+=row['front'];busy+=row['front']
            if not batch:
                duration=row['back']+r*(not row['ok']);clock+=duration;busy+=duration
                ends[row['id']]=clock
        if batch:
            for row in group:
                duration=row['back']+r*(not row['ok']);clock+=duration;busy+=duration
                ends[row['id']]=clock
        for j,row in enumerate(group):
            arrival=(index-len(group)+j)*spacing
            service=row['front']+row['back']+r*(not row['ok'])
            flow.append(ends[row['id']]-arrival)
            wait.append(max(0.,ends[row['id']]-arrival-service))
    return dict(busy_per100=busy/3,elapsed_per100=clock/3,wait=float(np.mean(wait)),flow=float(np.mean(flow)))
def main():
    for n,h in read(D/'before-replay.json').items():assert sha(D/n)==h
    decisions=read(D/'decisions.json');rows={r['id']:r for r in read(D/'manifest.json')};acts=read(D/'actions.json')
    resp=[read(p) for p in (D/'responses').glob('*.json')]
    assert len(resp)==len({(r['id'],r['mode']) for r in resp})==600
    tm={(r['id'],r['mode']):r['seconds'] for r in resp}
    for r in resp:
        assert r['action']==acts[r['id']]['always' if r['mode']=='measured' else 'direct'] and r['model']=='gpt-6.2-sol'
        assert ('Additional rendered RGB-D measurement' in r['prompt'])==(r['mode']=='measured')
    caps={r['id']:r for r in read(D/'capture-times.json')}
    raw=read(D/'scores.json');sc={(r['id'],r['mode']):r for r in raw};assert len(raw)==len(sc)==900
    for i,row in rows.items():
        row.update(decisions['items'][i]);row['capture']=caps[i];row['query_s']={m:tm[i,m] for m in ['direct','measured']}
        row['outcomes']={m:dict(sc[i,m],action=acts[i][m]) for m in ['direct','always','oracle']}
    speeds={k:metrics(v) for k,v in dict(rgb=[x['rgb_s'] for x in caps.values()],rgbd=[x['rgbd_s'] for x in caps.values()],
        direct_call=[tm[i,'direct'] for i in rows],measurement_call=[tm[i,'measured'] for i in rows],
        execution=[x['replay_s'] for x in raw if x['mode']!='oracle']).items()}
    summary=dict(timing=speeds,oracle=sum(sc[i,'oracle']['success'] for i in rows),calls_with_retries=sum(x['attempts']>1 for x in resp),budgets={})
    save('case-outcomes.json',list(rows.values()))
    allowed=True
    for k in [8,6]:
        allgroups={m:[] for m in METHODS};square={};perbatch={m:[] for m in METHODS};expect={'random_expected':[],'strat_expected':[]}
        summary['budgets'][str(k)]=b={};station={}
        for batch in decisions['batches']:
            ids=batch['orders']['natural'];sel=batch['selections'][str(k)]
            for method in METHODS:
                chosen=set(ids if method.startswith('strong') else [] if method=='direct' else sel[method])
                order=batch['orders'][method.split('_')[1]] if method.startswith('stream') else ids
                best=[]
                for i in order:
                    row=rows[i];use=i in chosen
                    gate=row['bothaccept'] if method in ['abboth','strong_ab'] else row['accept']
                    mode='always' if use and gate else 'direct'
                    ok=sc[i,mode]['success'];other='direct' if mode=='always' else 'always'
                    front=tm[i,'direct']+caps[i]['rgb_s'];extra=(tm[i,'measured']+caps[i]['rgbd_s']) if use else 0.
                    best.append(dict(id=i,task=row['task'],gap=row['gap'],use=use,ok=ok,mode=mode,
                                     alternate=bool(sc[i,other]['success']),front=front,back=extra+sc[i,mode]['replay_s']))
                allgroups[method].append(best);perbatch[method].append(np.mean([r['ok'] for r in best]))
            for method,baseline in [('random_expected','random'),('strat_expected','strat')]:
                chosen=sel[baseline]
                ev=0.
                for i in ids:
                    row=rows[i];prob=k/10 if baseline=='random' else sum(rows[j]['task']==row['task'] for j in chosen)/sum(rows[j]['task']==row['task'] for j in ids)
                    dn=int(sc[i,'direct']['success']);g=int(sc[i,'always' if row['accept'] else 'direct']['success'])
                    ev+=dn+prob*(g-dn)
                expect[method].append(ev/10)
        for method,groups in allgroups.items():
            rec=[r for grp in groups for r in grp];ok=sum(r['ok'] for r in rec);n=len(rec)
            base_time=sum(r['front']+r['back'] for r in rec);fails=n-ok
            sq=[r for r in rec if r['task']=='square']
            part={}
            for g in [4,2,1,.5,.25]:
                cells=[r for r in sq if r['gap']==g];part[str(g)]=dict(n=len(cells),ok=sum(r['ok'] for r in cells),measured=sum(r['use'] for r in cells))
            fullmode=lambda i:'always' if rows[i]['accept'] else 'direct'
            b[method]=dict(ok=ok,measured=sum(r['use'] for r in rec),busy0=base_time,fail=fails,square=sum(r['ok'] for r in sq),
                square_measured=sum(r['use'] for r in sq),sq_by_gap=part,
                square_missed=[r['id'] for r in sq if not r['use'] and not r['ok'] and sc[r['id'],fullmode(r['id'])]['success']],
                square_saved=[r['id'] for r in sq if not r['use'] and r['ok'] and not sc[r['id'],fullmode(r['id'])]['success']],
                alternate_rescues=sum(not r['ok'] and r['alternate'] for r in rec),
                vs_strong=stats(np.array(perbatch[method])-perbatch['strong']))
            station[method]={str(cost):{str(sp):queue(groups,method,sp,cost) for sp in (0,30,90)} for cost in COSTS}
        for m,v in expect.items(): b[m]=dict(expected_ok=float(sum(v)*10))
        of=np.array(perbatch['full'])
        comparisons={m:stats(of-(perbatch|expect)[m]) for m in ['random_expected','strat_expected','gap','abrank']}
        prev=0.
        for j,m in enumerate(sorted(comparisons,key=lambda m:comparisons[m]['p'])):
            prev=max(prev,min(1.,(4-j)*comparisons[m]['p']));comparisons[m]['holm']=prev
        b['comparisons']=comparisons
        b['stream_natural']['status']='通过' if allowed and b['stream_natural']['vs_strong']['meets'] else '未通过' if allowed else '仅描述'
        allowed=allowed and b['stream_natural']['vs_strong']['meets']
        for method in METHODS:
            delta=b[method]['fail']-b['strong']['fail'];saved=b['strong']['busy0']-b[method]['busy0']
            b[method]['extra_fail']=delta;b[method]['saved_base_s']=saved;b[method]['break_even_s']=saved/delta if delta else None
            group_delta_t=np.array([sum(r['front']+r['back'] for r in g) for g in allgroups['strong']])-np.array([sum(r['front']+r['back'] for r in g) for g in allgroups[method]])
            group_delta_f=(np.array(perbatch['strong'])-np.array(perbatch[method]))*10
            savings={}
            for cost in COSTS:
                y=(group_delta_t-cost*group_delta_f)*10/60 # minutes saved per 100 qualified pieces
                spread=t.ppf(.975,29)*y.std(ddof=1)/np.sqrt(30)
                savings[str(cost)]=[float(y.mean()),float(y.mean()-spread),float(y.mean()+spread)]
            b[method]['saving_min100']=savings
        b['station']=station
    save('summary.json',summary)
    # first square under each relevant failure pattern in the independent K=6 stream.
    use={i for b in decisions['batches'] for i in b['selections']['6']['stream_natural']};items=[]
    for tag,pred in [('流式漏测',lambda i,d,m:i not in use and rows[i]['accept'] and not d and m),
        ('误拒修正',lambda i,d,m:i in use and not rows[i]['accept'] and not d and m),
        ('两动作均失败',lambda i,d,m:not d and not m)]:
        key=next((i for i in sorted(rows) if rows[i]['task']=='square' and pred(i,sc[i,'direct']['success'],sc[i,'always']['success'])),None)
        if key:
            for mode in ('direct','always'):
                items.append(dict(id=key,task='square',gap=rows[key]['gap'],category=tag,mode=mode,action=acts[key][mode]))
    save('to_capture.json',items)
if __name__=='__main__':main()
