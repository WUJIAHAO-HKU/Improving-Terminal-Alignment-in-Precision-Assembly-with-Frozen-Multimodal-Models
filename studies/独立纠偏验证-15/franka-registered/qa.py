from robot import *
import sys
for k in map(int,sys.argv[1:]):
    a=Bench(k);c=a.c;vs=[]
    for j,p in enumerate(c['parts']):
        v=a.place(j,p['src'],np.array(c['target'])+[p['x'],p['y']]);vs.append(v);print(k,j,v,flush=True)
    for n,dx in enumerate(c['bolts']):
        v=a.tighten(n,np.array(c['target'])+[dx,0],.8);print(k,'bolt',v['ok'],v['trace'][-1],flush=True)

