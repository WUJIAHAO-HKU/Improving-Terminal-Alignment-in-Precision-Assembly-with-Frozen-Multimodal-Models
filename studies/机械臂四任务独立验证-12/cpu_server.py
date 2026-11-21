"""Physics pipeline: initial observation, model-directed grip, branched real arm transport/insertion/release."""
from pathlib import Path
import json,sys,shutil,os,traceback
import numpy as np
from cpu_gantry import Cell
from PIL import Image
D=Path(__file__).resolve().parent
def get(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,obj):p.write_text(json.dumps(obj,allow_nan=False),encoding='utf8')
def primary(r):
    d=D/'initial'/r['id'];c=Cell(r,d,0);c.apply({'op':'observe'});s=c.finish()
    # RGB-D camera depth: metric values displayed using one fixed calibration for all samples.
    import cv2
    depth=np.load(d/'00-depth.npy')
    u=np.clip((depth-235)/120,0,1);img=cv2.applyColorMap((255*(1-u)).astype('uint8'),cv2.COLORMAP_VIRIDIS)[:,:,::-1];Image.fromarray(img).save(d/'00-depth.png')
def grip(r,job,model):
    d=D/'sim'/model/r['id'];d.mkdir(parents=True,exist_ok=True);shutil.copy2(D/'initial'/r['id']/'state.npz',d/'state.npz')
    c=Cell(r,d,1);c.apply(dict(op='pick',**job));s=c.finish()
    lifted=any(x['left'] and x['right'] and x['part'][2]>25 for x in s['trace']);save(d/'grip.json',dict(lifted=lifted,bilateral={'leftpad','rightpad'}.issubset(s['contacts']),arm=s['arm']))
def evaluate(r,model,actions):
    d=D/'sim'/model/r['id'];g=get(d/'grip.json');cache={}
    outcomes={}
    for label,arg in actions.items():
        key=tuple(round(arg[k],4) for k in ['x','y','yaw'])
        if key in cache:outcomes[label]=dict(cache[key]);continue
        if not g['lifted'] or not g['bilateral']:
            outcomes[label]=dict(ok=False,reason='grasp');continue
        branch=d/('branch-'+label);branch.mkdir(parents=True,exist_ok=True);shutil.copy2(d/'state.npz',branch/'state.npz')
        c=Cell(r,branch,2)
        c.apply(dict(op='carry',z=35,**arg));carry=sum(x['left'] and x['right'] for x in c.samples)>=8
        c.apply(dict(op='insert'));c.apply(dict(op='release'));s=c.finish()
        drift=float(np.linalg.norm(np.subtract(s['trace'][-1]['part'],s['trace'][-4]['part'])))
        ok=bool(carry and s['seat'] and drift<.35 and not {'rightpad','leftpad'}.intersection(s['contacts']))
        outcomes[label]=dict(ok=ok,reason='seated' if ok else 'carry' if not carry else 'endpoint',height=s['part'][2],margin=s['containment_mm'],tilt=s['tilt'],drift=drift);cache[key]=outcomes[label]
    save(d/'outcomes.json',outcomes)
def run_job(args):
    r,mode,model,action=args
    if mode=='prepare':primary(r)
    elif mode=='grip':grip(r,action,model)
    else:evaluate(r,model,action)
if __name__=='__main__':
    import multiprocessing as mp
    mode=sys.argv[1];rows=get(D/'scenes.json');model=sys.argv[2] if len(sys.argv)>2 else ''
    jobs=get(D/(model+'-'+mode+'.json')) if model else {r['id']:{} for r in rows}
    with mp.get_context('spawn').Pool(int(os.environ.get('WORKERS','4')),maxtasksperchild=15) as pool:
        pool.map(run_job,[(r,mode,model,jobs[r['id']]) for r in rows if r['id'] in jobs],chunksize=1)

