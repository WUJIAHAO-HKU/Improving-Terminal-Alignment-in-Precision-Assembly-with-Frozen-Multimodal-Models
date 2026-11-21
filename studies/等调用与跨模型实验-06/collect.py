"""Same client and scene prompts as round 05, isolated output directory."""
import concurrent.futures
import random
import sys
from collections import Counter
from experiment import D,P,read,SOL,TARGETS
import model_client as client

def main():
    l=read(D/'lock.json')
    client.responses=D/'responses';client.responses.mkdir(exist_ok=True)
    selected={i for group in l['selected'] for i in group}
    jobs=[(r,mode,model) for r in client.rows for model in TARGETS for mode in ('direct','measured')]
    jobs += [(r,'repeat',SOL) for r in client.rows if r['id'] in selected]
    if len(sys.argv)>1: jobs=[j for j in jobs if j[2]==sys.argv[1]]
    rng=random.Random(61611);rng.shuffle(jobs)
    jobs=[j for j in jobs if not client.resp(*j).exists()]
    failures=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        futures={pool.submit(client.predict,j):j for j in jobs}
        for n,done in enumerate(concurrent.futures.as_completed(futures),1):
            j=futures[done]
            try: done.result()
            except Exception as e:
                failures.append((j[0]['id'],j[1],j[2],type(e).__name__,str(e)[-450:]))
                if len(failures)<=3: print('failed',failures[-1],flush=True)
            if n%20==0:print(n,'/',len(jobs),'errors',len(failures),flush=True)
    if failures:
        from experiment import save
        save('request-failures.json',failures)
        raise RuntimeError(str(len(failures))+' requests missing')
if __name__=='__main__':main()
