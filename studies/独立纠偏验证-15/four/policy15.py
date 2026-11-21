"""Locked action and measurement decisions, using public recipe descriptors and sensor estimates."""
import math
def metric(a,b,L):
    delta=abs((a[2]-b[2]+90)%180-90)
    return math.hypot(a[0]-b[0],a[1]-b[1])+L*.5*math.radians(delta)
def gate(first,top,ref,L,shift):
    t=math.radians(ref[2]);ref=[ref[0]+shift*math.cos(t),ref[1]+shift*math.sin(t),ref[2]]
    return metric(top,ref,L)<metric(first,ref,L)
def score(pre,gain):
    return gain + .035*min(max(pre,0),10)/10
def features(r,kit,spec=None):
    if not kit:
        L=r['size'];return r['task'],L,(.14*L if r['task']=='dshaft' else 0)
    parts=spec(r);profiles={v['profile'] for v in parts};cols={v['column'] for v in parts};mono=cols=={'M'}
    kind=('single_' if mono else 'paired_')+('slot' if 'slot' in profiles else 'D' if 'dflat' in profiles else 'round')
    return kind,r['span'],.26*3.9*r['scale'] if mono and 'dflat' in profiles else 0
def vec(a):return [a[k] for k in ('x','y','yaw')] if isinstance(a,dict) else a

