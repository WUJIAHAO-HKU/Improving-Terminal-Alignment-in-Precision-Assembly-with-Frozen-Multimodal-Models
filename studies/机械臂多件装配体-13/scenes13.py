import numpy as np
from catalog import RECIPES
def scene(id,recipe,seed):
    rng=np.random.default_rng(seed);n=len(RECIPES[recipe])
    # Two columns of staging nests. The wider bridge parts occupy alternating rows.
    layout=[[-83,-47],[-30,-47],[-83,0],[-30,0],[-83,47],[-30,47],[42,-50],[42,50]]
    slots=rng.permutation(8)
    staging=[[float(layout[i][0]+rng.uniform(-1.5,1.5)),float(layout[i][1]+rng.uniform(-1.5,1.5)),float(rng.uniform(-8,8))] for i in slots[:n]]
    return dict(id=id,recipe=recipe,seed=seed,span=float(rng.uniform(20,23)),scale=float(rng.uniform(.92,1.13)),gap=float(rng.choice([.75,1.15,1.55])),ta=float(rng.uniform(-8,8)),tx=float(rng.uniform(39,48)),ty=float(rng.uniform(-7,11)),staging=staging,trays=[int(i) for i in slots[:n]])

def cohort():
    rows=[]
    for i,recipe in enumerate(RECIPES):
        for j in range(5):
            r=scene(f"K{i:02d}-{j}",recipe,8382642+211*i+j);r["batch"]=(i+4*j)%20;r["variant"]=j;rows.append(r)
    assert all(sum(r['batch']==i for r in rows)==5 for i in range(20))
    return rows
