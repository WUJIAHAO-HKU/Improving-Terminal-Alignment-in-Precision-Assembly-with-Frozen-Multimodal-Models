from pathlib import Path
import json,collections
import numpy as np
from scipy.stats import t
D=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def run(model):
    rows=read(D/'scenes.json');ch=read(D/(model+'-choices.json'));out=[]
    for r in rows:
        i=r['id'];c=ch[i];v=read(D/'runs'/model/i/'results.json')
        keys=['first','geometry','repeat','depth','overhead','geometry_depth','geometry_top'];assert set(v)==set(keys)
        a=dict(id=i,recipe=r['recipe'],batch=r['batch'],direct=v['first']['complete'],geo=v['geometry']['complete'])
        for mode in ['repeat','depth','overhead']:
            for k in [3,4,5]:
                sel=c['rank']<=k;use=mode if sel else 'first'
                a[f'{mode}_{k}_switch']=v[use]['complete'];a[f'{mode}_{k}_gate']=v[use if c['accept'][mode] else 'first']['complete']
                g={'repeat':'geometry','depth':'geometry_depth','overhead':'geometry_top'}[mode];a[f'{mode}_{k}_geo']=v[g if sel else 'geometry']['complete']
        out.append(a)
    totals={k:sum(r[k] for r in out) for k in out[0] if k not in ['id','recipe','batch']}
    ni={}
    for m in ('overhead','depth','repeat'):
        passed=True
        for k in [4,3]:
            a=f'{m}_{k}_gate';full=f'{m}_5_gate'
            dif=np.array([np.mean([int(v[a])-int(v[full]) for v in out if v['batch']==b]) for b in range(20)]);sd=dif.std(ddof=1);low=dif.mean()-t.ppf(.975,19)*sd/np.sqrt(20)
            hit=bool(sd>0 and low>-.05)
            ni[a]=dict(diff=100*dif.mean(),lower=100*low,decision='descriptive' if m!='overhead' or not passed else 'pass' if hit else 'not demonstrated')
            passed=passed and hit
    summary=dict(totals=totals,paired=ni,rows=out)
    (D/(model+'-summary.json')).write_text(json.dumps(summary,indent=2),encoding='utf8')
if __name__=='__main__':
    import sys
    run(sys.argv[1])

