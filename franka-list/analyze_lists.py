"""Rebuild the locked estimands from individual Franka branch receipts and rank files."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.stats import t

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def write_rows(path, rows):
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def interval(values,level=.95):
    v=np.asarray(values,dtype=float)
    assert len(v)==64
    mean=float(v.mean());half=float(t.ppf((1+level)/2,63)*v.std(ddof=1)/8)
    return mean,mean-half,mean+half

def analyze(src,output):
    root=src/'formal'; rec=root/'records'
    cfg=read(root/'lock.json')
    assert hashlib.sha256((root/'lock.json').read_bytes()).hexdigest()=='1cd52959af21e1ebf57cfded179e1cd4f415161c7ae064cad9fba3232b7fafc9'
    gains=read(src/'commissioning/vendor/handoff/gain.json'); lists=('random','family','combined')
    arms=[];parts=[];batches=[];effects=[];overlaps=[]
    for model in cfg['models']:
        for b in range(cfg['batches']):
            ranks=read(rec/'rankings'/model/f'{b:02}.json')
            chosen={k:set(ranks['lists'][k]) for k in lists}
            ids=[f'L{i:03}' for i in range(5*b,5*b+5)]
            perm=np.random.default_rng(np.random.SeedSequence([cfg['allocation_seed'],b])).permutation(ids)
            assert chosen['random']==set(perm[:4])
            public={i:read(rec/i/'public.json') for i in ids}
            family=sorted(ids,key=lambda i:(-gains['four_'+model][public[i]['task']],i))
            assert chosen['family']==set(family[:4])
            assert chosen['combined']=={i for i in ids if ranks['new-4'][i]['measure']}
            assert all(len(s)==4 and s.issubset(ids) for s in chosen.values())
            overlaps.append(dict(model=model,batch=b,identical_family_combined=int(chosen['family']==chosen['combined']),identical_random_combined=int(chosen['random']==chosen['combined'])))
            cases=[]
            for i in ids:
                p=rec/i/model
                a,c=[read(p/br/'receipt.json') for br in ('first','overhead')]
                for item,br in [(a,'first'),(c,'overhead')]:
                    assert item['scene_id']==i and item['batch_id']==b and item['model']==model and item['branch']==br
                assert a['checkpoint_id']==c['checkpoint_id']==read(p/'grip.json')['checkpoint_id']
                g=read(p/'gates.json')['gates']['new']['selected'];assert g in ('first','overhead')
                y0=int(a['success']);y1=int(c['success'])
                part=dict(model=model,batch=b,scene=i,task=public[i]['task'],gap=public[i]['gap'],lifted=int(a['lifted']),first=y0,overhead=y1,selected=g,first_failure=a['failure_stage'],overhead_failure=c['failure_stage'],**{k:int(i in chosen[k]) for k in lists})
                parts.append(part);cases.append(part)
            for gate in ['switch','retain']:
                def branch(r):
                    return r['overhead'] if gate=='switch' or r['selected']=='overhead' else r['first']
                expected=sum(r['first']+.8*(branch(r)-r['first']) for r in cases)
                for k in lists:
                    wins=sum(branch(r) if r[k] else r['first'] for r in cases)
                    rescue=sum(r[k] and r['selected']=='first' and r['first']==1 and r['overhead']==0 for r in cases)
                    harm=sum(r[k] and r['selected']=='first' and r['first']==0 and r['overhead']==1 for r in cases)
                    batches.append(dict(model=model,batch=b,gate=gate,policy=k,success=wins,random_expected=expected,rescued=rescue,harmed=harm))
        bs=[r for r in batches if r['model']==model]
        vals={}
        def effect(name,v,primary=False):
            mean,lo,hi=interval(v)
            _,slo,shi=interval(v,.975)
            effects.append(dict(model=model,contrast=name,extra_per100=mean,low95=lo,high95=hi,sim_low=slo if primary else '',sim_high=shi if primary else ''))
        for gate in ['switch','retain']:
            for k in lists:
                rows=[r for r in bs if r['gate']==gate and r['policy']==k]
                v=np.array([r['success'] for r in rows])*20;vals[k,gate]=v
                arms.append(dict(model=model,gate=gate,policy=k,success=sum(r['success'] for r in rows),starts=320,rate_per100=v.mean(),rescued=sum(r['rescued'] for r in rows) if gate=='retain' else 0,harmed=sum(r['harmed'] for r in rows) if gate=='retain' else 0))
            for l,r in [('combined','random'),('family','random'),('combined','family')]:
                effect(f'{gate}:{l}-{r}',vals[l,gate]-vals[r,gate],gate=='switch' and l=='combined' and r=='random')
            exp=np.array([r['random_expected'] for r in rows])*20
            for k in ('combined','family'):
                effect(f'{gate}:{k}-expected_random',vals[k,gate]-exp)
        for k in lists:
            effect(f'{k}:retain-switch',vals[k,'retain']-vals[k,'switch'])
        effect('interaction:(combined-random)x(retain-switch)',(vals['combined','retain']-vals['random','retain'])-(vals['combined','switch']-vals['random','switch']))
    output.mkdir(exist_ok=True,parents=True)
    for filename,data in [('parts',parts),('batch',batches),('effects',effects),('arms',arms),('overlap',overlaps)]:
        write_rows(output/(filename+'.csv'),data)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('source',type=Path);ap.add_argument('output',type=Path);args=ap.parse_args()
    analyze(args.source,args.output)
