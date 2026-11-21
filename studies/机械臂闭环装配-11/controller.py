"""One fresh visual model request per policy decision; calibrated pixel-space motion interface."""
from pathlib import Path
import subprocess,sys,json,tempfile,shutil,math,time,re,concurrent.futures as cf
import numpy as np
from PIL import Image,ImageDraw
D=Path(__file__).resolve().parent
SERVER='assembly-jobs/arm-assembly'
TARGET='assembly-sim-a'

def proc(cmd,**kw):
    pr=subprocess.run(cmd,capture_output=True,**kw)
    if pr.returncode:raise RuntimeError((pr.stderr or pr.stdout).decode(errors='replace')[-900:])
    return pr.stdout
def ssh(command):return proc(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=8',TARGET,command],timeout=180)
def copy(src,dst):return proc(['scp','-q','-o','BatchMode=yes',str(src),str(dst)],timeout=120)
def save(p,obj):
    tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(obj,indent=2,allow_nan=False),encoding='utf8');tmp.replace(p)
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def step(folder,scene,index,act):
    f=folder/f'{index:02}.json'
    if f.exists():return read(f)
    req=dict(folder=f'runs/{folder.name}',scene=scene,step=index,action=act)
    local=folder/f'req{index:02}.json';save(local,req);name=folder.name+'-'+local.name
    copy(local,TARGET+':'+SERVER+'/'+name)
    ssh(f'cd {SERVER} && MUJOCO_GL=egl PYOPENGL_PLATFORM=egl python3 cell.py {name}')
    remote=TARGET+':'+SERVER+'/runs/'+folder.name+'/'
    for suffix in ['-eye.png','-top.png','.json']:
        filename=f'{index:02}'+suffix
        copy(remote+filename,folder/filename)
    return read(f)
def locate(pixel,z,cam='eye'):
    xyz=np.array([6,-205,239] if cam=='eye' else [0,0,294],float)
    back=xyz-np.array([0,0,5] if cam=='eye' else [0,0,0]);back/=np.linalg.norm(back)
    right=np.cross([0,0,1],back);right=right/np.linalg.norm(right) if np.linalg.norm(right)>1e-8 else np.array([1.,0,0])
    up=np.cross(back,right);f=180/np.tan(np.radians(38 if cam=='eye' else 37)/2)
    ray=-back+(pixel[0]-239.5)/f*right+(179.5-pixel[1])/f*up
    return (xyz+ray*(z-xyz[2])/ray[2])[:2]
def ask(folder,model,tag,imgs,instruction):
    dest=folder/(tag+'.json')
    if dest.exists():return read(dest)['answer']
    prompt="""You control a real simulated XYZ yaw gantry with a parallel gripper. No tools. Use the image(s) and telemetry, not internal state. Image resolution 480x360. Pixel (0,0) is top left. Millimetres; world +X is right, +Y away from camera. Positive yaw is counterclockwise from above. Fixed brass pins are on a dark base. Movable gray plate has two holes. Jaws grasp across its short sides. Output exactly one JSON object. """+instruction
    for attempt in range(3):
        try:
            with tempfile.TemporaryDirectory() as tmp:
                p=Path(tmp);cmd=[shutil.which('codex'),'exec','--ephemeral','--skip-git-repo-check','-s','read-only','--color','never','-m',model,'-c','model_reasoning_effort="medium"','-o',str(p/'reply')]
                for j,img in enumerate(imgs):
                    f=p/f'camera{j}.png';shutil.copyfile(img,f);cmd+=['-i',str(f)]
                t=time.monotonic();pr=subprocess.run(cmd+['--','-'],input=prompt.encode(),cwd=p,capture_output=True,timeout=210)
                if pr.returncode or re.search(rb'^exec\s*$',pr.stderr,re.M):raise RuntimeError('model request did not finish without tools: '+pr.stderr.decode(errors='replace')[-160:])
                raw=(p/'reply').read_text(encoding='utf8');answer=json.loads(re.search(r'\{[^{}]+\}',raw).group())
                save(dest,dict(requested_model=model,images=[i.name for i in imgs],prompt=prompt,raw=raw,answer=answer,seconds=time.monotonic()-t,attempt=attempt+1))
                return answer
        except Exception:
            if attempt==2:raise
            time.sleep(2)
def points(a,z,cam):
    pts=np.asarray(a['points'],dtype=float).reshape(2,2)
    if not np.isfinite(pts).all() or np.any(pts<0) or np.any(pts>=[480,360]):raise ValueError('coordinates outside camera')
    v=np.array([locate(x,z,cam) for x in pts]);delta=v[1]-v[0]
    yaw=(np.degrees(np.arctan2(delta[1],delta[0]))+90)%180-90
    return v.mean(axis=0),float(np.clip(yaw,-70,70))
INSPECT='Return {"op":"insert"} if ready to lower along Z; or {"op":"correct","dx":mm,"dy":mm,"dyaw":degrees} to adjust based on the visible holes and pins before insertion.'
def offset(arm,a,op):
    vals=[float(a.get(k,0)) for k in ('dx','dy','dyaw')];assert np.isfinite(vals).all()
    return dict(op=op,x=float(np.clip(arm[0]+np.clip(vals[0],-15,15),-90,90)),y=float(np.clip(arm[1]+np.clip(vals[1],-15,15),-53,53)),yaw=float(np.clip(arm[3]+np.clip(vals[2],-25,25),-75,75)),z=35)
def trial(params):
    model,scene=params;folder=D/'runs'/(model+'-'+scene['id']);folder.mkdir(parents=True,exist_ok=True);final=folder/'result.json'
    if final.exists():return read(final)
    idx=0;log=[]
    def move(act):
        nonlocal idx
        s=step(folder,scene,idx,act);log.append((idx,act,s));idx+=1;return s
    def eye():return folder/f'{idx-1:02}-eye.png'
    s=move(dict(op='observe'));initial=eye()
    q=ask(folder,model,'pick',[initial],'Locate the centres of the two moving plate holes in this oblique RGB, left then right. Command grasp, close and lift via {"op":"pick","points":[[u1,v1],[u2,v2]]}. The top of the loose plate is 6 mm above table.')
    if q.get('op')!='pick':raise ValueError('invalid pick')
    center,yaw=points(q,6,'eye');s=move(dict(op='pick',x=float(center[0]),y=float(center[1]),yaw=yaw))
    grip={'leftpad','rightpad'}.issubset(s['contacts'])
    retries=0;measured=False;kept=None
    if grip:
        q=ask(folder,model,'transport',[initial,eye()],f'Jaw contact on both sides. First image is the ORIGINAL scene before grasp, second is live. In FIRST image locate the top centres of both fixed pins (left then right) to command transport and alignment. Their tops are 14 mm above table. Decide whether an extra overhead measurement is warranted after transport. Return {{"op":"carry","points":[[u1,v1],[u2,v2]],"measure":true or false}}. Nominal per-side clearance {scene["gap"]} mm.')
        if q.get('op')!='carry' or type(q.get('measure')) is not bool:raise ValueError('invalid transport')
        center,yaw=points(q,14,'eye');s=move(dict(op='carry',x=float(center[0]),y=float(center[1]),yaw=yaw,z=35))
        measured=q['measure'];imgs=[eye()];tag='initial alignment'
        if measured:imgs.append(folder/f'{idx-1:02}-top.png');tag+=' plus requested overhead view'
        q=ask(folder,model,'accept',imgs,tag+'. Current wrist world [x,y,z,yaw] '+str(np.round(s['arm'],1).tolist())+'. Decide whether to keep original pose for insertion or replace it with a relative correction. '+INSPECT);kept=q['op']=='insert'
        if not kept:
            if q['op']!='correct':raise ValueError('unexpected alignment decision')
            s=move(offset(s['arm'],q,'correct'))
        # Insertion force/arm tracking alarm uses gripper encoder, not hidden seated labels.
        s=move(dict(op='insert'))
        for cycle in range(2):
            alarm=s['arm'][2]-7.3>1.2
            q=ask(folder,model,'inspect'+str(cycle),[eye()],f'Insertion command height 7.3 mm; measured wrist height {s["arm"][2]:.2f} mm; following-error alarm {alarm}. Decide release/open jaws or retract and retry with a relative correction bounded to 15 mm, 25 degrees. Return {{"op":"release"}} or {{"op":"retry","dx":mm,"dy":mm,"dyaw":degrees}}. Remaining permitted retries: {1-cycle}.')
            if q['op']=='release':break
            if cycle==1:raise ValueError('retry requested after limit; require a valid terminal decision')
            if q['op']!='retry':raise ValueError('invalid inspection')
            retries+=1;s=move(offset(s['arm'],q,'retry'));s=move(dict(op='insert'))
    s=move(dict(op='release'))
    lifted=any(any(x['left'] and x['right'] and x['part'][2]>25 for x in st['trace']) for _,act,st in log if act['op']=='pick')
    carried=any(sum(x['left'] and x['right'] for x in st['trace'])>=8 for _,act,st in log if act['op']=='carry')
    drift=np.linalg.norm(np.array(s['trace'][-1]['part'])-s['trace'][-4]['part'])
    result=dict(scene=scene['id'],model=model,grasp=grip,lift=lifted,carry=carried,measure=measured,kept=kept,retries=retries,success=bool(grip and lifted and carried and s['seat'] and drift<.35 and 'leftpad' not in s['contacts'] and 'rightpad' not in s['contacts']),final_pin_errors=s['errors'],final_height=s['part'][2],release_drift_mm=float(drift))
    path=SERVER+'/runs/'+folder.name
    ssh('cd '+path+' && for f in clip*.mp4; do echo file $f; done > clips.txt && ffmpeg -loglevel error -y -f concat -safe 0 -i clips.txt -c copy execution.mp4')
    copy(TARGET+':'+path+'/execution.mp4',folder/'execution.mp4')
    save(final,result);print(result,flush=True);return result
if __name__=='__main__':
    rows=read(D/'pilot-scenes.json')
    jobs=[(m,r) for r in rows for m in ('gpt-6.2-sol','gpt-6.1-terra')]
    if len(sys.argv)>1:jobs=jobs[:int(sys.argv[1])]
    with cf.ThreadPoolExecutor(max_workers=4) as e:
        futures=[e.submit(trial,j) for j in jobs];bad=[]
        for f in cf.as_completed(futures):
            try:f.result()
            except Exception as ex:bad.append(str(ex));print('ERROR',str(ex),flush=True)
        if bad:raise RuntimeError(str(bad))

