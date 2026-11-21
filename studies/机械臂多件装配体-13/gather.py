"""Synchronize completed independent evaluations on two worker hosts. Deduplicate by (model, scene)."""
from execute13 import D,REM,OP,HOST
from summarize13 import run
from decide13 import read
from pathlib import Path
import subprocess,tarfile,time,json
M=['gpt-6.2-sol','gpt-6.1-terra'];EB='assembly-sim-c';kit='assembly-jobs/kits'
sources=[(HOST,'22',OP,REM,M[:1]),('assembly-sim-b','22',['-o','BatchMode=yes',],'assembly-jobs/kit-runtime/kit13',M[1:]),(EB,'22',['-o','BatchMode=yes'],kit,M)]
def main():
    counts={}
    while not all((D/(m+'-summary.json')).exists() for m in M):
        for host,port,op,base,models in sources:
            for m in models:
                if (D/(m+'-summary.json')).exists():continue
                ssh=['ssh',*op,'-p',port,host];cmd="cd "+base+" && find runs/"+m+" -name results.json"
                ls=subprocess.run(ssh+[cmd],capture_output=True,text=True,check=True).stdout.splitlines()
                unseen=[s for s in ls if not (D/s).exists()]
                if not unseen:continue
                temp='partial-'+port+'-'+m+'.tgz'
                subprocess.run(ssh+['cd '+base+' && tar czf '+temp+' '+' '.join(unseen)],check=True)
                subprocess.run(['scp','-q',*op,'-P',port,host+':'+base+'/'+temp,str(D/temp)],check=True)
                with tarfile.open(D/temp) as z:z.extractall(D,filter='data')
                n=sum(1 for p in (D/'runs'/m).glob('*/results.json'))
                if counts.get(m)!=n:print(m,n,flush=True);counts[m]=n
                if n==100:run(m)
        if not all((D/(m+'-summary.json')).exists() for m in M):time.sleep(25)
if __name__=='__main__':main()
