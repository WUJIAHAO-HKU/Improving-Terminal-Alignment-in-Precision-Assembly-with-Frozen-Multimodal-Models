"""Record a single uninterrupted physics replay of the archived model-issued sequence."""
from render_kit import *
import kit
def main(model,i,mode):
    rows=json.loads(Path('scenes.json').read_text(encoding='utf-8-sig'));r=next(x for x in rows if x['id']==i)
    first=json.loads(Path(model+'-prefix.json').read_text())[i]
    plan=[first]+json.loads(Path(model+'-plans.json').read_text())[i][mode]
    existing=Path("recordings")/(model+"-"+i)/"replay.json"
    if existing.exists() and json.loads(existing.read_text())["mode"]==mode and (existing.parent/"execution.mp4").stat().st_size>1024:return
    m,d,steps=make(r);init(m,d);folder=Path('recordings')/(model+'-'+i);folder.mkdir(parents=True,exist_ok=True)
    ren=mj.Renderer(m,height=360,width=480)
    encoder=subprocess.Popen(['ffmpeg','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','480x360','-r','25','-i','-','-c:v','libx264','-threads','1','-pix_fmt','yuv420p',str(folder/'execution.mp4')],stdin=subprocess.PIPE)
    base=mj.mj_step;n=0;frames_n=0
    def advance(m,d,nstep=1):
        nonlocal n,frames_n
        for _ in range(nstep):
            base(m,d);n+=1
            if n%40==0:
                ren.update_scene(d,camera='video');encoder.stdin.write(ren.render().tobytes());frames_n+=1
    mj.mj_step=advance;events=[]
    try:
        for j,a in enumerate(plan):
            v,t=perform(m,d,r,j,a['pick'],a['place'],steps);events.append(v);ren.update_scene(d,camera='eye');Image.fromarray(ren.render()).save(folder/f'stage-{j+1:02}.png')
            if not v['lift'] or not v['carry']:break
        final=[judge(m,d,r,s,j)['seat'] for j,s in enumerate(steps)]
    finally:
        mj.mj_step=base;encoder.stdin.close();assert encoder.wait()==0;ren.close()
    out=dict(id=i,model=model,mode=mode,events=events,final=final,frames=frames_n)
    (folder/'replay.json').write_text(json.dumps(out,indent=2));print(model,i,final,flush=True)
if __name__=='__main__':main(*sys.argv[1:])

