from pathlib import Path
import shutil,json,hashlib
D=Path(__file__).resolve().parent;old=D.parent/'机械臂四任务独立验证-12'
for n in ('policy.py','gantry.py','server.py','decisions.py','analyze.py'):
    shutil.copyfile(old/n,D/n)
p=(old/'profiles.py').read_text(encoding='utf-8-sig')
a='profile(r,0)+[c,dy]'
assert p.count(a)==1
p=p.replace(a,"profile(r,0)*(2.15 if label=='other' and j==1 else 1.0)+[c,dy]")
(D/'profiles.py').write_text(p,encoding='utf8')
p=(old/'collect12.py').read_text(encoding='utf-8-sig').replace('Both are physically mateable; only the requested socket counts.','One socket has an oversized far-side key pin and cannot seat this part. Use the compatible receiver specified by the order.')
(D/'collect12.py').write_text(p,encoding='utf8')
p=(old/'execute.py').read_text(encoding='utf-8-sig').replace('assembly-jobs/arm-four','assembly-jobs/arm-keyed-Kq439R').replace('WORKERS=4 ','WORKERS=2 ')
(D/'execute.py').write_text(p,encoding='utf8')
lock=dict(protocol='Additional keyed dual-port cohort, n=25, 5 mixed blocks of 5. A wrong socket has a second locating pin with radius 2.15 times nominal. Freeze the previous batch rank, acceptance and sensory comparisons and use unseen dimensions, fresh draws and an unmarked physical gripper. Same logical budgets. Separate exploratory cohort; no pooling with the prespecified 100-scene tests. Verify a perfect commanded grasp seizes and carries; the compatible socket seats, and identical approach to incompatible socket physically cannot reach the seated height. All outcomes retained.',sha256={k:hashlib.sha256((D/k).read_bytes()).hexdigest() for k in ['design.py','profiles.py','collect12.py','gantry.py','server.py','policy.py','decisions.py','analyze.py']})
(D/'lock.json').write_text(json.dumps(lock,indent=2),encoding='utf8')
