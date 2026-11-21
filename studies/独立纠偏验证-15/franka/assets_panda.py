"""Preserve official inertial, joint, actuator and contact model. Use collision meshes for appearance."""
from pathlib import Path
import requests,xml.etree.ElementTree as ET,concurrent.futures,hashlib,json
D=Path(__file__).resolve().parent;repo='https://raw.githubusercontent.com/google-deepmind/mujoco_menagerie/main/franka_emika_panda/'
r=ET.parse(D/'panda.xml').getroot()
for b in r.findall('.//worldbody//body'):
    for x in list(b.findall('geom')):
        if x.get('class')=='visual':b.remove(x)
        elif x.get('class')=='collision':x.set('group','0');x.set('rgba','.68 .7 .72 1')
names={x.get('mesh') for x in r.findall('.//worldbody//geom')};d=D/'assets';d.mkdir(exist_ok=True)
files=[]
for x in list(r.find('asset').findall('mesh')):
    if x.get('name',Path(x.get('file')).stem) not in names:r.find('asset').remove(x)
    else:files.append(x.get('file'))
def get(n):
    v=requests.get(repo+'assets/'+n,timeout=40);v.raise_for_status();(d/n).write_bytes(v.content)
with concurrent.futures.ThreadPoolExecutor(6) as ex:list(ex.map(get,files))
for n in ['LICENSE','README.md']:
    v=requests.get(repo+n,timeout=15)
    if v.ok:(D/('panda-'+n)).write_bytes(v.content)
r.remove(r.find('keyframe'));r.find('compiler').set('meshdir','assets')
ET.ElementTree(r).write(D/'template.xml',encoding='utf-8')
print(files)


