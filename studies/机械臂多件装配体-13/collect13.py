from pathlib import Path
import concurrent.futures as cf, subprocess,shutil,tempfile,json,re,random,time
import numpy as np
from decide13 import D,read,save,pose,angle,targets,markers,xy
from recipe_info import spec
def query(r,model,mode):
    i=r['id'];folder=D/'responses'/model;folder.mkdir(parents=True,exist_ok=True);out=folder/f'{i}-{mode}.json'
    if out.exists():return
    comp=spec(r);initial=D/'observations'/i;imgs=[initial/'initial-eye.jpg'];cam='eye'
    text=f'You control a physical simulated XY-Z-yaw gantry and two opposed jaws. Order: {r["recipe"][3:]}. Parts are free bodies. World X right, Y away, positive yaw counterclockwise seen from above. Pixel resolution 480x360, origin upper left. Machined part edges and mating axes are unmarked. No tools. JSON only. '
    trays='; '.join(f'{j+1}. {p["name"]} in staging nest near world XY {p["approx_source"]} mm, profile {p["profile"]}, thickness {p["thickness"]} mm, destination {p["column"]}' for j,p in enumerate(comp))
    text+=f'Bill of materials and assembly order: {trays}. Image scale: camera eye at (6,-205,239) mm looks at (0,0,5) mm, up oriented away, vertical FOV 38 deg. Two-column separation where relevant {r["span"]:.2f} mm. '
    text+=('Target anchor means the MIDPOINT of the two fixed brass posts. ' if markers(r) else 'Target anchor means the center of the SINGLE fixed brass post. ')
    text+='Define the anchor by two symmetric pixels on the mating X axis, left then right, over the top plane of the post (or centers of the two posts). For round single post take a horizontal diameter; for D-profile follow the direction to the flat; for blade follow its long axis. Unfilled holes and tray coordinates are for identifying the correct loose components. '
    if mode=='prefix':
        text+='Using the initial oblique image, locate every loose part. Report two points on its upper surface, symmetric around its center and along its long X axis, so the jaws can grasp across the shorter Y dimension. Include all parts in listed order. Command first-stage assembly and store the remaining grasp targets. Return {"op":"assemble","picks":[[[u,v],[u,v]],...],"anchor":[[u,v],[u,v]]}.'
    else:
        imgs.append(D/'runs'/model/i/'live-eye.jpg')
        text+='Image 1 = initial, image 2 = live AFTER the first commanded component. Using the station and newly observed placement, command remaining assembly in BOM order (grasp targets saved). Report updated mating anchor in the FIRST image, accounting for the live image when helpful. '
        if mode=='depth':
            imgs.extend([initial/'initial-depth.jpg',D/'runs'/model/i/'live-depth.jpg']);text+='Additional images are initial and live registered depth (fixed 225--370 mm optical depth color range; near yellow, far purple). '
        if mode=='overhead':
            imgs.extend([initial/'initial-top.jpg',D/'runs'/model/i/'live-top.jpg']);cam='top';text+='Override output frame: report anchor pixel coordinates in the INITIAL overhead image (image 3); image 4 is live overhead. '
        text+='Reply {"op":"assemble","anchor":[[u,v],[u,v]]}.'
    for attempt in range(3):
        try:
            with tempfile.TemporaryDirectory() as tmp:
                p=Path(tmp);cmd=[shutil.which('codex'),'exec','--ephemeral','--skip-git-repo-check','-s','read-only','--color','never','-m',model,'-c','model_reasoning_effort="medium"','-o',str(p/'ans')]
                for j,f in enumerate(imgs):
                    dest=p/f'camera{j}.jpg';shutil.copyfile(f,dest);cmd+=['-i',str(dest)]
                t=time.monotonic();pr=subprocess.run(cmd+['--','-'],input=text.encode(),cwd=p,capture_output=True,timeout=240)
                if pr.returncode or re.search(rb'^exec\s*$',pr.stderr,re.M):raise RuntimeError('invalid model call')
                raw=(p/'ans').read_text(encoding='utf8');obj=json.loads(re.search(r'\{[^{}]*\}',raw).group());assert obj['op']=='assemble'
                def decode(v,z,c):
                    pts=np.asarray(v,float).reshape(2,2);assert np.isfinite(pts).all() and (pts>=0).all() and (pts<[480,360]).all()
                    w=xy(pts,z,c);return pose(w.mean(0),angle(w[1]-w[0]))
                anchor=decode(obj['anchor'],comp[0]['pin_top'],cam)
                rec=dict(model=model,raw=raw,prompt=text,mode=mode,id=i,anchor=anchor,inputs=[x.relative_to(D).as_posix() for x in imgs],attempts=attempt+1,seconds=time.monotonic()-t)
                if mode=='prefix':
                    assert len(obj['picks'])==len(comp)
                    rec['picks']=[decode(v,c['thickness'],'eye') for v,c in zip(obj['picks'],comp)]
                save(out,rec);return
        except Exception:
            if attempt==2:raise
            time.sleep(attempt+1)
def collect(model,modes):
    rows=read(D/'scenes.json');jobs=[(r,k) for r in rows for k in modes];random.Random(103).shuffle(jobs)
    with cf.ThreadPoolExecutor(max_workers=10) as ex:
        fut=[ex.submit(query,r,model,k) for r,k in jobs]
        errs=[]
        for f in cf.as_completed(fut):
            try:f.result()
            except Exception as e:errs.append(str(e))
    if errs:raise ValueError(errs[:8])
def prefix_plan(model):
    actions={}
    for r in read(D/'scenes.json'):
        rec=read(D/'responses'/model/(r['id']+'-prefix.json'))
        actions[r['id']]=dict(op='assemble',pick=rec['picks'][0],place=targets(r,rec['anchor'])[0])
    save(D/(model+'-prefix.json'),actions)

