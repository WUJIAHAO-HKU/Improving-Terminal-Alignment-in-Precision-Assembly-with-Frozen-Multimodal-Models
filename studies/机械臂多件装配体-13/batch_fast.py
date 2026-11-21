"""Replay locked robot commands from a restored post-first state, scheduling long recipes first."""
from render_kit import replay
from catalog import RECIPES
from pathlib import Path
import json,sys,multiprocessing as mp
if __name__=='__main__':
    model=sys.argv[1];n=int(sys.argv[2]);rows=json.loads(Path('scenes.json').read_text(encoding='utf-8-sig'));p=json.loads(Path(model+'-plans.json').read_text(encoding='utf8'))
    jobs=[(r,model,p[r['id']]) for r in sorted(rows,key=lambda r:-len(RECIPES[r['recipe']])) if not (Path('runs')/model/r['id']/'results.json').exists()]
    with mp.get_context('spawn').Pool(n,maxtasksperchild=12) as pool:
        for count,_ in enumerate(pool.imap_unordered(replay,jobs,chunksize=1),1):
            if count%10==0:print(model,count,flush=True)
