from pathlib import Path
import json,numpy as np,hashlib
D=Path(__file__).resolve().parent
TASKS=['twin','blade','dshaft','connector']
def generate():
    rng=np.random.default_rng(764310211);rows=[]
    # 20 independently generated five-part blocks, balancing four tasks across each four blocks.
    for b in range(20):
        for j in range(5):
            i=5*b+j;k=TASKS[(j+b)%4];size=float(rng.choice({'twin':[26.,28.5,33.5,35.5],'blade':[26.5,29.5,33.5,37.5],'dshaft':[14.5,16.5,19.5,21.5],'connector':[16.5,18.5,20.5,21.5]}[k]))
            ty=float(rng.uniform(-26,-15) if k=='connector' else rng.uniform(-12,15))
            other=39 if k=='connector' else 0
            if k=='connector' and rng.random()<.5:ty+=39;other=-39
            rows.append(dict(id=f'B{i:03}',task=k,batch=b,size=size,width=float(rng.choice([22.,23.,25.])),radius=float(rng.choice([2.6,3.1,3.6])),gap=float(rng.choice([.45,.75,1.1,1.5])),tx=float(rng.uniform(35,49)),ty=ty,ta=float(rng.uniform(-12,12)),other_y=other,sx=float(rng.uniform(-58,-38)),sy=float(rng.uniform(-20,12)),sa=float(rng.uniform(-22,22)),occ_x=float(rng.choice([-1,1])*rng.uniform(33,54)),occ_w=float(rng.uniform(5,12))))
    return rows
if __name__=='__main__':
    (D/'scenes.json').write_text(json.dumps(generate(),indent=2),encoding='utf8')

