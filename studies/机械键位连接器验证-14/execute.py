"""Resumable batch acquisition, CPU-safe GPU physics workers and result synchronization."""
from pathlib import Path
import subprocess,sys,tarfile,json,hashlib
from collect12 import collect
from decisions import prepare
from analyze import main as analyze
# NumPy/OpenCV on Windows cannot open non-ASCII absolute names. Use paths relative to this directory, leaving locked geometry and actions unchanged.
import decisions
decisions.D=Path('.')
D=Path(__file__).resolve().parent; REM='assembly-jobs/arm-keyed-Kq439R';HOST='assembly-sim-a'
opts=['-o','BatchMode=yes','-o','ConnectTimeout=12',]
def do(cmd):subprocess.run(cmd,check=True,cwd=D)
def ssh(cmd):do(['ssh',*opts,HOST,'cd '+REM+' && '+cmd])
def push(*names):do(['scp',*opts,*names,HOST+':'+REM+'/'])
def pull(name):do(['scp',*opts,HOST+':'+REM+'/'+name,str(D/name)])
def untar(name):
    with tarfile.open(D/name,'r:gz') as z:z.extractall(D,filter='data')
def main():
    from design import generate
    lock=json.loads((D/'lock.json').read_text(encoding='utf8'))
    for n,h in lock['sha256'].items():assert hashlib.sha256((D/n).read_bytes()).hexdigest()==h,n
    if not (D/'scenes.json').exists():(D/'scenes.json').write_text(json.dumps(generate(),indent=2),encoding='utf8')
    push('gantry.py','profiles.py','server.py','design.py','scenes.json','lock.json')
    py='WORKERS=2 MUJOCO_GL=egl PYOPENGL_PLATFORM=egl OPENBLAS_NUM_THREADS=1 python3'
    if not (D/'ready-init').exists():
        print('prepare starts',flush=True);ssh(py+' server.py prepare && tar czf initial.tar.gz initial/*/00-eye.png initial/*/00-top.png initial/*/00-depth.png initial/*/00-depth.npy')
        pull('initial.tar.gz');untar('initial.tar.gz');(D/'ready-init').touch()
    for model in ['gpt-6.2-sol','gpt-6.1-terra']:
        if (D/(model+'-summary.json')).exists():continue
        if not (D/('ready-grip-'+model)).exists():
            print('grasp decisions',model,flush=True);collect(model,['grip']);prepare(model,'grip');push(model+'-grip.json')
            ssh(py+' server.py grip '+model+' && tar czf '+model+'-grips.tar.gz sim/'+model+'/*/01-eye.png sim/'+model+'/*/grip.json')
            pull(model+'-grips.tar.gz');untar(model+'-grips.tar.gz');(D/('ready-grip-'+model)).touch()
        print('alignment decisions',model,flush=True)
        if model=='gpt-6.1-terra' and (D/'terra-prefetch.log').exists():
            import time
            for _ in range(180):
                if len(list((D/'responses'/model).glob('*.json')))>=500:break
                time.sleep(5)
        collect(model,['first','repeat','depth','overhead']);prepare(model,'evaluate');push(model+'-evaluate.json',model+'-choices.json')
        ssh(py+' server.py evaluate '+model+' && tar czf '+model+'-outcomes.tar.gz sim/'+model+'/*/outcomes.json')
        pull(model+'-outcomes.tar.gz');untar(model+'-outcomes.tar.gz');analyze(model);print('complete',model,flush=True)
if __name__=='__main__':main()

