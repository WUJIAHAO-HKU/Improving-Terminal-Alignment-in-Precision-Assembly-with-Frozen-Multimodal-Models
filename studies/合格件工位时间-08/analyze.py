"""Paired workstation occupancy for accepted output under complete on-station rework."""
from pathlib import Path
import numpy as np
from timing import D,P,G,read,save,sha
METHODS=('geo','sol6','sol8','sol10')
RGRID=(0,5,15,30,45,60,90,120)
rng=np.random.default_rng(630826)
# Same batch is resampled for every method, cost, and part type.
reps=rng.integers(0,30,(10000,30))
def main():
    timer=read(D/'timing.json');old={r['id']:r for r in read(P/'case-outcomes.json')}
    geo=read(G/'case-outcomes.json');base=read(G/'summary.json')
    assert len(geo)==240
    for filename,digest in read(P/'before-replay.json').items():assert sha(P/filename)==digest
    for line in (G/'before-replay.sha256').read_text().splitlines():
        h,n=line.split();assert sha(G/n)==h
    cases=[]
    for i,v in sorted(geo.items()):
        hist=old[i];times=np.median(timer['raw'][i],axis=0)
        cap=hist['capture'];calls=hist['query_s'];arms={}
        for mode in METHODS:
            k='0' if mode=='geo' else mode[3:];decision=v['decisions'][k];use=decision['measured']
            actual=decision['modes']['cv' if mode=='geo' else 'sol']
            result=v['outcomes'][actual]
            camera=cap['rgb_s']+(cap['rgbd_s'] if use else 0)
            call=0 if mode=='geo' else calls['direct']+(calls['measured'] if use else 0)
            if mode=='geo': local=times[0]
            elif mode=='sol10': local=times[1]+times[5]
            else:local=times[1]+times[2]+times[3 if k=='6' else 4]+use*times[5]
            if mode!='geo':
                a=hist['outcomes']['direct' if actual=='sol_rgb' else 'always']
                assert a['action']==result['action'] and a['success']==result['success']
            arms[mode]=dict(measure=int(use),calls=(0 if mode=='geo' else 1+int(use)),success=int(result['success']),camera=camera,inference=call,local=local,base=camera+call+local)
        cases.append(dict(id=i,batch=v['batch'],task=v['task'],gap=v['gap'],modes=arms))
    for m,k in zip(METHODS,['0','6','8','10']):
        assert sum(q['modes'][m]['success'] for q in cases)==base['budgets'][k]['counts']['cv' if m=='geo' else 'sol']
    save(D/'paired-cases.json',cases)
    groups={};shape_counts={'all':8,'round':3,'square':5}
    for grp,n in shape_counts.items():
        grp_rows=[x for x in cases if grp=='all' or x['task']==grp]
        data={}
        for m in METHODS:
            rec=[r['modes'][m] for r in grp_rows]
            info={k:float(np.mean([a[k] for a in rec])) for k in ('base','inference','local','camera')}
            info.update(n=len(rec),ok=sum(a['success'] for a in rec),measured=sum(a['measure'] for a in rec),
                        calls=sum(a['calls'] for a in rec),f=1-np.mean([a['success'] for a in rec]))
            mat=[]
            for b in range(30):
                rows=[r['modes'][m] for r in grp_rows if r['batch']==b];assert len(rows)==n
                mat.append([np.mean([r['base'] for r in rows]),1-np.mean([r['success'] for r in rows]),np.mean([r['inference'] for r in rows])])
            data[m]=np.array(mat);groups.setdefault(grp,{})[m]=info
        comparisons={}
        for a,b in [(x,y) for j,x in enumerate(METHODS) for y in METHODS[j+1:]]:
            diff=data[b]-data[a];est=diff.mean(0);rep=diff[reps].mean(1);key=a+'_'+b
            br=-est[0]/est[1]/60 if abs(est[1])>1e-10 else None
            comparisons[key]=dict(cross_minutes=br,fewer_fail_resample_pct=float(100*np.mean(rep[:,1]<-1e-10)),grid={})
            for R in RGRID:
                xb=rep[:,0]+R*60*rep[:,1];ci=np.percentile(xb,[2.5,97.5]).tolist()
                comparisons[key]['grid'][str(R)]=dict(delta_s=float(est[0]+R*60*est[1]),ci=ci)
        groups[grp]['comparisons']=comparisons
    summary=dict(groups=groups,sha256={str(p):sha(p) for p in [P/'case-outcomes.json',G/'case-outcomes.json',G/'summary.json',D/'timing.json',D/'paired-cases.json']})
    save(D/'summary.json',summary)
    for grp,z in groups.items():
        print(grp,[(m,z[m]['ok'],round(z[m]['base'],3)) for m in METHODS],[(k,round(v['cross_minutes'],2) if v['cross_minutes'] is not None else None) for k,v in z['comparisons'].items()])
    print('primary',groups['all']['comparisons']['geo_sol8'])
if __name__=='__main__':main()

