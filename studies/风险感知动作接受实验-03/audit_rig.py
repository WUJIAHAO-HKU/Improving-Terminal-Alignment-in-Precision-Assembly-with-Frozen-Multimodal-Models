"""Verify state reset and image reproduction before scoring held-out actions."""
from pathlib import Path
from tempfile import TemporaryDirectory
import os
import hashlib
from server import Rig, samples, TASKS, GAPS, dump, read

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    root=Path.cwd()
    manifest={r['id']:r for r in read('manifest.json')}
    output=[]
    with TemporaryDirectory(dir=root) as tmp:
        os.chdir(tmp)
        Path('frames').mkdir()
        try:
            for task in TASKS:
                for gap in GAPS:
                    rig=Rig(task,gap)
                    r=next(r for r in samples() if r['task']==task and r['gap']==gap)
                    path=Path('frames')/(r['id']+'.jpg')
                    depth=rig.render(r)
                    same_frame=digest(path)==digest(root/path)
                    same_depth=manifest[r['id']]['depth']==depth
                    ideal=(-r['x'],-r['y'])
                    first=rig.rollout(r,*ideal)
                    miss=rig.rollout(r,80-r['x'],-r['y'])
                    repeat=rig.rollout(r,*ideal)
                    output.append(dict(id=r['id'],task=task,gap=gap,frame=same_frame,depth=same_depth,
                                       repeat=first==repeat,ideal=first['success'],miss=miss['success']))
                    rig.e.close()
        finally:
            os.chdir(root)
    dump('rig-audit.json',output)
    assert all(r['frame'] and r['depth'] and r['repeat'] and not r['miss'] for r in output)
if __name__=='__main__':main()
