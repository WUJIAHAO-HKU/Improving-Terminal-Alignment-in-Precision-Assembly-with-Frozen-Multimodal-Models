"""Replay the archived policy choices; report prespecified estimands on all started scenes."""
from collections import Counter,defaultdict
from pathlib import Path
import csv,json,sys
import numpy as np
from scipy.stats import t
ROOT=Path(__file__).resolve().parent
REC=ROOT/'records'; OUT=ROOT/'results'
MODELS=('gpt-6.2-sol','gpt-6.1-terra')
TASKS=('twin','blade','dshaft','connector')
def read(p):return json.loads(p.read_text())
def write_csv(name,rows):
    with (OUT/name).open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def labels(m):return 'Sol' if m==MODELS[0] else 'Terra'

def main():
    OUT.mkdir(exist_ok=True)
    scenes=read(ROOT/'scenes.json');assert len(scenes)==100
    all_rows=[]; arm_rows=[]; ni_rows=[]; by_task=[];cases=[];mechanisms=[];ledger=[];data=[]
    for m in MODELS:
        units=[{} for _ in range(20)]
        for s in scenes:
            i=s['id'];d=REC/i/m;g=read(d/'grip.json')
            outcomes={branch:read(d/branch/'receipt.json') for branch in ('first','overhead')}
            assert all(v['checkpoint_id']==g['checkpoint_id'] for v in outcomes.values())
            y={b:bool(record['success']) for b,record in outcomes.items()}
            gates=read(d/'gates.json');ranks=read(REC/'rankings'/m/f"{s['batch']:02}.json")
            actual=Counter()
            for mode in ('grip','first','overhead'):
                a=list(d.glob(f'{mode}-cycle-*-attempt-*.json'))
                assert len([f for f in a if read(f)['error'] is None])==1
                actual[mode]=len(a)
            data.append(dict(model=m,scene=i,batch=s['batch'],task=s['task'],lifted=int(g['lifted']),first=int(y['first']),overhead=int(y['overhead']),
                             top_valid=int(gates['top_valid']),eye_valid=int(read(d/'first-stage.json')['eye_valid']),attempts=sum(actual.values())))
            for q in (3,4,5):
                for alloc,gate in ([('new','new')] if q==5 else [('old','old'),('new','old'),('old','new'),('new','new')]):
                    k=(q,alloc,gate)
                    rank=ranks[f'{alloc}-{q}'][i];meas=rank['measure'];selected=gates['gates'][gate]['selected'] if meas else 'first'
                    unit=dict(model=m,batch=s['batch'],scene=i,task=s['task'],quota=q,allocation=alloc,gate=gate,rank=rank['rank'],
                        measured=int(meas),branch=selected,first=int(y['first']),overhead=int(y['overhead']),success=int(y[selected]),lifted=int(g['lifted']),
                        checkpoint_id=g['checkpoint_id'],failure_stage=outcomes[selected]['failure_stage'] or '',
                        dshaft_false_reject=int(s['task']=='dshaft' and meas and not y['first'] and y['overhead'] and selected=='first'),
                        blade_missed_rescue=int(s['task']=='blade' and not meas and not y['first'] and y['overhead'] and gates['gates'][gate]['selected']=='overhead'))
                    all_rows.append(unit);units[s['batch']].setdefault(k,[]).append(unit)
        per_model=[u for u in data if u['model']==m]
        lifts=sum(u['lifted'] for u in per_model)
        full=np.array([sum(u['success'] for u in block[(5,'new','new')]) for block in units])
        lastpass=True
        for q in (5,4,3):
            for alloc,gate in ([('new','new')] if q==5 else [('old','old'),('new','old'),('old','new'),('new','new')]):
                k=(q,alloc,gate)
                rows=[u for block in units for u in block[k]]
                n=sum(u['success'] for u in rows);meas=sum(u['measured'] for u in rows)
                assert len(rows)==100 and meas==q*20
                arm_rows.append(dict(model=m,measured=meas,allocation=alloc,acceptance=gate,seated=n,started=100,lifted=lifts,seated_per_lift_pct=round(100*n/lifts,3) if lifts else None))
                for task in TASKS:
                    subset=[u for u in rows if u['task']==task]
                    assert len(subset)==25
                    by_task.append(dict(model=m,measured=meas,allocation=alloc,acceptance=gate,task=task,started=25,seated=sum(u['success'] for u in subset)))
                mechanisms.append(dict(model=m,measured=meas,allocation=alloc,acceptance=gate,dshaft_false_reject=sum(u['dshaft_false_reject'] for u in rows),
                                       blade_missed_rescue=sum(u['blade_missed_rescue'] for u in rows)))
                deployed_first=lifts; deployed_optional=sum(u['measured']*u['lifted'] for u in rows)
                ledger.append(dict(model=m,policy=f'{alloc}x{gate}',measurements=meas,planned_grip=100,planned_first=100,planned_optional=meas,
                    deployed_grip=100,deployed_first=deployed_first,deployed_optional=deployed_optional,
                    shadow_first_on_failed_grasps=100-deployed_first,selected_on_failed_grasps=meas-deployed_optional,
                    offline_grip=100,offline_first=100,offline_optional=100,offline_attempts=sum(u['attempts'] for u in per_model)))
            if q==5:continue
            old={r['scene']:r for block in units for r in block[(q,'old','old')]}
            new={r['scene']:r for block in units for r in block[(q,'new','new')]}
            for i in sorted(old):
                a,b=old[i],new[i]
                if a['success']!=b['success']:
                    cases.append(dict(model=m,measured=q*20,scene=i,task=a['task'],change='rescued' if b['success'] else 'new failure',
                        first=a['first'],overhead=a['overhead'],old_measured=a['measured'],new_measured=b['measured'],old_selected=a['branch'],new_selected=b['branch'],
                        checkpoint_id=a['checkpoint_id']))
            counts=np.array([sum(u['success'] for u in block[(q,'new','new')]) for block in units])
            dif=(counts-full)*20. # percentage points; denominator five per batch
            lower=dif.mean()-t.ppf(.975,19)*dif.std(ddof=1)/np.sqrt(20)
            variance=bool(np.ptp(dif)>0)
            passed=bool(variance and lower> -5.)
            status=('descriptive only' if not lastpass else 'pass' if passed else 'inconclusive (zero variance)' if not variance else 'did not pass')
            ni_rows.append(dict(model=m,saving_pct=100-q*20,budget_success=int(counts.sum()),full_success=int(full.sum()),difference_pp=round(float(dif.mean()),5),lower_97_5_pp=round(float(lower),5),nonzero_variance=variance,status=status,batch_differences_pp=' '.join(str(int(x)) for x in dif)))
            lastpass=lastpass and passed
    for name,rows in [('decisions.csv',all_rows),('equal-budget.csv',arm_rows),('noninferiority.csv',ni_rows),('per-task.csv',by_task),('mechanisms.csv',mechanisms),('calls.csv',ledger),('paired-outcomes.csv',data)]:
        write_csv(name,rows)
    if cases:write_csv('changed-cases.csv',cases)
    else:(OUT/'changed-cases.csv').write_text('model,measured,scene,task,change\n')
    return arm_rows,ni_rows,data,cases,mechanisms

if __name__=='__main__':
    _,ni,_,_,_=main()
    print(json.dumps(ni,indent=2))
