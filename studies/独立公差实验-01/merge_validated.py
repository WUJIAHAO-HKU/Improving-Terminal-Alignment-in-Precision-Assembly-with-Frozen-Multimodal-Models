"""Assemble the validated release only, excluding superseded cylindrical peg references."""
from pathlib import Path
import sys,shutil,json
root=Path(__file__).resolve().parent;c=root/'round-corrected';f=root/'validated';f.mkdir(exist_ok=True)
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def put(file,data):(f/file).write_text(json.dumps(data,indent=2),encoding='utf-8')
def isround(row):return row.get('task')=='round' or row.get('id','').startswith(('round-','stress-round-'))
for n in ['manifest.json','scores.json','stress-scores.json','fixtures.json','stress-manifest.json']:
 a=read(root/n);b=read(c/n);put(n,[r for r in a if not isround(r)]+[r for r in b if isround(r)])
for n in ['actions.json','stress-actions.json','locked-gate.json']:
 a=read(root/n);a.update(read(c/n));put(n,a)
for sub in ['frames','responses','stress-responses']:
 (f/sub).mkdir(exist_ok=True)
 for origin in [root,c]:
  for path in (origin/sub).iterdir():
   if not path.is_file():continue
   r=path.name.startswith(('round-','stress-round-'))
   if (origin==c)==r:shutil.copyfile(path,f/sub/path.name)
for n in ['capture.py','server.py','stress.py','infer.py','analyze.py','protocol.txt','resolution.py','architecture-final.png','report.py']:
 shutil.copyfile(root/n,f/n)
for n in ['timestep-check.json','audit_key.json','blinded-visual-audit.json']:
 shutil.copyfile(c/n,f/n)
shutil.copytree(c/'audit_views',f/'audit_views',dirs_exist_ok=True)
assert len(read(f/'manifest.json'))==180 and len(read(f/'scores.json'))==600 and len(read(f/'stress-scores.json'))==144
assert len(list((f/'responses').glob('*.json')))==420 and len(list((f/'stress-responses').glob('*.json')))==96

