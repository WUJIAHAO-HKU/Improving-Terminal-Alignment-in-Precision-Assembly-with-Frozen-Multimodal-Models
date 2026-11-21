"""Recompute from persistent batch archives, without importing the simulator or the policy."""
import csv
import hashlib
import io
import json
import math
import tarfile
from collections import Counter
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from scipy.stats import t

ROOT=Path(__file__).resolve().parent
DEST=ROOT/'results'
def digest(buf):return hashlib.sha256(buf).hexdigest()
def csvrows(file):
    with (DEST/file).open() as f:return list(csv.DictReader(f))
def outline(r,clearance):
    k,L,rad=r['task'],r['size'],r['radius']
    if k=='blade':
        x=L/2+clearance;y=rad+clearance;return np.array([[-x,-y],[x,-y],[x,y],[-x,y]])
    n=48 if k=='dshaft' else 32
    a=np.arange(n)*2*np.pi/n;u=np.stack((np.cos(a),np.sin(a)),axis=1)
    if k=='dshaft':
        length=np.minimum(L/2+clearance,(.22*L+clearance)/np.maximum(u[:,0],1e-9))
        return u*length[:,None]
    return u*(rad+clearance)
def margin(r,end):
    theta=math.radians(r['ta']);co,si=math.cos(theta),math.sin(theta)
    target=np.array([[co,si],[-si,co]])
    quat=end['part_quat'];rot=Rotation.from_quat(quat[1:]+quat[:1]).as_matrix()[:2,:2]
    cs=([-r['size']/2,r['size']/2] if r['task'] in ('twin','connector') else [0.])
    hole=outline(r,r['gap']);edges=np.roll(hole,-1,axis=0)-hole
    margins=[]
    for c in cs:
        pins=(outline(r,0)+[c,0])@target+[r['tx'],r['ty']]
        rel=(pins-np.array(end['part_mm'][:2]))@rot-[c,0]
        dist=rel[None,:,:]-hole[:,None,:]
        det=edges[:,0,None]*dist[:,:,1]-edges[:,1,None]*dist[:,:,0]
        margins.append(np.min(det/np.hypot(edges[:,0],edges[:,1])[:,None]))
    return min(margins)
def dist(a,b,L,wrap):
    dyaw=a['yaw']-b['yaw']
    if wrap:dyaw=(dyaw+90)%180-90
    return math.dist([a['x'],a['y']],[b['x'],b['y']])+L/2*math.radians(abs(dyaw))
def main():
    totals=Counter();batch_success=Counter();calls=Counter();covered=Counter();checked_pairs=0;attempts=0;flags=Counter();delta_cases=set()
    checkpoints=set();actuals={}
    with tarfile.open(ROOT/'archives/frozen-source.tar.gz') as source:
        get=lambda p:json.load(source.extractfile(p))
        cfg=get('formal/freeze.json');truth=get('formal/scenes.json');gains=get('commissioning/vendor/handoff/gain.json')
        for path,h in cfg['files'].items():assert digest(source.extractfile(path).read())==h,path
        sim_sha=digest(source.extractfile('formal/physics.py').read())
    assert len(truth)==100 and len({r['id'] for r in truth})==100 and Counter(r['task'] for r in truth)==cfg['task_counts']
    signed=[line.split() for line in (ROOT/'archives/batches.sha256').read_text().splitlines()]
    assert len(signed)==20
    for b,(h,name) in enumerate(signed):
        archive=ROOT/'archives'/name;assert digest(archive.read_bytes())==h
        with tarfile.open(archive) as tar:
            members={item.name:tar.extractfile(item).read() for item in tar if item.isfile()}
            def buf(p):return members[Path(p).as_posix()]
            def get(p):return json.loads(buf(p))
            for m in cfg['models']:
                entries=[];ranks_saved=get(f'records/rankings/{m}/{b:02}.json')
                for r in [s for s in truth if s['batch']==b]:
                    i=r['id'];s=Path('records')/i;d=s/m
                    pub=get(s/'public.json');assert pub['scene_id']==i and pub['batch_id']==b
                    assert set(pub)=={'task','gap','size','radius','width','scene_id','batch_id','port','calibration_id'}
                    if r['task']=='connector':assert pub['port']==('near' if r['other_y']>0 else 'far')
                    ck=digest(buf(d/'lift.npz'));assert ck==get(d/'grip.json')['checkpoint_id']
                    checkpoints.add((m,i,ck));grip=get(d/'grasp-trace.json')[-1]
                    lifted=grip['left'] and grip['right'] and grip['part_mm'][2]>25
                    assert lifted==get(d/'grip.json')['lifted'];covered[(m,'lift')]+=lifted
                    stage=get(d/'first-stage.json');post=get(d/'gates.json')
                    outcomes={};fp=stage['first'];tp=post['top']
                    react={}
                    for gate in ('old','new'):
                        ref=dict(post['top_ref'] if post['top_valid'] else stage['eye_ref'])
                        if gate=='new' and r['task']=='dshaft' and post['top_valid']:
                            a=math.radians(ref['yaw'])
                            ref['x']+=.14*r['size']*math.cos(a);ref['y']+=.14*r['size']*math.sin(a)
                        react[gate]='overhead' if dist(tp,ref,r['size'],gate=='new')<dist(fp,ref,r['size'],gate=='new') else 'first'
                        assert react[gate]==post['gates'][gate]['selected']
                    raw=dist(fp,stage['eye_ref'],r['size'],False)/r['gap'] if stage['eye_valid'] else 1e6
                    scores={'old':raw,'new':gains['four_'+m][r['task']]+.0035*min(max(raw,0),10)}
                    for mode in ('grip','first','overhead'):
                        inp=get(d/f'{mode}-input.json')
                        paths=[z['path'] for z in inp['images']]
                        expected=['initial-eye.png']+([] if mode=='grip' else [m+'/live-eye.png'])+(['initial-top.png'] if mode=='overhead' else [])
                        assert paths==expected
                        for z in inp['images']:assert digest(buf(s/z['path']))==z['sha256']
                        at=[n for n in members if n.startswith((d/f'{mode}-cycle-').as_posix()) and '-attempt-' in n and n.endswith('.json')]
                        assert sum(get(n)['error'] is None for n in at)==1
                        attempts+=len(at);calls[m]+=1
                        good=next(get(n) for n in at if get(n)['error'] is None)
                        import re
                        assert json.loads(re.search(r'\{[^{}]+\}',good['raw']).group())==get(d/f'{mode}-reply.json')
                    for branch in ('first','overhead'):
                        receipt=get(d/branch/'receipt.json')
                        assert receipt['checkpoint_id']==ck and receipt['scene_id']==i and receipt['batch_id']==b
                        assert receipt['controller_sha256']==sim_sha and receipt['calibration_sha256']==digest(buf(s/'calibration.json'))
                        assert receipt['input_manifest_sha256']==digest(buf(d/f'{branch}-input.json')) and receipt['reply_sha256']==digest(buf(d/f'{branch}-reply.json'))
                        end=receipt['endpoint'];trace=get(d/branch/'trace.json')
                        carry=sum(t['stage']=='carry' and t['left'] and t['right'] for t in trace)
                        assert carry==receipt['carry_bilateral_samples']
                        rot=Rotation.from_quat(end['part_quat'][1:]+end['part_quat'][:1]).as_matrix()
                        tilt=math.degrees(math.acos(np.clip(rot[2,2],-1,1)))
                        assert math.isclose(tilt,end['tilt_deg'],abs_tol=.00001)
                        real_margin=margin(r,end);assert math.isclose(real_margin,receipt['margin_mm'],abs_tol=1e-8)
                        if lifted:
                            assert trace[-1]['part_mm']==end['part_mm']
                            drift=math.dist(trace[-1]['part_mm'],trace[-4]['part_mm'])
                            assert math.isclose(drift,receipt['drift_mm'],abs_tol=1e-9)
                            ok=(carry>=8 and all(pad not in end['contacts'] for pad in ('left_finger_pad','right_finger_pad')) and 6.6<end['part_mm'][2]<7.5 and tilt<3 and real_margin>=-.15 and drift<.35)
                        else:ok=False
                        assert bool(ok)==receipt['success'];outcomes[branch]=bool(ok)
                        covered[(m,branch)]+=ok
                        for f in ('final.npz','final-top.png','final-eye.png'):assert len(buf(d/branch/f))>0
                    entries.append((i,scores,react,outcomes,r['task']))
                    checked_pairs+=1
                assert len(entries)==5
                for q in (3,4,5):
                    sel_map={}
                    for alloc in ('old','new'):
                        ids=sorted(entries,key=lambda e:(-e[1][alloc],e[0]))
                        for rank,(i,sc,react,y,task) in enumerate(ids,1):
                            saved=ranks_saved[f'{alloc}-{q}'][i]
                            assert rank==saved['rank'] and (rank<=q)==saved['measure'] and math.isclose(saved['score'],sc[alloc],abs_tol=1e-10)
                            for gate in ('old','new'):
                                if q==5 and (gate!='new' or alloc!='new'):continue
                                pick=react[gate] if rank<=q else 'first';ok=y[pick]
                                arm=(m,20*q,alloc,gate)
                                totals[arm]+=ok;batch_success[arm,b]+=ok
                                sel_map[i,alloc,gate]=int(ok)
                                actuals[m,i,q,alloc,gate]=(int(rank<=q),rank,pick,int(ok))
                                flags[arm,'dshaft']+=int(task=='dshaft' and rank<=q and not y['first'] and y['overhead'] and pick=='first')
                                flags[arm,'blade']+=int(task=='blade' and rank>q and not y['first'] and y['overhead'] and react[gate]=='overhead')
                    if q!=5:
                        for i,*_ in entries:
                            change=sel_map[i,'new','new']-sel_map[i,'old','old']
                            if change:delta_cases.add((m,20*q,i,change))
    assert checked_pairs==200 and len(checkpoints)==200
    for r in csvrows('decisions.csv'):
        assert actuals[r['model'],r['scene'],int(r['quota']),r['allocation'],r['gate']]==(int(r['measured']),int(r['rank']),r['branch'],int(r['success']))
    for r in csvrows('equal-budget.csv'):
        k=(r['model'],int(r['measured']),r['allocation'],r['acceptance']);assert totals[k]==int(r['seated']) and covered[r['model'],'lift']==int(r['lifted'])
    for r in csvrows('mechanisms.csv'):
        k=(r['model'],int(r['measured']),r['allocation'],r['acceptance']);assert flags[k,'blade']==int(r['blade_missed_rescue']) and flags[k,'dshaft']==int(r['dshaft_false_reject'])
    assert delta_cases=={(r['model'],int(r['measured']),r['scene'],1 if r['change']=='rescued' else -1) for r in csvrows('changed-cases.csv')}
    tested={}
    for r in csvrows('noninferiority.csv'):
        m=r['model'];q=100-int(r['saving_pct'])
        dif=np.array([(batch_success[(m,q,'new','new'),b]-batch_success[(m,100,'new','new'),b])/5 for b in range(20)])
        bound=100*(dif.mean()-t.isf(.025,19)*np.sqrt(np.var(dif,ddof=1)/20))
        assert abs(bound-float(r['lower_97_5_pp']))<.00001
        ok=bool(np.ptp(dif)>0 and bound> -5)
        interpretation='descriptive only' if q==60 and not tested[m,80] else 'inconclusive (zero variance)' if np.ptp(dif)==0 else 'pass' if ok else 'did not pass'
        tested[m,q]=ok;assert interpretation==r['status']
    audit=dict(archive_batches=20,scenes=100,model_grasps=checked_pairs,physical_branch_labels=2*checked_pairs,
               model_policy_decisions=len(actuals),logical_model_calls=dict(calls),actual_model_attempts=attempts,
               checked='Frozen hashes, input image identity, raw response parsing, common checkpoints, contact/released pose and CAD containment, ranks, gates, changes of outcome, batch-paired limits and sequential claims.')
    (DEST/'independent-audit.json').write_text(json.dumps(audit,indent=2))
    print(audit)
if __name__=='__main__':main()
