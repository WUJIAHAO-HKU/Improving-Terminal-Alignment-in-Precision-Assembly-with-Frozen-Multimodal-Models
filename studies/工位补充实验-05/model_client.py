"""One anonymously named image per fresh model request. Save raw outputs and actual CLI request logs."""
import concurrent.futures, json, pathlib, subprocess, tempfile, shutil, time, re, random, sys, os, math
from statistics import median
D=pathlib.Path(__file__).resolve().parent
rows=json.loads((D/'manifest.json').read_text());responses=D/'responses';responses.mkdir(exist_ok=True)
def resp(r,mode,model):
    return responses/f"{r['id']}--{model}--{mode}.json"
def predict(job):
    r,mode,model=job;out=resp(r,mode,model)
    if out.exists():return
    task=r['task'];g=r['gap'];radius={'square':22.75,'round':31.1764,'dual':50}[task]
    part={'square':'brown square nut aperture and the stationary square peg below','round':'steel ring (inner edges around its central bore) and the stationary round peg below','dual':'red plate square aperture and green stationary cylindrical pin below'}[task]
    prompt=f"""Precision-assembly visual action benchmark. One 320x320 RGB scene showing a {part}. Move the HOLE part horizontally so its aperture center is exactly above the stationary peg axis. Ignore the handle. Predict the ideal move in robot world millimeters. Camera looks downward, tilted {r['angle']} degrees toward world +Y. Image right = +X, up = away toward +Y. FOV 30 degrees vertical, optical center (159.5,159.5). Nominal camera working distance roughly {500 if task=='dual' else 360} mm. Nominal aperture width {2*radius:.2f} mm. Peg width or diameter {2*(radius-g):.2f} mm. Account for parallax and any occlusion. Use only this image and prompt. No tools. Output only one JSON object with dx and dy in mm, to one decimal place."""
    if mode=='measured':
        prompt+=f" Additional rendered RGB-D measurement: estimated vertical distances BELOW CAMERA ORIGIN to upper face of moving part {r['depth']['near']} mm and to stationary peg top {r['depth']['far']} mm. These are vertical distances, not optical-axis depths. Measurements may contain noise."
    if mode=='stress':
        prompt+=" Also align the moving hole plane parallel to the table using rotation about world X (roll) and, for square peg only, around world Z (yaw). Initially the part may be aligned already. Handle points along +X at zero yaw. Positive roll raises +Y side; positive yaw rotates +X toward +Y. Give angular CORRECTIONS in degrees about the aperture center (apply as increments to current world roll and yaw). Return only JSON with four numeric keys dx, dy, roll, yaw. Use yaw=0 for a cylindrical peg."
    call_start=time.monotonic()
    for attempt in range(3):
        with tempfile.TemporaryDirectory() as tmp:
            tmp=pathlib.Path(tmp);im=tmp/'observation.jpg';shutil.copyfile(D/'frames'/(r['id']+'.jpg'),im)
            cmd=[shutil.which('codex'),'exec','--ephemeral','--skip-git-repo-check','--color','never','-s','read-only','-m',model,'-c','model_reasoning_effort="medium"','-i',str(im),'-o',str(tmp/'out.txt'),prompt]
            start=time.monotonic()
            try:
                z=subprocess.run(cmd,cwd=tmp,stdin=subprocess.DEVNULL,capture_output=True,timeout=170)
                if z.returncode:raise RuntimeError(z.stderr.decode(errors='replace')[-450:])
                raw=(tmp/'out.txt').read_text(encoding='utf-8');d=json.loads(re.search(r'\{[^{}]+\}',raw).group())
                act=[float(d[k]) for k in (('dx','dy','roll','yaw') if mode=='stress' else ('dx','dy'))]
                assert all(math.isfinite(v) and abs(v)<300 for v in act)
                if re.search(r'^exec\s*$',z.stderr.decode(errors='replace'),re.M):raise RuntimeError('unexpected tool action')
                record=dict(model=model,id=r['id'],mode=mode,prompt=prompt,raw=raw,action=act,seconds=round(time.monotonic()-call_start,3),final_attempt_s=round(time.monotonic()-start,3),attempts=attempt+1)
                out.write_text(json.dumps(record),encoding='utf-8');return
            except Exception as e:
                if attempt==2:raise
                time.sleep(1+attempt)
def run(jobs):
    random.Random(7291).shuffle(jobs)
    with concurrent.futures.ThreadPoolExecutor(max_workers=int(os.environ.get('ASSEMBLY_WORKERS','8'))) as ex:
        fut=[ex.submit(predict,j) for j in jobs];errors=[]
        for i,f in enumerate(concurrent.futures.as_completed(fut),1):
            try:f.result()
            except Exception as e:errors.append(str(e))
            if i%10==0:print('completed',i,'/',len(fut),'errors',len(errors),flush=True)
    if errors:raise RuntimeError(errors[:3])
def get(r,m,model='gpt-6.2-sol'):
    return json.loads(resp(r,m,model).read_text())['action']
if __name__=='__main__':
    mode=sys.argv[1]
    if mode=='cal':
        run([(r,'direct','gpt-6.2-sol') for r in rows if r['split']=='cal'])
        bounds={}
        for task in ('square','round','dual'):
            vals=[]
            for k in range(4):
                errs=[]
                for r in rows:
                    if (r['split'],r['task'],r['k'])!=('cal',task,k):continue
                    ax,ay=get(r,'direct');ex,ey=ax+r['x'],ay+r['y']
                    errs.append(math.hypot(ex,ey) if task=='round' else max(abs(ex),abs(ey)))
                vals.append(median(errs))
            bounds[task]=sorted(vals)[2] # pre-specified 3rd of four scene-seed median residuals
        (D/'locked-gate.json').write_text(json.dumps(bounds,indent=2));print(bounds)
    if mode=='test':
        assert (D/'locked-gate.json').exists()
        run([(r,m,model) for r in rows if r['split']=='test' for model,m in [('gpt-6.2-sol','direct'),('gpt-6.2-sol','measured'),('gpt-6.1-terra','direct')]])
    if mode=='stress':
        responses=D/'stress-responses';responses.mkdir(exist_ok=True)
        stress=json.loads((D/'stress-manifest.json').read_text())
        run([(r,'stress',model) for r in stress for model in ['gpt-6.2-sol','gpt-6.1-terra']])
        acts={r['id']:{model:get(r,'stress',model) for model in ['gpt-6.2-sol','gpt-6.1-terra']} for r in stress}
        for r in stress:acts[r['id']]['oracle']=[-r['x'],-r['y'],-r['tilt'],-r['yaw']]
        (D/'stress-actions.json').write_text(json.dumps(acts))
    if mode=='actions':
        gate=json.loads((D/'locked-gate.json').read_text());actions={}
        for r in rows:
            if r['split']!='test':continue
            d=get(r,'direct');m=get(r,'measured');actions[r['id']]=dict(direct=d,always=m,on_demand=m if r['gap']<=gate[r['task']] else d,terra=get(r,'direct','gpt-6.1-terra'),oracle=[-r['x'],-r['y']])
        (D/'actions.json').write_text(json.dumps(actions))

