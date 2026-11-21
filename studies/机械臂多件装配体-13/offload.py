"""Retrieve first-component checkpoint data and distribute exact replay, without new model requests."""
from execute13 import D,ssh,REM,OP,HOST
from summarize13 import run
import subprocess,sys,time,tarfile
from pathlib import Path
model=sys.argv[1];n=sys.argv[2]
EB='assembly-sim-c';dest='assembly-jobs/kits';sc=['scp','-q','-o','BatchMode=yes','-P','22'];sh=['ssh','-o','BatchMode=yes',EB]
def do(a):subprocess.run(a,cwd=D,check=True)
while not (D/('ready-'+model)).exists():time.sleep(5)
pack=model+'-checkpoint.tar.gz'
ssh('tar czf '+pack+' runs/'+model+'/*/common.npy runs/'+model+'/*/live-depth.npy runs/'+model+'/*/common.json')
do(['scp',*OP,HOST+':'+REM+'/'+pack,pack])
with tarfile.open(D/pack) as z:z.extractall(D,filter='data')
do(sc+[pack,'kit.py','geometry13.py','frame.py','catalog.py','render_kit.py','scenes.json','batch_fast.py',EB+':'+dest+'/'])
do(sh+['cd '+dest+' && tar xzf '+pack])
while not (D/(model+'-plans.json')).exists():time.sleep(5)
do(sc+[model+'-plans.json',EB+':'+dest+'/'])
py='OPENBLAS_NUM_THREADS=1 PYTHONPATH='+dest+'/env python3'
archive=model+'-EB-results.tar.gz'
do(sh+['cd '+dest+' && '+py+' batch_fast.py '+model+' '+n+' && tar czf '+archive+' runs/'+model+'/*/results.json'])
do(sc+[EB+':'+dest+'/'+archive,archive])
with tarfile.open(D/archive) as z:z.extractall(D,filter='data')
run(model);print('verified finished EB',model,flush=True)
