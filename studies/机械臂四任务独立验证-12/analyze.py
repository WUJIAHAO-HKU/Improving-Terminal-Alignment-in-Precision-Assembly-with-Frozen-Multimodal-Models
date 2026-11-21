from pathlib import Path
import json,sys
import numpy as np
from scipy.stats import t
D=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf8'))
def main(model):
    rows=read(D/'scenes.json');cs=read(D/(model+'-choices.json'))
    traces=[];results={}
    for r in rows:
        i=r['id'];c=cs[i];y=read(D/'sim'/model/i/'outcomes.json')
        v=dict(id=i,task=r['task'],batch=r['batch'],direct=int(y['first']['ok']),geo=int(y['geometry']['ok']))
        for mod in ['repeat','depth','overhead']:
            for k in [3,4,5]:
                sel=c['rank']<=k;v[f'{mod}_{k}_switch']=int(y[mod if sel else 'first']['ok']);v[f'{mod}_{k}_gate']=int(y[mod if sel and c['accept'][mod] else 'first']['ok'])
                v[f'{mod}_{k}_geo']=int(y[({'overhead':'geometry_top','depth':'geometry_depth','repeat':'geometry'}[mod] if sel else 'geometry')]['ok'])
        traces.append(v)
    groups=sorted({r['batch'] for r in rows})
    for m in ['overhead','repeat','depth']:
        full=f'{m}_5_gate'
        passed=True
        for k in (4,3):
            key=f'{m}_{k}_gate';dd=[np.mean([v[key]-v[full] for v in traces if v['batch']==b]) for b in groups]
            sd=np.std(dd,ddof=1);low=float(np.mean(dd)-t.ppf(.975,len(dd)-1)*sd/np.sqrt(len(dd)));win=bool(sd>0 and low>-.05)
            results[key]=dict(ok=sum(v[key] for v in traces),full=sum(v[full] for v in traces),diff_pp=100*float(np.mean(dd)),lower_pp=100*low,decision=('descriptive' if m!='overhead' or not passed else ('pass' if win else 'not demonstrated')),nonzero_variance=bool(sd>0));passed=passed and win
    (D/(model+'-summary.json')).write_text(json.dumps(dict(n=len(rows),NI=results,totals={k:sum(v[k] for v in traces) for k in traces[0] if k not in ['id','batch','task']},cases=traces),indent=2),encoding='utf8')
if __name__=='__main__':main(sys.argv[1])

