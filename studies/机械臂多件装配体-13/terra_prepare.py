"""Prepare the second model's distinct prompts and post-grasp camera views concurrently."""
import time
from execute13 import D,collect,prefix_plan,push,pull,ssh,PY
model='gpt-6.1-terra'
while not (D/'ready-initial').exists():time.sleep(4)
if not (D/('ready-'+model)).exists():
    collect(model,['prefix']);prefix_plan(model);push(model+'-prefix.json')
    ssh(PY+' render_kit.py prefix '+model+' && tar czf '+model+'-prefix.tar.gz runs/'+model+'/*/live-*.jpg runs/'+model+'/*/common.json')
    pull(model+'-prefix.tar.gz');(D/('ready-'+model)).touch()
collect(model,['first','repeat','depth','overhead'])
print('Terra decisions acquired',flush=True)
