"""Independently validate 64 batches of raw evidence, including geometry, image hashes and policy inputs."""
import argparse,sys,hashlib,tarfile,json,re,io,math
from pathlib import Path
from collections import Counter
import numpy as np
from scipy.spatial.transform import Rotation
from audit_geometry import margin,dist

def verify(src,raw):
    root=src/'formal';cfg=json.loads((root/'lock.json').read_text())
    def sha(v):return hashlib.sha256(v).hexdigest()
    for p,h in cfg['files'].items():assert sha((src/p).read_bytes())==h,p
    truth=json.loads((root/'scenes.json').read_text())
    assert len(truth)==320 and len({r['id'] for r in truth})==320 and Counter(r['task'] for r in truth)==cfg['tasks']
    gains=json.loads((src/'commissioning/vendor/handoff/gain.json').read_text())
    counts=Counter()
    for b in range(64):
        with tarfile.open(raw/f'batch-{b:02}.tgz') as t:
            payload={x.name.removeprefix('./'):t.extractfile(x).read() for x in t if x.isfile()}
        get=lambda p:json.loads(payload[p])
        for m in cfg['models']:
            sc={}
            for row in truth[b*5:b*5+5]:
                i=row['id']; assert b==row['batch']
                pub=get(i+'/public.json');assert pub['scene_id']==i and pub['port']==row['port']
                p=f'{i}/{m}/'; stage=get(p+'first-stage.json');post=get(p+'gates.json')
                assert stage['scene_id']==i
                ck=sha(payload[p+'lift.npz']);grip=get(p+'grip.json');assert ck==grip['checkpoint_id']
                lift=get(p+'grasp-trace.json')[-1];lifted=lift['left'] and lift['right'] and lift['part_mm'][2]>25;assert lifted==grip['lifted']
                for mode in ('grip','first','overhead'):
                    inp=get(p+mode+'-input.json')
                    paths=['initial-eye.png']+([] if mode=='grip' else [m+'/live-eye.png'])+(['initial-top.png'] if mode=='overhead' else [])
                    assert inp['model']==m and inp['effort']=='medium' and [z['path'] for z in inp['images']]==paths
                    for z in inp['images']:assert sha(payload[i+'/'+z['path']])==z['sha256']
                    attempts=[get(k) for k in payload if k.startswith(p+mode+'-cycle-') and '-attempt-' in k]
                    good=[a for a in attempts if a['error'] is None];assert len(good)==1
                    assert json.loads(re.search(r'\{[^{}]+\}',good[0]['raw']).group())==get(p+mode+'-reply.json')
                    counts['logical_calls']+=1;counts['attempts']+=len(attempts)
                for br in ('first','overhead'):
                    r=get(p+br+'/receipt.json');assert r['checkpoint_id']==ck and r['scene_id']==i and r['batch_id']==b and r['model']==m
                    assert r['controller_sha256']==cfg['files']['formal/physics.py'] and r['calibration_sha256']==sha(payload[i+'/calibration.json'])
                    for k in ('input','reply'):assert sha(payload[p+br+'-'+k+'.json'])==r[('input_manifest' if k=='input' else 'reply')+'_sha256']
                    e=r['endpoint'];trace=get(p+br+'/trace.json');carry=sum(z['stage']=='carry' and z['left'] and z['right'] for z in trace)
                    assert r['carry_bilateral_samples']==carry
                    mar=margin(row,e);assert abs(mar-r['margin_mm'])<1e-7
                    tilt=math.degrees(math.acos(np.clip(Rotation.from_quat(e['part_quat'][1:]+e['part_quat'][:1]).as_matrix()[2,2],-1,1)))
                    assert math.isclose(tilt,e['tilt_deg'],abs_tol=1e-5)
                    if lifted:
                        assert trace[-1]['part_mm']==e['part_mm']
                        drift=math.dist(trace[-1]['part_mm'],trace[-4]['part_mm'])
                        assert math.isclose(drift,r['drift_mm'],abs_tol=1e-9)
                        ok=(carry>=8 and not any(pad in e['contacts'] for pad in ('left_finger_pad','right_finger_pad')) and 6.6<e['part_mm'][2]<7.5 and mar>=-.15 and tilt<3 and drift<.35)
                    else:ok=False
                    assert bool(ok)==r['success']
                    for k in ('final.npz','final-eye.png','final-top.png'):assert payload[p+br+'/'+k]
                    counts['physical_endpoints']+=1
                ref=dict(post['top_ref'] if post['top_valid'] else stage['eye_ref'])
                if pub['task']=='dshaft' and post['top_valid']:
                    theta=math.radians(ref['yaw']);ref['x']+=.14*pub['size']*math.cos(theta);ref['y']+=.14*pub['size']*math.sin(theta)
                pick='overhead' if dist(post['top'],ref,pub['size'],True)<dist(stage['first'],ref,pub['size'],True) else 'first'
                assert pick==post['gates']['new']['selected']
                dev=dist(stage['first'],stage['eye_ref'],pub['size'],False)/pub['gap'] if stage['eye_valid'] else 1e6
                sc[i]=gains['four_'+m][pub['task']]+.035*min(max(dev,0),10)/10
            rank=get(f'rankings/{m}/{b:02}.json')
            assert set(rank['lists']['combined'])==set(sorted(sc,key=lambda i:(-sc[i],i))[:4])
    assert counts['logical_calls']==1920 and counts['physical_endpoints']==1280
    print(json.dumps(counts,indent=2))
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('source',type=Path);ap.add_argument('archives',type=Path)
    args=ap.parse_args();verify(args.source,args.archives)
