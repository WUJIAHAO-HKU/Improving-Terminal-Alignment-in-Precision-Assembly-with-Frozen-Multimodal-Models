from server import primary,grip,evaluate,get,Path
from design import generate
import json,numpy as np
r=generate()[1].copy();r.update(id='QAkey',ta=2.,tx=41.,ty=-17.,sa=-3.,sx=-44.,sy=-2.,other_y=36.,radius=3.1,gap=.9)
primary(r);grip(r,dict(x=r['sx'],y=r['sy'],yaw=r['sa']),'fixture-QA')
pose=dict(x=r['tx'],y=r['ty'],yaw=r['ta']);ang=np.deg2rad(r['ta']);dy=r['other_y']
wrong=dict(x=r['tx']-np.sin(ang)*dy,y=r['ty']+np.cos(ang)*dy,yaw=r['ta'])
evaluate(r,'fixture-QA',dict(compatible=pose,incompatible=wrong))
d=Path('sim/fixture-QA/QAkey');y=get(d/'outcomes.json');z=get(d/'branch-incompatible/02.json')
print(y,flush=True)
assert y['compatible']['ok'] and not y['incompatible']['ok'] and y['incompatible']['height']>9 and min(np.linalg.norm(np.subtract(z['part'][:2],[wrong['x'],wrong['y']])),99)<8
Path('key-commission.json').write_text(json.dumps(dict(scene=r,commands=[pose,wrong],outcomes=y,final_wrong=z['part'])))
