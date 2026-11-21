"""Per-step robot observations and full physical branching for a model-issued ordered recipe."""
from kit import *
from PIL import Image
import cv2
def frames(folder,m,d,ren,tag):
    for cam in ['eye','top']:
        ren.update_scene(d,camera=cam);Image.fromarray(ren.render()).save(folder/f'{tag}-{cam}.jpg',quality=92)
    ren.enable_depth_rendering();ren.update_scene(d,camera='eye');depth=ren.render()*1000;ren.disable_depth_rendering()
    np.save(folder/f'{tag}-depth.npy',depth.astype('float32'))
    u=np.clip((depth-225)/145,0,1);b=cv2.applyColorMap((255*(1-u)).astype('uint8'),cv2.COLORMAP_VIRIDIS)
    Image.fromarray(b[:,:,::-1]).save(folder/f'{tag}-depth.jpg',quality=92)
def prepare(r):
    m,d,steps=make(r);init(m,d);folder=Path('observations')/r['id'];folder.mkdir(parents=True,exist_ok=True)
    with mj.Renderer(m,height=360,width=480) as ren:frames(folder,m,d,ren,'initial')
def prefix(arg):
    r,model,cmd=arg;m,d,steps=make(r);init(m,d);folder=Path('runs')/model/r['id'];folder.mkdir(parents=True,exist_ok=True)
    assert cmd['op']=='assemble'
    v,trace=perform(m,d,r,0,cmd['pick'],cmd['place'],steps);v['q']=trace[::4]
    (folder/'common.json').write_text(json.dumps(v))
    with mj.Renderer(m,height=360,width=480) as ren:frames(folder,m,d,ren,'live')
    spec=mj.mjtState.mjSTATE_INTEGRATION;state=np.empty(mj.mj_stateSize(m,spec));mj.mj_getState(m,d,state,spec);np.save(folder/'common.npy',state)
def replay(arg):
    r,model,plans=arg;m,d,steps=make(r);folder=Path('runs')/model/r['id'];folder.mkdir(parents=True,exist_ok=True)
    results={};common=json.loads((folder/'common.json').read_text());state=np.load(folder/'common.npy');spec=mj.mjtState.mjSTATE_INTEGRATION
    cache={}
    for mode,plan in plans.items():
        mj.mj_resetData(m,d);mj.mj_setState(m,d,state,spec);mj.mj_forward(m,d);events=[common];key=()
        for j,cmd in enumerate(plan,1):
            if not (events[-1]['lift'] and events[-1]['carry']):break
            if cmd['op']!='assemble':raise ValueError('unauthorized robot primitive')
            p=cmd['pick'];a=cmd['place']
            # The action bound is part of the deployed arm interface, not a post hoc filter.
            p=[float(np.clip(p[0],-102,102)),float(np.clip(p[1],-62,62)),float(np.clip(p[2],-80,80))]
            a=[float(np.clip(a[0],-102,102)),float(np.clip(a[1],-62,62)),float(np.clip(a[2],-80,80))]
            key+=tuple(p+a)
            if key in cache:
                v,saved=cache[key];mj.mj_setState(m,d,saved,spec);mj.mj_forward(m,d)
            else:
                v,trace=perform(m,d,r,j,p,a,steps);v['q']=trace[::4]
                saved=np.empty(mj.mj_stateSize(m,spec));mj.mj_getState(m,d,saved,spec);cache[key]=(v,saved)
            events.append(v)
            # Bilateral transport interlock; post-release seated labels never control the next step.
            if not (v['lift'] and v['carry']):break
        final=[judge(m,d,r,s,j)['seat'] for j,s in enumerate(steps)]
        results[mode]=dict(complete=bool(len(events)==len(steps) and all(v['ok'] for v in events) and all(final)),events=events,final=final)
    (folder/'results.json').write_text(json.dumps(results,separators=(',',':')))
if __name__=='__main__':
    import multiprocessing as mp
    mode=sys.argv[1];rows=json.loads(Path('scenes.json').read_text(encoding='utf-8-sig'))
    if mode=='prepare':
        with mp.get_context('spawn').Pool(3,maxtasksperchild=10) as pool:pool.map(prepare,rows,chunksize=1)
    elif mode=='prefix':
        model=sys.argv[2];plans=json.loads(Path(model+'-prefix.json').read_text(encoding='utf8'))
        with mp.get_context('spawn').Pool(3,maxtasksperchild=8) as pool:pool.map(prefix,[(r,model,plans[r['id']]) for r in rows],chunksize=1)
    else:
        model=sys.argv[2];plans=json.loads(Path(model+'-plans.json').read_text(encoding='utf8'))
        with mp.get_context('spawn').Pool(3,maxtasksperchild=6) as pool:pool.map(replay,[(r,model,plans[r['id']]) for r in rows],chunksize=1)

