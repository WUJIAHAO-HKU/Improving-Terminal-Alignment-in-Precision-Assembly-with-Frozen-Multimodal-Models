"""Save anonymized oblique views of known poses and final states for independent visual inspection."""
import sys
from server import *
rng=random.Random(7801)
items=[];kind=sys.argv[1]
if kind=='failures': items=read('to_capture.json')
else:
    for task in TASKS:
        for gap in [4,1,.25]:
            for label in ['seated','hover','partial','tilted','miss']:
                items.append(dict(task=task,gap=gap,label=label))
    rng.shuffle(items)
for task in TASKS:
    for g in sorted({v['gap'] for v in items if v['task']==task}):
        rig=Rig(task,g)
        for i,item in enumerate(items):
            if item['task']!=task or item['gap']!=g:continue
            r=next(r for r in samples() if r['task']==task and r['gap']==g and (r['id']==item['id'] if kind=='failures' else r['split']=='test'))
            if kind=='failures':
                rig.rollout(r,*item['action'])
            else:
                lab=item['label'];at_base=-.032 if rig.dual else rig.e.table_offset[2]+.010-rig.center[2]
                h={'seated':at_base,'hover':.030,'partial':-.012,'tilted':.010,'miss':at_base}[lab]
                rig.pose(r,(80 if lab=='miss' else 0)-r['x'],-r['y'],h,.22 if lab=='tilted' else 0)
            s=rig.s
            dest=D/('failure_views' if kind=='failures' else 'audit_views');dest.mkdir(exist_ok=True)
            fig=Image.new('RGB',(480,240))
            for panel,deg in enumerate([10,66]):
                a=math.radians(deg);dist=.55 if rig.dual else .44
                aim=rig.center.copy();aim[2]-=.018 if rig.dual else .063
                s.model.cam_pos[rig.cam]=aim+[0,-dist*np.sin(a),dist*np.cos(a)];s.model.cam_quat[rig.cam]=[np.cos(a/2),np.sin(a/2),0,0];s.forward()
                img=s.render(width=240,height=240,camera_name=rig.cam_name)[::-1].copy()
                fig.paste(Image.fromarray(img),(240*panel,0))
            fig.save(dest/f'{i:02d}.jpg',quality=93)
        rig.e.close()
dump('failure_views.json' if kind=='failures' else 'audit_key.json',items)

