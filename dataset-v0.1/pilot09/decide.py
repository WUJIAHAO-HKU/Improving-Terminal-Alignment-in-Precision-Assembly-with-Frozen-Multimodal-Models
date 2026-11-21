from pathlib import Path
import json,hashlib
from PIL import Image
import numpy as np
from policy import target,err
D=Path(__file__).resolve().parent
rows=json.loads((D/'scenes.json').read_text())
out={}; choices={}
for r in rows:
    i=r['id'];task=r['task']
    act={k:json.loads((D/'responses'/f'{i}-{k}.json').read_text())['action'] for k in ('rgb','view','repeat')}
    g={k:target(np.asarray(Image.open(D/'frames'/f'{i}-{k}.png').convert('RGB')),p,task) for k,p in [('rgb',r['pitch']),('top',0)]}
    post=g['top'] if g['top'] is not None else g['rgb']
    def prefer(candidate,ref):return err(act[candidate],ref,task)<err(act['rgb'],ref,task)
    out[i]={**act,'geo':g['rgb'] if g['rgb'] is not None else [0]*3,'geo_top':post if post is not None else [0]*3}
    choices[i]=dict(batch=r['batch'],priority=err(act['rgb'],g['rgb'],task)/r['gap'],view=prefer('view',post),repeat=prefer('repeat',g['rgb']),geometry_valid={k:v is not None for k,v in g.items()})
for b in range(6):
    seq=sorted((i for i in choices if choices[i]['batch']==b),key=lambda i:(-choices[i]['priority'],i))
    for rank,i in enumerate(seq,1):
        choices[i]['rank']=rank
        if not np.isfinite(choices[i]['priority']):choices[i]['priority']=None
for fname,obj in [('actions',out),('choices',choices)]:
    (D/(fname+'.json')).write_text(json.dumps(obj,indent=2,allow_nan=False),encoding='utf8')

