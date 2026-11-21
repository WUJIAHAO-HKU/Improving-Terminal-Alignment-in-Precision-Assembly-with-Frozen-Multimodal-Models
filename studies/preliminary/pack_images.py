"""Save four independent scenes per labeled image from the renderer's JSONL stdout."""
import sys, json, base64, io
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
root=Path(__file__).resolve().parent
rows=[json.loads(l) for l in Path(sys.argv[1]).read_text(encoding="utf-8-sig").splitlines() if l.startswith("{")]
assert len(rows)==12
for j in range(3):
    sheet=Image.new("RGB",(672,720),"white")
    for k,r in enumerate(rows[j*4:j*4+4]):
        img=Image.open(io.BytesIO(base64.b64decode(r["img"])))
        x,y=k%2*336,k//2*360
        sheet.paste(img,(x,y+24))
        ImageDraw.Draw(sheet).text((x+8,y+2),"Case "+str(r["id"]), fill="black",font=ImageFont.truetype("arial.ttf",18))
    sheet.save(root/f"{sys.argv[2]}cases-{j+1}.png")

