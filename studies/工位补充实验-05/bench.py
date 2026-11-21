"""Measure workstation software stages and replay all alternatives from the same initial state."""
from time import perf_counter
import sys
import numpy as np
from server import samples, Rig, TASKS, GAPS, W, D, read, dump
from PIL import Image
def main():
    stage=sys.argv[1];rows=samples();result=[];timing=[]
    if stage=='score': actions=read('actions.json')
    for task in TASKS:
        for gap in GAPS:
            rig=Rig(task,gap)
            relevant=[r for r in rows if r['task']==task and r['gap']==gap]
            if not relevant:continue
            if stage=='render':
                rig.pose(relevant[0])
                rig.s.render(width=W,height=W,camera_name=rig.cam_name,depth=False)
                rig.render(relevant[0])
            for r in relevant:
                if stage=='render':
                    start=perf_counter();rig.pose(r)
                    rgb=rig.s.render(width=W,height=W,camera_name=rig.cam_name,depth=False)[::-1].copy()
                    rgb_seconds=perf_counter()-start
                    start=perf_counter();r['depth']=rig.render(r);depth_seconds=perf_counter()-start
                    # The timed extra capture includes pose reset, RGB-D capture, plane extraction and JPEG I/O.
                    result.append(r);timing.append(dict(id=r['id'],rgb_s=rgb_seconds,rgbd_s=depth_seconds))
                else:
                    for mode,a in actions[r['id']].items():
                        start=perf_counter();score=rig.rollout(r,*a)
                        result.append(dict(id=r['id'],mode=mode,replay_s=perf_counter()-start,**score))
            rig.e.close()
            print(stage,task,gap,len(result),flush=True)
    if stage=='render':
        dump('manifest.json',result);dump('capture-times.json',timing)
    else:dump('scores.json',result)
if __name__=='__main__': main()
