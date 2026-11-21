import numpy as np
from scipy.stats import t
from pipeline import D,P,read,save,sha
def main():
    hashes=(D/'before-replay.sha256').read_text().splitlines()
    for line in hashes:
        h,n=line.split();assert sha(D/n)==h
    for n,h in read(D/'lock.json')['hashes'].items():
        from pathlib import Path
        assert sha(Path(n))==h
    obs={r['id']:r for r in read(P/'manifest.json')}
    pred=read(D/'test-predictions.json');actions=read(D/'actions.json');dec=read(P/'decisions.json')
    old={(r['id'],r['mode']):r for r in read(P/'scores.json')}
    raw=read(D/'scores.json');sc={(r['id'],r['mode']):r for r in raw}
    ids=sorted(pred);assert len(raw)==len(sc)==1680 and len(ids)==240
    for i in ids:
        for m,m0 in [('sol_rgb','direct'),('sol_rgbd','always'),('oracle','oracle')]:
            assert all(sc[i,m][k]==old[i,m0][k] for k in ['success','height','lateral','tilt','stable','official'])
    out={i:dict(task=obs[i]['task'],gap=obs[i]['gap'],angle=obs[i]['angle'],batch=obs[i]['batch'],localization=pred[i],
        outcomes={m:dict(sc[i,m],action=a) for m,a in actions[i].items()},decisions={}) for i in ids}
    budgets={};Y=lambda i,m:int(sc[i,m]['success'])
    for k in [0,6,8,10]:
        use=set(ids) if k==10 else set() if k==0 else {i for b in dec['batches'] for i in b['selections'][str(k)]['stream_natural']}&set(ids)
        cols={'cv':[],'cv_raw':[],'sol':[],'sol_switch':[],'oracle':[]};errors={'cv':[],'sol':[]}
        for i in ids:
            sensor='rgbd' if i in use else 'rgb'
            gm='sol_rgbd' if i in use and dec['items'][i]['accept'] else 'sol_rgb'
            modes=dict(cv=sensor,cv_raw=sensor+'_raw',sol=gm,sol_switch='sol_'+sensor,oracle='oracle')
            for name,m in modes.items():
                cols[name].append(Y(i,m))
                if name in errors:
                    errors[name].append(float(np.linalg.norm(np.array(actions[i][m])+[obs[i]['x'],obs[i]['y']])))
            out[i]['decisions'][str(k)]=dict(measured=i in use,modes=modes,geometric_error=errors['cv'][-1],sol_error=errors['sol'][-1])
        a=np.array(cols['cv']);b=np.array(cols['sol'])
        diff=(a-b).reshape(30,8).mean(1)*100;mu=diff.mean();spread=t.ppf(.975,29)*diff.std(ddof=1)/np.sqrt(30)
        sub={}
        for key,mask in [(v,[obs[i]['task']==v for i in ids]) for v in ['square','round']]+[(f'gap{g}',[obs[i]['gap']==g for i in ids]) for g in [4,2,1,.5,.25]]+[(f'angle{ang}',[obs[i]['angle']==ang for i in ids]) for ang in sorted({obs[i]['angle'] for i in ids})]:
            mask=np.asarray(mask)
            sub[key]=dict(n=int(mask.sum()),cv=int(a[mask].sum()),sol=int(b[mask].sum()),measured=sum(i in use for i,z in zip(ids,mask) if z))
        budgets[str(k)]=dict(measured=len(use),counts={m:sum(v) for m,v in cols.items()},diff=float(mu),ci=[float(mu-spread),float(mu+spread)],
            win=int((a>b).sum()),loss=int((a<b).sum()),subset=sub,errors={m:dict(median=float(np.median(v)),p90=float(np.quantile(v,.9))) for m,v in errors.items()},
            localized=sum(bool(pred[i]['rgbd' if i in use else 'rgb']['localized']) for i in ids))
    cases={}
    for n,ca,sa in [('geometry_only',1,0),('sol_only',0,1),('both_fail',0,0),('both_succeed',1,1)]:
        for i in ids:
            v=out[i]['decisions']['8']['modes']
            if (Y(i,v['cv']),Y(i,v['sol']))==(ca,sa):cases[n]=i;break
    save(D/'case-outcomes.json',out);save(D/'summary.json',dict(budgets=budgets,examples=cases))
if __name__=='__main__':main()
