from pathlib import Path
import concurrent.futures,sys,json,hashlib,os,time
import cv2,numpy as np
from geometry import estimate
D=Path(__file__).resolve().parent;P=D.parent/'工位补充实验-05';DEV=D.parent/'风险感知动作接受实验-03'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def infer(job):
    folder,id,task,gap,angle,depth,dz=job
    img=cv2.imdecode(np.fromfile(folder/'frames'/(id+'.jpg'),dtype=np.uint8),cv2.IMREAD_COLOR)
    assert img is not None
    t=time.perf_counter();out=estimate(img,task,gap,angle,depth,dz);out['seconds']=time.perf_counter()-t
    return id,out
def main():
    mode=sys.argv[1]
    dev=read(DEV/'manifest.json')
    dz_by={task:float(np.median([r['height']+10 for r in dev if r['task']==task])) for task in ['square','round']}
    if mode=='lock':
        predictions=read(D/'calibrate-predictions.json')
        calibration={}
        for task in dz_by:
            for sensor in ['rgb','rgbd']:
                data=[r for r in dev if r['task']==task and predictions[r['id']][sensor]['localized']]
                residual=np.array([np.array(predictions[r['id']][sensor]['action'])+[r['x'],r['y']] for r in data])
                slope=np.tan(np.radians([r['angle'] for r in data]))
                calibration[task+sensor]=[float(np.median(residual[:,0])),float(np.median(residual[:,1]/slope))]
        save(D/'lock.json',dict(prior=dz_by,calibration=calibration,hashes={str(p):sha(p) for p in [D/'geometry.py',D/'pipeline.py',D/'protocol.txt',D/'calibrate-predictions.json',DEV/'manifest.json',P/'manifest.json',P/'decisions.json',P/'before-replay.json',P/'server.py',P/'rig_base.py']}));return
    folder=P if mode=='test' else DEV
    if mode=='test':
        lock=read(D/'lock.json');assert all(sha(Path(p))==h for p,h in lock['hashes'].items());dz_by=lock['prior']
    rows=sorted((r for r in read(folder/'manifest.json') if r['task'] in dz_by),key=lambda r:r['id'])
    if mode=='dev':rows=[r for j,r in enumerate(rows) if j%9==0]
    # Strict per-image whitelist; world offsets and test fixture poses are never passed to the estimator.
    jobs=[(folder,r['id'],r['task'],r['gap'],r['angle'],r['depth'],dz_by[r['task']]) for r in rows]
    with concurrent.futures.ProcessPoolExecutor(max_workers=6) as pool: v=dict(pool.map(infer,jobs))
    if mode=='test':
        for r in rows:
            for m in ('rgb','rgbd'):
                cand=v[r['id']][m]; cand['raw']=cand['action'][:]
                if cand['localized']:
                    bx,bz=lock['calibration'][r['task']+m]
                    cand['action']=(np.array(cand['raw'])-[bx,bz*np.tan(np.radians(r['angle']))]).tolist()
    save(D/(mode+'-predictions.json'),v)
    if mode=='test':
        original=read(P/'actions.json')
        actions={i:{m:z[m]['action'] for m in ('rgb','rgbd')}|{m+'_raw':z[m]['raw'] for m in ('rgb','rgbd')}|{'sol_rgb':original[i]['direct'],'sol_rgbd':original[i]['always'],'oracle':original[i]['oracle']} for i,z in v.items()}
        save(D/'actions.json',actions)
    elif mode=='dev':
        for r in rows:
            a=v[r['id']];print(r['id'],r['task'],r['angle'],r['gap'],np.round(a['rgb']['action'],1),'expected',np.round([-r['x'],-r['y']],1),'fit',round(a['rgb']['match'],2),flush=True)
if __name__=='__main__':main()
