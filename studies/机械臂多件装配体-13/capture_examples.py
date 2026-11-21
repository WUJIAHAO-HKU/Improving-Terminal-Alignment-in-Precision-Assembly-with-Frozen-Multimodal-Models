from execute13 import D,OP,REM,HOST,PY,ssh,push,pull
from decide13 import read
from catalog import RECIPES
import time,json
from pathlib import Path
def main():
    models=['gpt-6.2-sol','gpt-6.1-terra']
    while not all((D/(m+'-summary.json')).exists() for m in models):time.sleep(5)
    scenes=read(D/'scenes.json');selected=[]
    push('record_kit.py')
    for m in models:
        cs=read(D/(m+'-choices.json'));arr=[]
        for r in scenes:
            i=r['id'];ch=cs[i];mode='overhead' if ch['rank']<=4 and ch['accept']['overhead'] else 'first'
            v=read(D/'runs'/m/i/'results.json')[mode]
            arr.append((v['complete'],len(v['events']),sum(t['ok'] for t in v['events']),i,mode,r))
        success=(m==models[0]);sub=[v for v in arr if v[0]==success]
        if not sub:sub=arr
        a=max(sub,key=lambda w:(w[2],w[1],w[3]));_,_,_,i,mode,r=a
        push(m+'-plans.json',m+'-prefix.json')
        ssh(PY+' record_kit.py '+m+' '+i+' '+mode)
        selected.append(dict(id=i,model=m,mode=mode,recipe=r['recipe']))
    ssh('tar czf kit-recordings.tar.gz recordings');pull('kit-recordings.tar.gz')
    for case in selected:
        m,i,mode=case['model'],case['id'],case['mode']
        actual=read(D/'recordings'/(m+'-'+i)/'replay.json');raw=read(D/'runs'/m/i/'results.json')[mode]
        assert actual['final']==raw['final'] and [v['ok'] for v in actual['events']]==[v['ok'] for v in raw['events']]
        assert all(abs(a['height']-b['height'])<.02 for a,b in zip(actual['events'],raw['events']))
    (D/'recordings/selected.json').write_text(json.dumps(selected,indent=2),encoding='utf8')
if __name__=='__main__':main()
