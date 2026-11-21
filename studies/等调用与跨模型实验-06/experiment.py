"""Locked Sol information ablation and zero-shot transfer on the original 300 scenes."""
import hashlib
import json
import sys
from pathlib import Path
import numpy as np

D=Path(__file__).resolve().parent
P=D.parent/'工位补充实验-05'
sys.path.insert(0,str(P))
from rules4 import pre,post,quality,forecast,fit,read,sha
from policy5 import stream
SOL='gpt-6.2-sol'
TARGETS=['gpt-6.1-terra','gpt-6-luna']
def save(n,obj):
    (D/n).write_text(json.dumps(obj,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf8')
def lock():
    prev=read(P/'before-replay.json')
    assert all(sha(P/n)==v for n,v in prev.items())
    prior=read(P/'decisions.json')
    selected=[b['selections']['8']['stream_natural'] for b in prior['batches']]
    assert len(selected)==30 and all(len(set(z))==8 for z in selected)
    ids=set(i for group in selected for i in group)
    assert len(ids)==240
    frozen=read(P/'policy-lock.json')
    x=[];y=[]
    for name in ['独立测量策略实验-02','风险感知动作接受实验-03']:
        root=P.parent/name
        for r in read(root/'case-outcomes.json'):
            action=r['scores']['direct']['action']
            x.append(pre(r,quality(root/'frames'/(r['id']+'.jpg')),action,frozen['limit']))
            y.append(int(r['scores']['direct']['success']))
    save('lock.json',dict(models=TARGETS,primary='stream_natural',selected=selected,
        rgb_model=fit(np.asarray(x),np.asarray(y)),limit=frozen['limit'],
        hashes={str(p):sha(p) for p in [P/'before-replay.json',P/'policy-lock.json',P/'study-lock.json',P/'model_client.py',P/'actions.json',D/'protocol.txt',D/'experiment.py',D/'collect.py']},
        frames={i:sha(P/'frames'/(i+'.jpg')) for i in prior['items']}))
def decide():
    l=read(D/'lock.json');assert all(sha(Path(p))==h for p,h in l['hashes'].items())
    w=read(P/'policy-lock.json');ref=read(P/'study-lock.json')['ref']
    old=read(P/'actions.json');prev=read(P/'decisions.json')
    selected={i for group in l['selected'] for i in group}
    rows=sorted(read(P/'manifest.json'),key=lambda r:(r['batch'],r['k']))
    acts={};vs={}; masks={};base=P/'responses'
    def response(i,m,mode):
        src=D/'responses'/f'{i}--{m}--{mode}.json'
        v=read(src)
        reference=read(base/f"{i}--{SOL}--{'measured' if mode=='measured' else 'direct'}.json")
        assert v['model']==m and v['mode']==mode and v['id']==i and v['prompt']==reference['prompt']
        return v['action']
    for r in rows:
        i=r['id'];assert sha(P/'frames'/(i+'.jpg'))==l['frames'][i]
        q=quality(P/'frames'/(i+'.jpg'));lim=l['limit']
        acts[i]=dict(original=old[i]['direct'],depth=old[i]['always']);vs[i]={}
        if i in selected:
            second=response(i,SOL,'repeat');acts[i]['repeat']=second
            def rgbscore(a):
                # Input whitelist: gap, angle, task, RGB quality, and this RGB candidate.
                obs={k:r[k] for k in ('task','angle','gap')}
                return float(forecast(l['rgb_model'],pre(obs,q,a,lim)))
            d=rgbscore(acts[i]['original'])
            vs[i]['rgb_accept']=rgbscore(second)>d
            vs[i]['shared_depth_accept']=rgbscore(acts[i]['depth'])>d
        vs[i]['depth_accept']=prev['items'][i]['accept']
        for m in TARGETS:
            a=response(i,m,'direct');z=response(i,m,'measured')
            acts[i][m+'_d']=a;acts[i][m+'_m']=z
            vs[i][m]=dict(score=float(forecast(w['pre'],pre(r,q,a,lim))),
                accept=bool(forecast(w['post'],post(r,q,a,z,lim))>0))
    for m in TARGETS:
        v={i:vs[i][m] for i in vs};masks[m]={}
        for k in [8,6]:
            masks[m][str(k)]=[stream(b['orders']['natural'],v,k,ref) for b in prev['batches']]
    assert len(list((D/'responses').glob('*.json')))==1440
    save('actions.json',acts);save('gates.json',vs);save('masks.json',masks)
    save('locked-before-replay.json',{n:sha(D/n) for n in ['actions.json','gates.json','masks.json','lock.json']})
if __name__=='__main__':{'lock':lock,'decide':decide}[sys.argv[1]]()
