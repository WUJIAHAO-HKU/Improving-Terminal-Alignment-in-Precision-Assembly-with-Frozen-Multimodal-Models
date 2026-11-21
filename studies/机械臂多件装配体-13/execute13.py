from pathlib import Path
import json,hashlib,subprocess,tarfile,sys
from collect13 import collect,prefix_plan
from decide13 import branches
from summarize13 import run
from scenes13 import cohort
D=Path(__file__).resolve().parent;REM='assembly-jobs/arm-kits';HOST='assembly-sim-a'
OP=['-o','BatchMode=yes','-o','ConnectTimeout=10',]
PY='MUJOCO_GL=egl PYOPENGL_PLATFORM=egl OPENBLAS_NUM_THREADS=1 python3'
def do(cmd):subprocess.run(cmd,cwd=D,check=True)
def ssh(s):do(['ssh',*OP,HOST,'cd '+REM+' && '+s])
def push(*names):do(['scp',*OP,*names,HOST+':'+REM+'/'])
def pull(k):
    do(['scp',*OP,HOST+':'+REM+'/'+k,k])
    with tarfile.open(D/k,'r:gz') as z:z.extractall(D,filter='data')
def main():
    lock=json.loads((D/'lock.json').read_text());assert all(hashlib.sha256((D/n).read_bytes()).hexdigest()==v for n,v in lock['sha256'].items())
    commissioned=json.loads((D/'commission-layout2.json').read_text());assert len(commissioned)==20 and all(all(r['ok'] for r in v['components']) and all(v['final']) for v in commissioned.values())
    if not (D/'scenes.json').exists():(D/'scenes.json').write_text(json.dumps(cohort(),indent=2),encoding='utf8')
    if not (D/'ready-initial').exists():
        push('kit.py','catalog.py','frame.py','geometry13.py','render_kit.py','scenes.json','lock.json');print('render',flush=True)
        ssh(PY+' render_kit.py prepare && tar czf kit-initial.tar.gz observations');pull('kit-initial.tar.gz');(D/'ready-initial').touch()
    for model in ['gpt-6.2-sol','gpt-6.1-terra']:
        if (D/(model+'-summary.json')).exists():continue
        if not (D/('ready-'+model)).exists():
            print('first stage',model,flush=True);collect(model,['prefix']);prefix_plan(model);push(model+'-prefix.json')
            ssh(PY+' render_kit.py prefix '+model+' && tar czf '+model+'-prefix.tar.gz runs/'+model+'/*/live-*.jpg runs/'+model+'/*/common.json')
            pull(model+'-prefix.tar.gz');(D/('ready-'+model)).touch()
        print('remaining recipe',model,flush=True);collect(model,['first','repeat','depth','overhead']);branches(model);push(model+'-plans.json',model+'-choices.json')
        ssh(PY+' render_kit.py finish '+model+' && tar czf '+model+'-results.tar.gz runs/'+model+'/*/results.json')
        pull(model+'-results.tar.gz');run(model);print('finished',model,flush=True)
if __name__=='__main__':main()

