from pathlib import Path
import numpy as np,json
from scipy.stats import t
D=Path(__file__).resolve().parent
M=['gpt-6.2-sol','gpt-6.1-terra']
def rd(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def ni(rows,a,b):
    blocks=sorted({r['batch'] for r in rows})
    delta=np.array([np.mean([int(x[a])-int(x[b]) for x in rows if x['batch']==j]) for j in blocks]);sd=delta.std(ddof=1)
    lo=(delta.mean()-t.ppf(.975,len(blocks)-1)*sd/np.sqrt(len(blocks)))*100
    return dict(diff_pp=100*delta.mean(),lower_pp=lo,positive_variance=bool(sd>1e-12),pass_margin=bool(sd>1e-12 and lo>-5))
def analyze(k,m):
    p=D/k;kit=k=='kits';rows=[];rr=rd(p/'scenes.json');ch=rd(p/(m+'-choices.json'))
    for r in rr:
        i=r['id'];c=ch[i];y=rd(p/('runs' if kit else 'sim')/m/i/('results.json' if kit else 'outcomes.json'));field='complete' if kit else 'ok';a=int(y['first'][field]);b=int(y['overhead'][field]);z=dict(id=i,batch=r['batch'],family=r['recipe'] if kit else r['task'],category=c['cat'],first=a,top=b,**{q:c[q] for q in ('old_rank','new_rank','old_accept','new_accept')})
        for al in ['old','new']:
            for g in ['old','new','switch']:
                for j in (3,4,5):
                    z[f'{al}_{g}_{j}']=b if c[al+'_rank']<=j and (g=='switch' or c[g+'_accept']) else a
        rows.append(z)
    totals={x:sum(int(r[x]) for r in rows) for x in ['first','top',*[f'{a}_{g}_{j}' for a in ('old','new') for g in ('old','new','switch') for j in (3,4,5)]]}
    ni80=ni(rows,'new_new_4','new_new_5');ni60=ni(rows,'new_new_3','new_new_5');ni80['formal']=True;ni60['formal']=ni80['pass_margin']
    return dict(totals=totals,primary=[ni80,ni60],rows=rows)
def franka(kind='franka'):
    out=[]
    for m in M:
        for k in range(5):
            p=D/kind/'runs'/(m+'-'+str(k));events=[rd(x) for x in sorted(p.glob('out-*.json'))];end=rd(p/'endpoints.json');replay=rd(p/'video-check.json');assert len(events)==len(end)+2 and replay==[v['ok'] for v in events]
            bolts=[v for v in events if 'bolt' in v]
            out.append(dict(model=m,task=k,nparts=len(end),carried=sum(bool(len(x['lift_contact'])==len(x['carry_contact'])==2 and x['transport_mm']>35) for x in events[:-2]),placed=sum(x['ok'] for x in events[:-2]),final_seated=sum(x['seated'] for x in end),tightened=sum(x['ok'] for x in bolts),complete=all(x['ok'] for x in events) and all(x['seated'] for x in end),bolts=[dict(bolt=v['bolt'],ever_engaged=v['engaged'],stop=v['stop'],**v['trace'][-1]) for v in bolts]))
    return out
if __name__=='__main__':
    results={s:{m:analyze(s,m) for m in M} for s in ['four','kits']};results['franka']=franka();results['registered']=franka('franka-registered')
    (D/'independent-results.json').write_text(json.dumps(results,indent=2),encoding='utf8')


