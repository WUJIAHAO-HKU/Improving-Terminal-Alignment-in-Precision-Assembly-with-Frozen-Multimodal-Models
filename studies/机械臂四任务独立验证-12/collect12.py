from pathlib import Path
import sys,subprocess,concurrent.futures as cf, shutil, time, json, random, tempfile,re
import numpy as np
from policy import xy,pose,public
D=Path(__file__).resolve().parent
def get(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def modelcall(row,model,mode):
    i=row['id'];r=public(row);out=D/'responses'/model/(i+'-'+mode+'.json');out.parent.mkdir(exist_ok=True,parents=True)
    if out.exists():return
    name={'twin':'two-dowel cover','blade':'slotted blade collar','dshaft':'D-shaped sleeve with flat to local +X','connector':'two-hole keyed connector'}[r['task']]
    desc=f"The task is to insert the unmarked {name}. Recipe dimension {r['size']} mm, part outer width {r['width']} mm, clearance per side {r['gap']} mm. "
    imgs=[D/'initial'/i/'00-eye.png']
    text="You operate an XYZ+yaw Cartesian robot with a parallel-jaw gripper. Reply JSON only. No tools. World X increases toward image right, Y away; yaw is counterclockwise from above. Images 480x360. Pixel coordinates (u,v) from top left. The gray movable component starts left of the dark receiving fixture with brass mating features. "+desc
    if mode=='grip':
        text+='Command pick and lift; locate two points on its longitudinal centerline, symmetric about the MOVABLE component center, left then right, on the top face. Do not target the receiving fixture. Use visible long plate edges to judge yaw. Return {"op":"pick","points":[[u,v],[u,v]]}.'
        cam='eye';z=6
    else:
        imgs.append(D/'sim'/model/i/'01-eye.png');text+='First image is the original oblique view and second is live after model-commanded grasp/lift. '
        if r['port']:text+=f"The order specifies the {r['port']} receiver: near means closer to the oblique camera (smaller world Y), far means further from it. Both are physically mateable; only the requested socket counts. "
        if mode=='overhead':
            imgs.append(D/'initial'/i/'00-top.png');text+='Third image is the optional simultaneous overhead view of the ORIGINAL scene. Output pixel coordinates in that THIRD image. ';cam='top'
        else:
            cam='eye';text+='Output pixel coordinates in the FIRST image. '
            if mode=='depth':
                imgs.append(D/'initial'/i/'00-depth.png');text+='Third image is registered optical-axis depth of the first view, fixed viridis scale closest yellow at 235 mm, farthest purple at 355 mm. '
        text+='Command motion to the receiving feature and insertion followed by release. Give two points along the long mating axis at the 14 mm high peg tops, symmetric around the desired wrist center. For twin or connector use both pin tops. For a slot use the ends of the blade centerline. For D-shaft use ends of an axis passing through its shaft center and pointing to the flat, NOT the truncated silhouette midpoint. Correct for grasp offset if visible. Return {"op":"assemble","points":[[u1,v1],[u2,v2]]}.'
        z=14
    for n in range(3):
        try:
            with tempfile.TemporaryDirectory() as tmp:
                p=Path(tmp);cmd=[shutil.which('codex'),'exec','--ephemeral','--skip-git-repo-check','-s','read-only','--color','never','-c','model_reasoning_effort="medium"','-m',model,'-o',str(p/'action.json')]
                for j,img in enumerate(imgs):
                    dest=p/f'im{j}.png';shutil.copyfile(img,dest);cmd+=['-i',str(dest)]
                t=time.monotonic();result=subprocess.run(cmd+['--','-'],input=text.encode(),cwd=p,capture_output=True,timeout=230)
                if result.returncode or re.search(rb'^exec\s*$',result.stderr,re.M):raise RuntimeError('invalid model run')
                raw=(p/'action.json').read_text(encoding='utf8');q=json.loads(re.search(r'\{[^{}]+\}',raw).group())
                assert q['op']==('pick' if mode=='grip' else 'assemble');pts=np.array(q['points'],float).reshape(2,2);assert np.isfinite(pts).all() and (pts>=0).all() and (pts<[480,360]).all()
                w=xy(pts,z,cam);diff=w[1]-w[0];theta=(np.rad2deg(np.arctan2(diff[1],diff[0]))+90)%180-90
                rec=dict(model=model,mode=mode,id=i,raw=raw,action=pose(*w.mean(0),theta),prompt=text,input_images=[x.relative_to(D).as_posix() for x in imgs],seconds=time.monotonic()-t,attempts=n+1)
                out.write_text(json.dumps(rec,indent=2),encoding='utf8');return
        except Exception as e:
            if n==2:raise
            time.sleep(n+1)
def collect(model,modes):
    rows=get(D/'scenes.json');jobs=[(r,m) for r in rows for m in modes];random.Random(4506).shuffle(jobs)
    fails=[]
    with cf.ThreadPoolExecutor(max_workers=9) as ex:
        futures={ex.submit(modelcall,r,model,m):(r['id'],m) for r,m in jobs}
        for f in cf.as_completed(futures):
            try:f.result()
            except Exception as e:fails.append((futures[f],str(e)))
    if fails:raise RuntimeError(str(fails[:10]))
if __name__=='__main__':collect(sys.argv[1],sys.argv[2:])

