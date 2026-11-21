from pathlib import Path
from collections import Counter
import json
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
D=Path(__file__).resolve().parent
def get(k):return json.loads((D/(k+'.json')).read_text(encoding='utf-8-sig'))
rows=get('scenes');ch=get('choices');scores={s['id']:s for s in get('scores')}
def pick(c,mode,k,gate):
    if c['rank']>k or gate and not c[mode]:return 'rgb'
    return mode
out={}; examples=[]
cols=['rgb','repeat4','repeat4gate','view4','view4gate','view3gate','allview','allgate','geo','geo_top','zero','oracle']
for r in rows:
    i=r['id'];c=ch[i];s=scores[i];v={'rgb':s['rgb']['ok'],'zero':r['zero']['ok'],'oracle':r['oracle']['ok'],'geo':s['geo']['ok'],'geo_top':s['geo_top']['ok']}
    for label,mode,k,gate in [('repeat4','repeat',4,False),('repeat4gate','repeat',4,True),('view4','view',4,False),('view4gate','view',4,True),('view3gate','view',3,True),('allview','view',5,False),('allgate','view',5,True)]:
        v[label]=s[pick(c,mode,k,gate)]['ok']
    out[i]=v
    if not v['rgb'] or not v['view4gate']:
        examples.append(dict(id=i,task=r['task'],gap=r['gap'],rank=c['rank'],accepted=c['view'],initial_yaw=r['yaw'],rgb=s['rgb'],view=s['view']))
summary={}
for task in ['twin','blade','dshaft','total']:
    ids=[r['id'] for r in rows if task=='total' or r['task']==task]
    summary[task]={k:sum(out[i][k] for i in ids) for k in cols}
    summary[task]['n']=len(ids)
summary['equal_budget']={'selected':sum(c['rank']<=4 for c in ch.values()),'switches':sum(c['rank']<=4 and c['view'] for c in ch.values()),'depth_oracle_controls':'overhead RGB is the acquired view; no depth channel in pilot.'}
summary['failure_examples']=examples
(D/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf8')
fig,axes=plt.subplots(2,3,figsize=(7.2,4.6),layout='constrained')
for j,(task,title) in enumerate([('twin','Twin dowels'),('blade','Blade and slot'),('dshaft','D-shaft and sleeve')]):
    r=next(r for r in rows if r['task']==task)
    for ax,cam in zip(axes[:,j],['rgb','top']):
        ax.imshow(Image.open(D/'frames'/f"{r['id']}-{cam}.png"));ax.set_xticks([]);ax.set_yticks([])
        if cam=='rgb':ax.set_title(title,fontsize=11)
        if j==0:ax.set_ylabel('Initial view' if cam=='rgb' else 'Extra view')
fig.savefig(D.parent/'JMS论文/figures/fig7-orientation.pdf',bbox_inches='tight');plt.close(fig)
print({k:summary[k] for k in ('twin','blade','dshaft','total')})

