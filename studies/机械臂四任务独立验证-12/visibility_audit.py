"""Post-run pixel coverage audit, unavailable to the models or ranking rule."""
from gantry import build,mj,np
from pathlib import Path
import json
from multiprocessing import get_context
def visible(r):
    i=r['id'];m,d=build(r);spec=mj.mjtState.mjSTATE_INTEGRATION
    mj.mj_setState(m,d,np.load(Path('initial')/i/'state.npz')['state'],spec);mj.mj_forward(m,d)
    guard=m.geom('guard').id;m.geom_group[guard]=5
    with mj.Renderer(m,height=360,width=480) as ren:
        ren.enable_segmentation_rendering();op=mj.MjvOption()
        def capture(v):
            op.geomgroup[5]=v;ren.update_scene(d,camera='eye',scene_option=op);img=ren.render();return np.where(img[:,:,1]==int(mj.mjtObj.mjOBJ_GEOM),img[:,:,0],-1)
        actual=capture(1);clear=capture(0)
    out={}
    for prefix in ['cover_','pin_primary','pin_other']:
        ids=[g for g in range(m.ngeom) if (m.geom(g).name or '').startswith(prefix)];mask=np.isin(clear,ids);n=int(mask.sum())
        out[prefix]=[int((mask&(actual==guard)).sum()),n]
    return i,out
if __name__=='__main__':
    rows=json.loads(Path('scenes.json').read_text(encoding='utf-8-sig'))
    with get_context('spawn').Pool(2,maxtasksperchild=12) as pool:data=dict(pool.imap_unordered(visible,rows))
    Path('visibility.json').write_text(json.dumps(data,indent=2))
