from pathlib import Path
import concurrent.futures as cf,subprocess,sys,json,re,tempfile,shutil,tarfile,time,hashlib
D=Path(__file__).resolve().parent
from station import config
host='assembly-sim-c';base='assembly-jobs/franka-registered-rule15';OP=['-o','BatchMode=yes','-o','ConnectTimeout=10'];py='MUJOCO_GL=egl PYOPENGL_PLATFORM=egl OPENBLAS_NUM_THREADS=1 PYTHONPATH=site-packages python3'
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
                if v['op']=='place':assert type(v['nest']) is int and 0<=v['nest']<4
                else:assert v['socket'] in (0,1)
                return v,raw
            except (ValueError,AssertionError,KeyError,AttributeError):pass
    raise RuntimeError('unusable model reply '+m)
def run(z):
    m,k=z;c=config(k);folder=D/'runs'/f'{m}-{k}';folder.mkdir(parents=True,exist_ok=True);rel=folder.relative_to(D).as_posix()
    def run_cmd(arg):ssh('cd '+base+' && '+py+' episode.py '+str(k)+' '+rel+' '+arg)
    run_cmd('init')
    for j in range(len(c['parts'])+2):
        stem=f'{j:02}';img=folder/('live-'+stem+'.jpg');copy(host+':'+base+'/'+rel+'/'+img.name,str(img));p=c['parts']
        inventory=sorted([(x['nest'],x['stock']) for x in p])
        text=f'You supervise a simulated Franka Panda from this current unmarked camera view and calibrated production records. Product {c["title"]}. The station accepts registered fixture skills. Input inventory (nest ID, stock number) {inventory}. Full BOM in process order '+str([(x['name'],x['stock']) for x in p])+'. No tools. Reply JSON only. '
        if j<len(p):
            text+=f'Operation {j+1}: grasp the stock belonging to {p[j]["name"]}, then place it at its CAD mating column. The runtime uses surveyed nest and fixture coordinates. Choose the nest ID corresponding to that stock. Return {{"op":"place","nest":integer}}.'
        else:
            text+=f'Next controlled tightening operation: use the {"left" if j==len(p) else "right"} flange fastener. Calibrated driver channel 0 is left and channel 1 is right. Return {{"op":"tighten","socket":integer}}.'
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

