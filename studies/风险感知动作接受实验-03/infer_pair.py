import pathlib,subprocess,tempfile,shutil,time,re,json,math,concurrent.futures,random
D=pathlib.Path(__file__).resolve().parent;rows=json.loads((D/'manifest.json').read_text());R=D/'responses';R.mkdir(exist_ok=True)
def run_one(r):
  op=[R/f"{r['id']}--direct.json",R/f"{r['id']}--measured.json"]
  if all(x.exists() for x in op): return
  part={'square':'brown square nut with square aperture and peg','round':'steel ring and cylindrical peg','dual':'red plate aperture and green pin'}[r['task']]
  p=f"""Precision assembly benchmark. One 320x320 RGB scene shows a {part}. Move the hole part horizontally over the stationary peg axis. Image right is +X and image up is +Y. Camera pitch {r['angle']} degrees, vertical FOV 30 degrees, optical center (159.5,159.5). Nominal aperture {45.5 if r['task']=='square' else 62.35 if r['task']=='round' else 100} mm. Peg size {2*({'square':22.75,'round':31.1764,'dual':50}[r['task']]-r['gap']):.2f} mm. Give two independent candidate actions. direct uses RGB only. measured may additionally use noisy RGB-D readings with moving-face distance {r['depth']['near']:.1f} mm and peg-top distance {r['depth']['far']:.1f} mm below camera. Output only JSON with numeric keys direct_dx,direct_dy,measured_dx,measured_dy."""
  with tempfile.TemporaryDirectory() as td:
    td=pathlib.Path(td);shutil.copy(D/'frames'/(r['id']+'.jpg'),td/'x.jpg');out=td/'o.txt';cmd=[shutil.which('codex'),'exec','--ephemeral','--skip-git-repo-check','--color','never','-s','read-only','-m','gpt-6.2-sol','-c','model_reasoning_effort="medium"','-i',str(td/'x.jpg'),'-o',str(out),p];st=time.monotonic();z=subprocess.run(cmd,cwd=td,stdin=subprocess.DEVNULL,capture_output=True,timeout=300);raw=out.read_text(encoding='utf-8');m=re.search(r'\{[^{}]+\}',raw);d=json.loads(m.group());
    for mode,keys in [('direct',('direct_dx','direct_dy')),('measured',('measured_dx','measured_dy'))]:
      a=[float(d[k]) for k in keys];assert all(math.isfinite(v) and abs(v)<300 for v in a);f=R/f"{r['id']}--{mode}.json";f.write_text(json.dumps(dict(id=r['id'],mode=mode,action=a,raw=raw,seconds=time.monotonic()-st)),encoding='utf-8')
def main():
  random.Random(8812).shuffle(rows)
  with concurrent.futures.ThreadPoolExecutor(max_workers=32) as ex:
    fs=[ex.submit(run_one,r) for r in rows]
    for i,f in enumerate(concurrent.futures.as_completed(fs),1):
      f.result()
      if i%10==0: print(i,flush=True)
  acts={r['id']:{m:json.loads((R/f"{r['id']}--{m}.json").read_text())['action'] for m in ('direct','measured')} for r in rows};(D/'actions.json').write_text(json.dumps(acts))
if __name__=='__main__':main()
