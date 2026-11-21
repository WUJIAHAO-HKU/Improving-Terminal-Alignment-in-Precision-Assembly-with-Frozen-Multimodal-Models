"""Infer Sol direct and measured actions for round 3."""
import pathlib,subprocess,tempfile,shutil,time,re,json,math,concurrent.futures,random,sys
D=pathlib.Path(__file__).resolve().parent;rows=json.loads((D/'manifest.json').read_text());R=D/'responses';R.mkdir(exist_ok=True)
def path(r,m):return R/f"{r['id']}--{m}.json"
def run_one(z):
 r,m=z;o=path(r,m)
 if o.exists():return
 part={'square':'brown square nut with square aperture and peg','round':'steel ring and cylindrical peg','dual':'red plate aperture and green pin'}[r['task']]
 prompt=f"""Precision assembly. One 320x320 RGB scene shows a {part}. Move the hole part horizontally over the stationary peg axis. Image right is +X, image up is +Y. Camera pitch {r['angle']} degrees, vertical FOV 30 degrees, optical center (159.5,159.5). Nominal aperture {45.5 if r['task']=='square' else 62.35 if r['task']=='round' else 100} mm. Peg size {2*({'square':22.75,'round':31.1764,'dual':50}[r['task']]-r['gap']):.2f} mm. Use image and prompt only. Output one JSON object with dx and dy in millimeters."""
 if m=='measured':prompt+=f" Additional RGB-D plane readings are moving-face {r['depth']['near']:.1f} mm and peg-top {r['depth']['far']:.1f} mm below camera. They include noise."
 with tempfile.TemporaryDirectory() as q:
  q=pathlib.Path(q);shutil.copy(D/'frames'/(r['id']+'.jpg'),q/'x.jpg');reply=q/'o.txt';cmd=[shutil.which('codex'),'exec','--ephemeral','--skip-git-repo-check','--color','never','-s','read-only','-m','gpt-6.2-sol','-c','model_reasoning_effort="medium"','-i',str(q/'x.jpg'),'-o',str(reply),prompt];st=time.monotonic();z=subprocess.run(cmd,cwd=q,stdin=subprocess.DEVNULL,capture_output=True,timeout=240);raw=reply.read_text(encoding='utf-8');d=json.loads(re.search(r'\{[^{}]+\}',raw).group());a=[float(d['dx']),float(d['dy'])];assert all(math.isfinite(v) and abs(v)<300 for v in a);o.write_text(json.dumps(dict(id=r['id'],mode=m,action=a,raw=raw,seconds=time.monotonic()-st)),encoding='utf-8')
def main():
 jobs=[(r,m) for r in rows for m in ['direct','measured']];random.Random(8801).shuffle(jobs)
 with concurrent.futures.ThreadPoolExecutor(max_workers=32) as ex:
  for i,f in enumerate(concurrent.futures.as_completed([ex.submit(run_one,z) for z in jobs]),1):
   f.result()
   if i%20==0:print(i,flush=True)
 acts={r['id']:{m:json.loads(path(r,m).read_text())['action'] for m in ['direct','measured']} for r in rows};(D/'actions.json').write_text(json.dumps(acts))
if __name__=='__main__':main()

