from cell import *
r=dict(tx=41,ty=7,ta=4,sx=-46,sy=-9,sa=-8,gap=1,pitch_mm=30)
acts=[dict(op='observe'),dict(op='pick',x=-46,y=-9,yaw=-8),dict(op='carry',x=41,y=7,yaw=4,z=35),dict(op='insert'),dict(op='release')]
for i,act in enumerate(acts):
 c=Cell(r,Path('commission'),i);c.apply(act);s=c.finish()
 print(i,s['part'],s['seat'],s['contacts'],s['arm'],sum(v['left'] and v['right'] for v in s['trace']),flush=True)

