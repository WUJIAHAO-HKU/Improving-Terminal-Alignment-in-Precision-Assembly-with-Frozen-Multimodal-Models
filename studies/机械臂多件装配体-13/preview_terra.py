from execute13 import D,ssh,push,PY
from decide13 import read
m='gpt-6.1-terra';c=read(D/(m+'-choices.json'));a=[]
for r in read(D/'scenes.json'):
    i=r['id'];k='overhead' if c[i]['rank']<=4 and c[i]['accept']['overhead'] else 'first'
    v=read(D/'runs'/m/i/'results.json')[k]
    if not v['complete']:a.append((sum(t['ok'] for t in v['events']),len(v['events']),i,k))
_,_,i,k=max(a);print(i,k,flush=True);push(m+'-plans.json',m+'-prefix.json')
ssh(PY+' record_kit.py '+m+' '+i+' '+k)
