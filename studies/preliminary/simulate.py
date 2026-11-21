"""Render matched overhead observations, or test recorded Cartesian corrections in MuJoCo."""
import base64
import io
import json
import os
import sys
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image
import robosuite as suite
from robosuite.controllers import load_controller_config

def main():
    np.random.seed(123)
    env = suite.make('NutAssemblySquare', robots='Panda', has_renderer=False,
                     has_offscreen_renderer=True, use_camera_obs=False,
                     controller_configs=load_controller_config(default_controller='OSC_POSE'))
    env.reset()
    tight = os.getenv("ASSEMBLY_TIGHT") == "1"
    if tight:
        state = env.sim.get_state()
        xml = ET.fromstring(env.model.get_xml())
        geoms = xml.findall(".//body[@name='peg1']/geom")
        assert len(geoms)==2
        for g in geoms:
            g.set("size","0.02175 0.02175 0.1")
        env.reset_from_xml_string(ET.tostring(xml,encoding="unicode"))
        env.sim.set_state(state)
        env.sim.forward()
    sim = env.sim
    peg_id = sim.model.body_name2id('peg1')
    peg = sim.data.body_xpos[peg_id].copy()
    nut = next(n for n in env.nuts if 'Square' in n.name)
    gid = int(sim.model.body_geomadr[peg_id])
    top = sim.data.geom_xpos[gid, 2] + sim.model.geom_size[gid, 2]
    cam = sim.model.camera_name2id('birdview')
    sim.model.cam_quat[cam] = [1,0,0,0]
    sim.model.cam_fovy[cam] = 30
    width = 336
    cases = [(12,0),(-4,3),(0,-14),(-11,10),(3,-4),(-15,0),(0,11),(10,-12),(-3,-3),(9,8),(3,14),(0,0)]
    rng = np.random.RandomState(312)
    saved = sim.get_state()
    corrections = json.loads(sys.argv[1]) if len(sys.argv)>1 else None
    oblique = os.getenv("ASSEMBLY_VIEW") == "oblique"
    results=[]
    for i,(x,y) in enumerate(cases):
        drift = rng.uniform(-0.018,0.018,2)
        # The camera origin varies independently of the peg and nut.
        z = top + .024
        sim.model.cam_pos[cam] = [peg[0]+drift[0],peg[1]+drift[1],z+.35]
        if oblique:
            a = np.deg2rad(38)
            sim.model.cam_quat[cam] = [np.cos(a/2),np.sin(a/2),0,0]
            sim.model.cam_pos[cam] = [peg[0]+drift[0],peg[1]+drift[1]-.35*np.sin(a),top+.35*np.cos(a)]
        commands = corrections[i] if corrections is not None else [[0,0]]
        for action in commands:
            sim.set_state(saved)
            dx,dy=action
            pos = [peg[0]+(x+dx)/1000,peg[1]+(y+dy)/1000,z,1,0,0,0]
            sim.data.set_joint_qpos(nut.joints[0], np.array(pos))
            sim.data.set_joint_qvel(nut.joints[0],np.zeros(6))
            sim.forward()
            if corrections is None:
                img = Image.fromarray(sim.render(width=width,height=width,camera_name='birdview')[::-1].copy())
                stream=io.BytesIO()
                img.save(stream,format='PNG')
                print(json.dumps(dict(id=i+1,x=x,y=y,mm_per_px=700*np.tan(np.deg2rad(15))/width,
                                      img=base64.b64encode(stream.getvalue()).decode())),flush=True)
            else:
                for _ in range(450):
                    sim.step()
                p=sim.data.body_xpos[env.obj_body_id[nut.name]].copy()
                official=bool(env._check_success())
                results.append(dict(id=i+1,action=action,official=official,final_above_table_mm=round(float((p[2]-env.table_offset[2])*1000),1)))
    if corrections is not None:print(json.dumps(results))
    env.close()
if __name__=='__main__':main()

