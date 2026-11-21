from pathlib import Path
import concurrent.futures as cf,subprocess,sys,json,re,tempfile,shutil,tarfile,time,hashlib
D=Path(__file__).resolve().parent
from station import config
host='assembly-sim-c';base='assembly-jobs/franka-station-rule15';OP=['-o','BatchMode=yes','-o','ConnectTimeout=10'];py='MUJOCO_GL=egl PYOPENGL_PLATFORM=egl OPENBLAS_NUM_THREADS=1 PYTHONPATH=site-packages python3'
def cmd(xs):subprocess.run(xs,check=True,cwd=D)
def ssh(x):cmd(['ssh',*OP,host,x])
def copy(src,dest):cmd(['scp','-q',*OP,src,dest])
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def query(m,img,prompt):
    for attempt in range(3):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);shutil.copyfile(img,p/'view.jpg')
            proc=subprocess.run([shutil.which('codex'),'exec','--ephemeral','--skip-git-repo-check','-s','read-only','--color','never','-c','model_reasoning_effort="medium"','-m',m,'-i',str(p/'view.jpg'),'-o',str(p/'answer'),'--','-'],input=prompt.encode(),cwd=p,capture_output=True,timeout=290)
            if proc.returncode or re.search(rb'^exec\s*$',proc.stderr,re.M):continue
            raw=(p/'answer').read_text(encoding='utf8')
            try:
                v=json.loads(re.search(r'\{[^{}]*\}',raw).group());assert v['op'] in ('place','tighten')
                for key in (['pick','base'] if v['op']=='place' else ['socket']):
                    assert len(v[key])==2 and all(isinstance(x,(float,int)) and x>=0 and x<lim for x,lim in zip(v[key],[480,360]))
                return v,raw
            except (ValueError,AssertionError,KeyError,AttributeError):pass
    raise RuntimeError('unusable model reply '+m)
def run(z):
    m,k=z;c=config(k);folder=D/'runs'/f'{m}-{k}';folder.mkdir(parents=True,exist_ok=True);rel=folder.relative_to(D).as_posix()
    def run_cmd(arg):ssh('cd '+base+' && '+py+' episode.py '+str(k)+' '+rel+' '+arg)
    run_cmd('init')
    for j in range(len(c['parts'])+2):
        stem=f'{j:02}';img=folder/('live-'+stem+'.jpg');copy(host+':'+base+'/'+rel+'/'+img.name,str(img));p=c['parts']
        text='You operate a seven-joint Franka Panda assembly station, from its live 480 by 360 overhead RGB image. Pixel origin top-left. X points right, Y up. Pick parts by friction jaws; two visible gray screws on the long final flange are captive. Lighting can produce dark shadows. No tools. Return JSON only. Product '+c['title']+'. '
        if j<len(p):
            approx=p[j]['src'];text+=f"Next command: pick {p[j]['name']}, stored in the nest near {round(approx[0]/.02)*.02:.2f},{round(approx[1]/.02)*.02:.2f} metres. Camera principal point at (239.5,179.5) corresponds to world (0.50,0) and scale roughly 1.4 mm/px. Read the ACTUAL center of the LOOSE part in this image. Also locate the geometric center of the stationary rectangular base in the upper central work area (often partially covered by earlier components). Specify the base center; the controller adds the recipe's column offset. Return "+'{"op":"place","pick":[u,v],"base":[u,v]}.'
        else:text+=('Engage the '+('left' if j==len(p) else 'right')+' captive screw head on the placed flange. Use its current observed head center. The driver will stop at the prescribed simulated torque. Return {"op":"tighten","socket":[u,v]}.')
        act,raw=query(m,img,text);assert act['op']==('place' if j<len(p) else 'tighten');act['index']=j if j<len(p) else j-len(p);ap=folder/('action-'+stem+'.json');ap.write_text(json.dumps(act),encoding='utf8')
        (folder/('prompt-'+stem+'.json')).write_text(json.dumps(dict(model=m,prompt=text,raw=raw,image=img.name),indent=2),encoding='utf8')
        copy(str(ap),host+':'+base+'/'+rel+'/');run_cmd(ap.name)
    run_cmd('video')
    pack=f'{m}-{k}.tgz';ssh('cd '+base+' && tar czf '+pack+' '+rel);copy(host+':'+base+'/'+pack,pack)
    with tarfile.open(D/pack) as t:t.extractall(D,filter='data')
    ev=[read(p) for p in sorted(folder.glob('out-*.json'))];assert [v['ok'] for v in ev]==read(folder/'video-check.json')
    print(m,k,[v['ok'] for v in ev],flush=True)
if __name__=='__main__':
    ssh('mkdir -p '+base)
    with tarfile.open(D/'station.tgz','w:gz') as t:
        for n in ['station.py','robot.py','episode.py','template.xml','assets','panda-LICENSE']:t.add(D/n,arcname=n)
    copy('station.tgz',host+':'+base+'/');ssh('cd '+base+' && tar xzf station.tgz')
    with cf.ThreadPoolExecutor(4) as ex:list(ex.map(run,[(m,k) for k in range(5) for m in ('gpt-6.2-sol','gpt-6.1-terra')]))

