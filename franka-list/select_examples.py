"""Select the first eligible record of each predefined discordance type (ID order)."""
import csv,sys,json,tarfile
from pathlib import Path
from PIL import Image, ImageDraw,ImageFont
from io import BytesIO

def main(out,ar):
    data=list(csv.DictReader((out/'results/parts.csv').open(encoding='utf-8-sig')))
    found=[]
    for m in sorted({x['model'] for x in data}):
        rows=[r for r in data if r['model']==m]
        conditions={
          'combined_adds_success':lambda r:r['combined']=='1' and r['random']=='0' and r['first']=='0' and r['overhead']=='1',
          'random_adds_success':lambda r:r['combined']=='0' and r['random']=='1' and r['first']=='0' and r['overhead']=='1',
          'retaining_loses_success':lambda r:r['combined']=='1' and r['selected']=='first' and r['first']=='0' and r['overhead']=='1',
          'retaining_rescues_success':lambda r:r['combined']=='1' and r['selected']=='first' and r['first']=='1' and r['overhead']=='0'}
        for label,cond in conditions.items():
            eligible=[r for r in rows if cond(r)]
            if not eligible:continue
            r=eligible[0];i=r['scene'];p=f'{i}/{m}/'
            with tarfile.open(ar/f"batch-{int(r['batch']):02}.tgz") as t:
                def image(path): return Image.open(BytesIO(t.extractfile(path).read())).convert('RGB')
                ims=[image(i+'/initial-eye.png'),image(p+'first/final-top.png'),image(p+'overhead/final-top.png')]
                pair=Image.new('RGB',(1440,400),'white');draw=ImageDraw.Draw(pair)
                for j,(im,title) in enumerate(zip(ims,['Initial observation','First action: '+r['first'],'Overhead action: '+r['overhead']])):
                    pair.paste(im,(480*j,40));draw.text((480*j+12,12),title,fill='black')
                folder=out/'examples';folder.mkdir(exist_ok=True)
                name=m+'-'+label+'-'+i+'.png';pair.save(folder/name)
                meta=[json.load(t.extractfile(p+br+'/receipt.json')) for br in ('first','overhead')]
            found.append(dict(model=m,kind=label,eligible=len(eligible),scene=i,batch=r['batch'],task=r['task'],gap_mm=r['gap'],first=r['first'],overhead=r['overhead'],accepted=r['selected'],first_margin_mm=meta[0]['margin_mm'],overhead_margin_mm=meta[1]['margin_mm'],image=name))
    (out/'examples.json').write_text(json.dumps(found,indent=2),encoding='utf8')
if __name__=='__main__':main(Path(sys.argv[1]),Path(sys.argv[2]))
