"""Run Terra's immutable physics branches on the second CPU host, with frozen model responses."""
import time,subprocess,tarfile
from execute13 import D,HOST,REM,OP,ssh,pull,PY
from decide13 import branches
from summarize13 import run
from pathlib import Path
model='gpt-6.1-terra'
host='assembly-sim-b';opts=['-o','BatchMode=yes','-o','ConnectTimeout=10',]
base='assembly-jobs/kit-runtime';dest=base+'/kit13'
def do(args):subprocess.run(args,cwd=D,check=True)
while not (D/('ready-'+model)).exists():time.sleep(5)
while len(list((D/'responses'/model).glob('*.json')))<500:time.sleep(5)
branches(model)
pack='terra-transfer-states.tar.gz'
ssh('tar czf '+pack+' runs/'+model+'/*/common.npy runs/'+model+'/*/common.json')
do(['scp',*OP,HOST+':'+REM+'/'+pack,pack])
do(['ssh',*opts,host,'mkdir -p '+dest])
do(['scp',*opts,pack,'scenes.json','kit.py','geometry13.py','frame.py','catalog.py','render_kit.py',model+'-plans.json',host+':'+dest+'/'])
py='OPENBLAS_NUM_THREADS=1 '+base+'/env/bin/python'
archive=model+'-results.tar.gz'
do(['ssh',*opts,host,'cd '+dest+' && tar xzf '+pack+' && '+py+' render_kit.py finish '+model+' && tar czf '+archive+' runs/'+model+'/*/results.json'])
do(['scp',*opts,host+':'+dest+'/'+archive,archive])
with tarfile.open(D/archive) as z:z.extractall(D,filter='data')
run(model)
print('Terra replay and paired analysis complete',flush=True)
