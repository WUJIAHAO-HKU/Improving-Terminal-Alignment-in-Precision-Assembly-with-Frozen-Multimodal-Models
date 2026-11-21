"""Summarize verified full episodes; build a time-indexed visual check from the actual MP4."""
from pathlib import Path
import json,cv2,numpy as np
from PIL import Image,ImageDraw
D=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def main():
    rows=[]
    for f in sorted((D/'runs').glob('*/result.json')):
        d=f.parent;r=read(f);st=[read(p) for p in sorted(d.glob('[0-9][0-9].json'))]
        a=[read(p)['action']['op'] for p in sorted(d.glob('req*.json'))]
        cap=cv2.VideoCapture(str(d/'execution.mp4'));frames=int(cap.get(cv2.CAP_PROP_FRAME_COUNT));fps=cap.get(cv2.CAP_PROP_FPS)
        trace_frames=sum(len(v['trace']) for v in st)
        assert frames==trace_frames and fps==25 and a[0]=='observe' and a[-1]=='release'
        snapshots=[]
        for j,(op,e) in enumerate(zip(a,st)):
            t=sum(len(v['trace']) for v in st[:j+1])-1
            cap.set(cv2.CAP_PROP_POS_FRAMES,t);ok,img=cap.read();assert ok
            im=Image.fromarray(cv2.cvtColor(img,cv2.COLOR_BGR2RGB)).resize((240,180));snapshots.append((op,im,t/fps))
        cap.release()
        grid=Image.new('RGB',(240*len(snapshots),204),'white');draw=ImageDraw.Draw(grid)
        for j,(op,im,t) in enumerate(snapshots):
            grid.paste(im,(240*j,0));draw.text((240*j+12,184),f'{t:.2f} s   {op}',fill='black')
        grid.save(d/'execution-frames.jpg',quality=92)
        r['video_seconds']=frames/fps;r['calls']=sum(1 for p in d.glob('*.json') if 'answer' in read(p))
        r['first_insert_seated']=next((v['seat'] for op,v in zip(a,st) if op=='insert'),False)
        r['trace_frames']=trace_frames
        rows.append(r)
    (D/'pilot-summary.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
    return rows
if __name__=='__main__':
    for r in main(): print(r['model'],r['scene'],r['success'],r['retries'],r['video_seconds'])

