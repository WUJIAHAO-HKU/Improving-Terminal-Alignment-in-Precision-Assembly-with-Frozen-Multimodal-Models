from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
import hashlib,json
from analysis15 import D,rd,M
P=D.parent/'JMS论文';O=P/'output'
def pack():
    for k in ['four','kits']:
        p=D/k;rs=rd(p/'scenes.json');assert len(set(a['id'] for a in rs))==100
        assert all(hashlib.sha256((p/f).read_bytes()).hexdigest()==v for f,v in rd(p/'lock.json')['sha256'].items())
        for m in M:
            assert len(list((p/'responses'/m).glob('*.json')))==300
            for r in rs:
                i=r['id'];q=rd(p/('runs' if k=='kits' else 'sim')/m/i/('results.json' if k=='kits' else 'outcomes.json'));assert set(q)=={'first','overhead'}
    dest=O/'robot-assembly-independent-rules-and-franka.zip';tmp=dest.with_suffix('.building');h={}
    with ZipFile(tmp,'w',ZIP_DEFLATED,compresslevel=2) as z:
        for p in sorted(D.rglob('*')):
            if not p.is_file() or p.suffix.lower() not in ('.py','.json','.png','.jpg','.mp4','.xml','.stl','.obj','.npy','.md') and p.name!='panda-LICENSE':continue
            if '__pycache__' in p.parts:continue
            n=p.relative_to(D).as_posix();v=p.read_bytes();z.writestr(n,v);h[n]=hashlib.sha256(v).hexdigest()
        z.writestr('CHECKSUMS.sha256',''.join(f'{v}  {n}\n' for n,v in h.items()))
        z.writestr('README.txt','Independent simulation supplement. Four and kits contain 100 fresh scenes each, paired across models. For each episode join the proposal and overhead action, rank, decisions and physical endpoints by model and scene id. Vary old/new rank and gate without rerunning physics using analysis15.py. Run analysis15.py from its parent with the four folders present. Development cases are from v0.2; the independent set did not fit the gains. The two Franka folders contain DIRECT visual point selection and REGISTERED skills, respectively. Each has ten individual infer-and-execute episodes and uninterrupted deterministic video replays. Registered skills supply the stock/nest map and quantized (0.5 mm) simulator configuration as a surrogate for surveyed coordinates. Screw reaction torque is a prescribed simulation load; compare actuator torque, rotation, advance, stop and engagement in the individual out-NN records. No physical robot or actual tightening pair was instrumented. Menagerie assets license supplied. Hardware timings and manufacturer limits cannot be inferred from this setup.')
    with ZipFile(tmp) as z:
        assert z.testzip() is None
        for n,v in h.items():assert hashlib.sha256(z.read(n)).hexdigest()==v
    tmp.replace(dest);print(dest.name,dest.stat().st_size,len(h))
def src():
    dest=O/'JMS-draft-source.zip';tmp=dest.with_suffix('.new')
    fs={f.name:f for f in P.glob('*.tex') if f.name!='outline.tex'}
    for n in ['fig11-revised-budgets.pdf','fig12-panda-fastener.pdf','fig13-revision-cases.pdf']:fs['figures/'+n]=P/'figures'/n
    for n in ['development-cases.json','independent-results.json','new-cases.json']:fs['evidence/revision15/'+n]=D/n
    with ZipFile(dest) as old,ZipFile(tmp,'w',ZIP_DEFLATED) as z:
        for n in old.namelist():
            if n not in fs:z.writestr(n,old.read(n))
        for n,p in fs.items():z.write(p,n)
    with ZipFile(tmp) as z:assert z.testzip() is None
    tmp.replace(dest)
if __name__=='__main__':pack();src()

