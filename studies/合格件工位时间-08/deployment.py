"""Workstation time scenarios. All setup and rework inputs are blocking station time."""
import argparse,json
from pathlib import Path
from math import inf
METHODS=('geo','sol6','sol8','sol10')
def coefficients(groups,m,square=5/8,latency_factor=1.0):
    def get(shape):
        v=groups[shape][m]
        return (v['base']+(latency_factor-1)*v['inference'],v['f'])
    sq,r=get('square'),get('round')
    return tuple(square*x+(1-square)*y for x,y in zip(sq,r))
def station(groups,m,rework_min,parts,delta_setup_min,square=5/8,latency_factor=1.0,motion_s=0.0):
    u,f=coefficients(groups,m,square,latency_factor)
    return u+60*rework_min*f+motion_s+(60*delta_setup_min/parts if m=='geo' else 0)
def envelope(groups,square=5/8,latency_factor=1.0,sol_only=False):
    methods=METHODS[1:] if sol_only else METHODS
    coef={m:coefficients(groups,m,square,latency_factor) for m in methods}
    cuts=[0.]
    for j,a in enumerate(methods):
        for b in methods[j+1:]:
            u,f=coef[a];v,g=coef[b]
            if abs(f-g)>1e-10:
                r=(v-u)/(f-g)/60
                if r>0:cuts.append(r)
    cuts=sorted(set(cuts))+[inf]
    regions=[]
    for l,r in zip(cuts,cuts[1:]):
        probe=(l+r)/2 if r!=inf else l+1
        winner=min(methods,key=lambda m:coef[m][0]+probe*60*coef[m][1])
        if regions and regions[-1][2]==winner:regions[-1]=(regions[-1][0],r,winner)
        else:regions.append((l,r,winner))
    return regions
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rework-min',type=float,required=True);p.add_argument('--parts',type=int,default=100)
    p.add_argument('--delta-setup-min',type=float,default=0);p.add_argument('--square-share',type=float,default=.625)
    p.add_argument('--latency-factor',type=float,default=1);p.add_argument('--motion-s',type=float,default=0)
    v=p.parse_args()
    if v.parts<=0 or min(v.rework_min,v.latency_factor,v.motion_s)<0 or not 0<=v.square_share<=1:p.error('invalid scenario')
    groups=json.loads((Path(__file__).resolve().parent/'summary.json').read_text(encoding='utf8'))['groups']
    values={m:station(groups,m,v.rework_min,v.parts,v.delta_setup_min,v.square_share,v.latency_factor,v.motion_s) for m in METHODS}
    print('Seconds per qualified unit, relative to common setup; smaller is better')
    for m,time in sorted(values.items(),key=lambda kv:kv[1]):print(m,round(time,2))

