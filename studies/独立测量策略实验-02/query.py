"""Send the locked observations in fresh sessions, then assemble execution-only payload."""
from model_client import run,get,rows,D
import json,sys
def main():
    assert (D/'locked-ranks.json').exists()
    assert len(rows)==300 and len({r['seed'] for r in rows})==300
    jobs=[(r,m,'gpt-6.2-sol') for r in rows for m in ['direct','measured']]
    run(jobs)
    acts={r['id']:dict(direct=get(r,'direct'),always=get(r,'measured'),oracle=[-r['x'],-r['y']]) for r in rows}
    (D/'actions.json').write_text(json.dumps(acts,indent=2))
if __name__=='__main__':main()

