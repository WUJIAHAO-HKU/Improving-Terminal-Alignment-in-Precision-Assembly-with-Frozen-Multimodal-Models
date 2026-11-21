from pathlib import Path
import subprocess,sys,tarfile,json,hashlib,shutil
from concurrent.futures import ThreadPoolExecutor
D=Path.cwd();kit=D.name=='kits';sys.path.insert(0,str(D));import decide15
EB='assembly-sim-c';host=EB if kit else 'assembly-sim-a'
op=['-o','BatchMode=yes','-o','ConnectTimeout=10']
base='assembly-jobs'+'/closed-loop-rule15-'+D.name
py=('PYTHONPATH=site-packages python3' if kit else 'python3')
py='MUJOCO_GL=egl PYOPENGL_PLATFORM=egl OPENBLAS_NUM_THREADS=1 '+py
def do(cmd):subprocess.run(cmd,check=True,cwd=D)
def ssh(cmd):do(['ssh',*op,host,'cd '+base+' && '+cmd])
def push(*fs):do(['scp','-q',*op,*fs,host+':'+base+'/'])
def fetch(tag,files):
    ssh('tar czf '+tag+'.tgz '+files)
    do(['scp','-q',*op,host+':'+base+'/'+tag+'.tgz',tag+'.tgz'])
    with tarfile.open(D/(tag+'.tgz')) as z:z.extractall(D,filter='data')
def model(m):
    prefix='prefix' if kit else 'grip'
    if kit:from collect13 import collect,prefix_plan
    else:from collect12 import collect
    if not (D/('seen-'+m)).exists():
        collect(m,[prefix])
        if kit:prefix_plan(m)
        else:
            gr={r['id']:decide15.read(D/'responses'/m/(r['id']+'-grip.json'))['action'] for r in rows};decide15.save(m+'-grip.json',gr)
        push(m+'-'+prefix+'.json');ssh(py+' '+('render_kit.py' if kit else 'server.py')+' '+prefix+' '+m)
        fetch(m+'-live',('runs/'+m+'/*/live-*.jpg runs/'+m+'/*/common.json') if kit else 'sim/'+m+'/*/01-eye.png sim/'+m+'/*/grip.json')
        (D/('seen-'+m)).touch()
    print(m,'live feedback to model',flush=True);collect(m,['first','overhead']);decide15.make(m,kit)
    last='finish' if kit else 'evaluate';push(m+('-plans.json' if kit else '-evaluate.json'))
    print(m,'physical placement',flush=True);ssh(py+' '+('render_kit.py' if kit else 'server.py')+' '+last+' '+m)
    fetch(m+'-out',('runs/'+m+'/*/results.json') if kit else 'sim/'+m+'/*/outcomes.json')
    print(m,'done',flush=True)
lock=decide15.read('lock.json')
for n,h in lock['sha256'].items():assert hashlib.sha256((D/n).read_bytes()).hexdigest()==h,n
if kit:from scenes13 import cohort as design
else:from design import generate as design
rows=design();decide15.save('scenes.json',rows)
do(['ssh',*op,host,'mkdir -p '+base])
push(*[p.name for p in D.glob('*.py')],'scenes.json','lock.json')
if not (D/'prepared').exists():
    ssh(py+' '+('render_kit.py' if kit else 'server.py')+' prepare')
    fetch('initials','observations' if kit else 'initial/*/00-*.png')
    (D/'prepared').touch()
print('initial views ready',flush=True)
with ThreadPoolExecutor(2) as pool:list(pool.map(model,['gpt-6.2-sol','gpt-6.1-terra']))


