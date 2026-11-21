from pathlib import Path
import json,sys,numpy as np
from policy import public,geometry,diff
D=Path(__file__).resolve().parent
def get(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf8')
def prepare(model,stage):
    scenes=get(D/'scenes.json');actions={};choices={}
    for row in scenes:
        i=row['id'];root=D/'initial'/i;r=public(row)
        if stage=='grip':
            actions[i]=get(D/'responses'/model/(i+'-grip.json'))['action'];continue
        a={m:get(D/'responses'/model/(i+'-'+m+'.json'))['action'] for m in ['first','repeat','depth','overhead']}
        g,ok=geometry(root/'00-eye.png',r);gd,okd=geometry(root/'00-eye.png',r,depth=np.load(root/'00-depth.npy'));gt,okt=geometry(root/'00-top.png',r,'top')
        refs={'repeat':g,'depth':gd if okd else g,'overhead':gt if okt else g}
        choices[i]=dict(batch=row['batch'],task=r['task'],pre=diff(a['first'],g,r)/r['gap'] if ok else 1e6,accept={m:diff(a[m],ref,r)<diff(a['first'],ref,r) for m,ref in refs.items()},geometry_visible=ok)
        actions[i]={**a,'geometry':g,'geometry_depth':refs['depth'],'geometry_top':refs['overhead']}
    if stage!='grip':
        for b in sorted({r['batch'] for r in scenes}):
            ids=sorted((i for i in choices if choices[i]['batch']==b),key=lambda i:(-choices[i]['pre'],i))
            for rank,i in enumerate(ids,1):choices[i]['rank']=rank
        save(D/(model+'-choices.json'),choices)
    save(D/(model+'-'+stage+'.json'),actions)
if __name__=='__main__':prepare(*sys.argv[1:])

