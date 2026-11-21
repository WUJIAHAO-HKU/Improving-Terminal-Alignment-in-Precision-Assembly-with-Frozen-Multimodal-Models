from catalog import RECIPES
TRAYS=[[-83,-47],[-30,-47],[-83,0],[-30,0],[-83,47],[-30,47],[42,-50],[42,50]]
def spec(r):
    parts=RECIPES[r['recipe']];stacks={'M':4,'L':4,'R':4};desc=[]
    for j,v in enumerate(parts):
        cols=list(v.column) if v.column=='LR' else [v.column]
        z=stacks[cols[0]]
        for c in cols:stacks[c]+=v.thickness
        slot=r['trays'][j]
        desc.append(dict(name=v.label,profile=v.profile,column=v.column,bottom=z,thickness=v.thickness,slot=slot,approx_source=TRAYS[slot]))
    for v in desc:
        col=v['column'];v['pin_top']=max(stacks[c] for c in (list(col) if col=='LR' else [col]))+1.5
    return desc

