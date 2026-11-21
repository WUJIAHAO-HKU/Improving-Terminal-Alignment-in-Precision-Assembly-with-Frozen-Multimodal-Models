from pathlib import Path
import numpy as np
def generate():
    rng=np.random.default_rng(245983330);rows=[]
    for i in range(25):
        sgn=(-1)**int(rng.integers(2));dy=sgn*36.;sy=-dy/2+rng.uniform(-2,2)
        rows.append(dict(id=f'P{i:03}',batch=i//5,task='connector',size=float(rng.choice([17.2,19.2,21.2])),width=24.,radius=float(rng.choice([2.6,3.,3.4])),gap=float(rng.choice([.45,.75,1.1,1.5])),tx=float(rng.uniform(36,44)),ty=sy,ta=float(rng.uniform(-9,9)),other_y=dy,sx=float(rng.uniform(-52,-38)),sy=float(rng.uniform(-15,10)),sa=float(rng.uniform(-16,16)),occ_x=float(rng.choice([-1,1])*rng.uniform(30,50)),occ_w=float(rng.uniform(5,11))))
    return rows
