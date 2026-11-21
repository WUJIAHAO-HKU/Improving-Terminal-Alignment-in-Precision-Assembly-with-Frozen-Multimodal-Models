from pathlib import Path
import concurrent.futures as cf
import tempfile, subprocess, shutil, json, time, random, math, sys
D=Path(__file__).resolve().parent
MODEL='gpt-6.2-sol'
def predict(job):
    r,mode=job;out=D/'responses'/f"{r['id']}-{mode}.json"
    if out.exists():return
    task=r['task'];span=60 if task=='twin' else 48
    desc={'twin':'two-hole cover onto both round pins, 32 mm apart','blade':'rectangular slot over a 36 by 6 mm blade','dshaft':'D-bore onto D-shaft with its flat facing +X'}[task]
    prompt=f"""Output one JSON object with numeric dx,dy (mm) and yaw (degrees): one relative translation and yaw correction to seat a {desc}. Rotate about plate center; positive yaw is counterclockwise seen from above. Fixed red dots are 88 mm apart on the target X axis; moving green dots are {span} mm apart along the plate local X axis. Pair midpoints are the target and part origins. World X points right and Y away (up in overhead view). Camera1 looks obliquely from -Y at {r['pitch']} degrees from vertical. Cameras have 40 deg vertical FOV, 360 square pixels, look at (0,0,9) mm from distance 170 mm. Per-side clearance {r['gap']} mm. Account for different heights. Only use supplied images, no tools. Return dx,dy,yaw to one decimal place."""
    if mode=='view':prompt+=' Second image is a simultaneous overhead view of the same pose, with the same target and working distance.'
    started=time.monotonic()
    for attempt in range(1,4):
        try:
            with tempfile.TemporaryDirectory() as t:
                tmp=Path(t);cmd=[shutil.which('codex'),'exec','--ephemeral','--skip-git-repo-check','--color','never','-s','read-only','-m',MODEL,'-c','model_reasoning_effort="medium"','-o',str(tmp/'answer.txt')]
                for j,cam in enumerate(['rgb','top'] if mode=='view' else ['rgb']):
                    im=tmp/f'camera{j+1}.png';shutil.copyfile(D/'frames'/f"{r['id']}-{cam}.png",im);cmd+=['-i',str(im)]
                res=subprocess.run(cmd+["--","-"],input=prompt.encode(),cwd=tmp,capture_output=True,timeout=240)
                if res.returncode:raise RuntimeError(res.stderr.decode(errors='replace')[-480:])
                import re
                if re.search(rb'^exec\s*$',res.stderr,re.M):raise ValueError('unexpected tool use')
                raw=(tmp/'answer.txt').read_text(encoding='utf8');obj=json.loads(re.search(r'\{[^{}]*\}',raw).group())
                act=[float(obj[k]) for k in ('dx','dy','yaw')]
                if not all(math.isfinite(v) and abs(v)<=300 for v in act):raise ValueError('invalid action')
                out.write_text(json.dumps(dict(model=MODEL,mode=mode,id=r['id'],action=act,prompt=prompt,raw=raw,attempts=attempt,seconds=round(time.monotonic()-started,2)),indent=2),encoding='utf8')
                return
        except Exception as e:
            if attempt==3:raise
            time.sleep(attempt)
if __name__=='__main__':
    rows=json.loads((D/'scenes.json').read_text());(D/'responses').mkdir(exist_ok=True)
    jobs=[(r,m) for r in rows for m in ('rgb','view','repeat')]
    random.Random(151).shuffle(jobs)
    if len(sys.argv)>1:jobs=jobs[:int(sys.argv[1])]
    with cf.ThreadPoolExecutor(max_workers=10) as ex:
        fut=[ex.submit(predict,j) for j in jobs]
        for i,f in enumerate(cf.as_completed(fut),1):f.result();print(i,flush=True)

