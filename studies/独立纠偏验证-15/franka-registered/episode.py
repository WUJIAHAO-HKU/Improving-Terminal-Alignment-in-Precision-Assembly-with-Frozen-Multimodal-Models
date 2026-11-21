"""Per-request MuJoCo checkpoint and observations, with a continuous deterministic telemetry-matched replay."""
from robot import *
from PIL import Image
import sys
def save(p,v):p.write_text(json.dumps(v,indent=2,default=lambda x:x.item()),encoding='utf8')
def apply(a,act):
    c=a.c;k=act['op'];j=act['index'];p=c['parts'][j] if k=='place' else c['parts'][-1]
    def xy(uv,h):u,v=uv;s=(.85-h)*2*np.tan(np.deg2rad(17))/360;return np.array([.50+(u-239.5)*s,(179.5-v)*s])
    if k=='place':
        fixture=np.round(np.array(c['target'])/.0005)*.0005
        # Fixture center and staging pockets are commissioned coordinates read before execution.
        # All inspected workpieces remain unmarked. Empty pockets are legal model choices.
        nominal=[[.38,-.135],[.49,-.14],[.62,-.13],[.64,.005]][act['nest']]
        pk=next((np.round(np.array(v['src'])/.0005)*.0005 for v in c['parts'] if v['nest']==act['nest']),nominal)
        return a.place(j,pk,fixture+[p['x'],p['y']])
    fixture=np.round(np.array(c['target'])/.0005)*.0005;physical=act['socket'];return a.tighten(physical,fixture+[c['bolts'][physical],0],.8)
def run(k,folder,what):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    a=Bench(k,video=what=='video');state=mj.mjtState.mjSTATE_INTEGRATION
    cp=folder/'state.npz'
    if what=='video':
        events=[]
        for p in sorted(folder.glob('action-*.json')):events.append(apply(a,json.loads(p.read_text())))
        a.savevideo(folder/'execution.mp4');save(folder/'video-check.json',[v['ok'] for v in events]);return
    if what!='init':
        old=np.load(cp);mj.mj_setState(a.m,a.d,old['s'],state);a.latches=list(old['l']);mj.mj_forward(a.m,a.d)
        act=json.loads((folder/what).read_text(encoding='utf-8-sig'));v=apply(a,act);save(folder/what.replace('action','out'),v)
    s=np.empty(mj.mj_stateSize(a.m,state));mj.mj_getState(a.m,a.d,s,state);np.savez(cp,s=s,l=a.latches)
    ix=len(list(folder.glob('out-*.json')))
    im=a.snap();Image.fromarray(im).save(folder/f'live-{ix:02}.jpg',quality=95)
    save(folder/'endpoints.json',[a.assembled(j) for j in range(len(a.c['parts']))])
if __name__=='__main__':run(int(sys.argv[1]),sys.argv[2],sys.argv[3])
