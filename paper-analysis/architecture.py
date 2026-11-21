"""Rebuild the paper schematic on the 1440 x 600 reference coordinate system."""
from pathlib import Path
import math
from PIL import Image,ImageOps,ImageEnhance
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.colors import HexColor,Color
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import pymupdf
D=Path(__file__).resolve().parent
raw=Image.open(D/'tmp/pdfs/architecture-art.png').convert('RGB')
dst=D/'figures/fig2-architecture.pdf'
c=Canvas(str(dst),pagesize=(1440,600))
pdfmetrics.registerFont(TTFont('SerifBI','timesbi.ttf'))
def color(s):return HexColor(s)
dark='#201c21';purple='#693a88';lav='#f0ebf2';green='#577a36';amber='#a86327';violet='#703589'
def rect(x,y,w,h,fill='white',edge=dark,r=4,lw=1.6):
    c.setLineWidth(lw);c.setStrokeColor(color(edge));c.setFillColor(color(fill) if fill.startswith('#') else Color(1,1,1));c.roundRect(x,600-y-h,w,h,r,stroke=1,fill=1)
def txt(x,y,s,size=17,col=dark,rot=0):
    c.saveState();c.translate(x,600-y);c.rotate(rot);c.setFont('SerifBI',size);c.setFillColor(color(col));c.drawCentredString(0,-size*.32,s);c.restoreState()
def path(points,col=dark,lw=1.8,arrow=True):
    c.setStrokeColor(color(col));c.setLineWidth(lw);p=c.beginPath();p.moveTo(points[0][0],600-points[0][1])
    for x,y in points[1:]:p.lineTo(x,600-y)
    c.drawPath(p)
    if arrow:
        (a,b),(x,y)=points[-2:];z=math.atan2(y-b,x-a);p=c.beginPath();p.moveTo(x,600-y)
        for k in [-.49,.49]:p.lineTo(x-8*math.cos(z+k),600-y+8*math.sin(z+k))
        p.close();c.setFillColor(color(col));c.drawPath(p,fill=1,stroke=0)
def panel(x,y,w,h):rect(x+4,y+4,w,h,'#d9d8d8','#e1e0df',14,.6);rect(x,y,w,h,'#ffffff','#dbd9d9',14,.8)
def title(x,y,w,s):rect(x,y,w,26,lav);txt(x+w/2,y+13,s,18)
def tile(x,y,im,w,h):
    im=ImageOps.fit(im,(int(w*2),int(h*2)))
    c.drawImage(ImageReader(im),x,600-y-h,w,h)
def box(x,y,w,h,s,fill='#fff1c3',fs=16):rect(x,y,w,h,fill);txt(x+w/2,y+h/2,s,fs)
def stack(x,y,f):
    for a in [8,4,0]:rect(x+a,y-a,18,18,f,dark,0,1.1)
def chevron(x,y,col=purple):
    pts=[(x,y-15),(x+11,y-15),(x+11,y-24),(x+25,y),(x+11,y+24),(x+11,y+15),(x,y+15),(x,y-15)]
    path(pts,col,2.8,False)
frames=next(D.parent.glob('*05'))/'frames'; imgs=[Image.open(p).convert('RGB') for p in sorted(frames.glob('*.jpg'))[:8]]
def montage(x,y,side):
    for n in range(4):tile(x+(n%2)*(side/2+3),y+(n//2)*(side/2+3),imgs[n],side/2-2,side/2-2)
    tile(x+side*.23,y+side*.23,imgs[4],side*.53,side*.53)
# Top gallery, aligned to the six source thumbnail boxes.
rect(5,8,1409,125,'#ffffff','#bcbcbc',14,2.1)
txt(25,72,'Mixed-model stream',13,rot=90)
path([(54,28),(131,44),(131,94),(54,114),(54,28)],purple,2,False)
txt(91,62,'Assembly',15,purple);txt(91,82,'policy',15,purple)
for j,(s,col) in enumerate([('Square','#f8dddd'),('Round','#eaf0dc'),('Held pair','#dceafa')]):
    y=22+j*34;box(145,y,62,23,s,col,12);path([(211,y+12),(242,y+12)],purple)
for x,w,(l,r),s in zip([249,450,644,836,1029,1219],[185,180,180,178,180,181],[(335,585),(606,850),(867,1110),(1126,1370),(1388,1630),(1647,1889)],['Square bore','Round bore','Held parts','Paired replay','First-pass yield','Station time']):
    tile(x,27,raw.crop((l,37,r,112)),w,88)
    c.saveState();c.setFillAlpha(.48);c.setFillColor(color('#23172b'));c.rect(x,600-89,w,24,stroke=0,fill=1);c.restoreState();txt(x+w/2,77,s,18,'#ffffff')
panel(398,179,294,196);panel(935,179,265,78);panel(1189,286,240,297);panel(0,420,744,163)
title(423,164,254,'Frozen multimodal model');title(935,164,266,'Selective measurement')
title(1189,274,212,'Workstation evaluation');title(201,401,261,'Offline paired rollouts')
for x in (450,646):path([(x,163),(x,135)],purple)
txt(548,149,'Applied to the mixed-model stream',13,purple)
montage(5,204,133);txt(72,356,'RGB observations',18)
path([(147,272),(222,272)]);txt(185,254,'RGB',15,purple);txt(184,291,'Process data',14,purple)
for j,col in enumerate(['#99b677','#e1ad48','#97b9d9','#82a871','#c4b6e2','#e7ce53','#8fbed2','#d0a04c']):
    stack(227+(j%2)*35,224+(j//2)*28,col)
txt(255,356,'Visible inputs',17);path([(284,272),(306,272)]);box(306,251,47,44,'[ · ; · ]','#ffffff',19);chevron(363,270)
rect(408,205,42,142);txt(429,275,'First request',16,rot=90)
for x,s in [(466,'RGB'),(513,'View'),(559,'Part type'),(653,'Action')]:
    rect(x,205,29,66,'#dce2f2');txt(x+14,238,s,14,rot=90)
for a,b in [(450,466),(495,513),(542,559),(589,612),(636,653)]:path([(a,237),(b,237)])
txt(625,237,'...',18)
rect(463,286,224,74,'#ffffff','#a2a2a2',9,1)
for x,cc,s in [(472,'#dfedd4','Pose'),(519,'#fff0b1','Gap'),(580,'#dfedd4','View'),(629,'#fde5d9','Move')]:
    rect(x,297,31,51,cc);txt(x+15,322,s,14,rot=90)
for a,b in [(503,519),(551,580),(611,629)]:path([(a,322),(b,322)])
chevron(703,264)
for j,col in enumerate(['#f5d6dd','#e4d7f5','#fee9d5','#e0ecc7','#c6e1ed']):stack(751,205+28*j,col)
txt(767,356,'First proposal',16);txt(838,181,'Process cues',15)
stack(825,209,'#d1e9ee');box(817,250,49,43,'[ · ; · ]','#ffffff',18)
path([(838,229),(838,249)]);path([(777,271),(816,271)]);path([(866,271),(885,271)])
rect(886,201,42,141);txt(907,270,'Pre-measurement score',13,rot=90)
path([(929,236),(958,236),(958,225),(974,225)])
for x,w,s,col in [(975,48,'Score','#e5efd7'),(1039,51,'Quota','#dce6f4'),(1106,82,'Measure?','#fce0cc')]:box(x,205,w,41,s,col,15)
path([(1023,225),(1038,225)]);path([(1090,225),(1106,225)])
for x,y,s,col,ico in [(1261,169,'Frozen','#e6e9ef','ice'),(1261,212,'Fitted','#f8d2cd','flame')]:
    rect(x,y,105,29,col);rect(x,y,30,29,'#ffffff');txt(x+68,y+14,s,17)
    c.drawImage(ImageReader(raw.crop((1704,230 if ico=='ice' else 292,1739,265 if ico=='ice' else 323))),x+4,600-y-26,22,22)
for j,col in enumerate(['#f7c9c1','#e7d3e7','#f4d0c9']):stack(27+20*j,506-(j%2)*19,col)
txt(67,549,'Paired labels',16)
for x,s,col in [(147,'Replay','#ffffff'),(241,'Compare','#f2edf3'),(405,'Fit ridge','#f7e9df')]:
    rect(x,447,39,100,col);txt(x+20,499,s,16,rot=90)
for x in (98,200,290,465,627):chevron(x,498,dark)
stack(342,481,'#ded5ec');stack(342,514,'#efe3cb');txt(355,548,'Gains',16)
for j,col in enumerate([amber,green,violet]):
    x=500+40*j;path([(x,499),(x+8,486),(x+15,500),(x+22,480),(x+32,491)],col,2,False)
txt(558,520,'Cross-fitted',17);txt(558,542,'gain scores',16)
rect(660,425,62,141,'#dba697',dark,10)
c.saveState();p=c.beginPath();p.roundRect(662,600-564,58,137,8);c.clipPath(p,stroke=0,fill=0);c.linearGradient(690,600-427,690,600-564,[color('#edb88c'),color('#80519b')]);c.restoreState()
txt(691,497,'Locked rules',18,rot=90)
# Routes show mutually exclusive branches; the second request is made only after Measure.
for y,yt,x,col,lab,action in [(442,310,946,amber,'Skip','First action'),(486,390,957,green,'Retain','First action'),(534,489,963,violet,'Replace','Second action')]:
    path([(722,y),(x,y),(x,yt),(973,yt)],col,2.5);box(973,yt-14,75,27,lab,'#fce796')
    path([(1049,yt),(1084,yt)],col,2)
    rect(1086,yt-16,82,42,'#33384f','#343348',1);txt(1127,yt+5,action,14,'#ffffff')
    txt(834,y-11,{'Skip':'Budget / score','Retain':'Measured gain ≤ 0','Replace':'Measured gain > 0'}[lab],15,col)
# Offline parameters govern scoring; branch constraints use the two available candidates.
c.saveState();c.setDash(3,3);path([(691,424),(691,393),(839,393),(839,304),(880,304)],'#786887',1.3);c.restoreState()
path([(1146,247),(1146,264)],dark,1.3)
rect(945,260,257,22,'#faf7fa','#a89caf',4,.7);txt(1073,271,'If measured: same model + depth',13)
path([(1065,282),(1065,323),(1054,323)],'#a899ad',.8,False)
path([(1049,283),(937,283),(937,307),(966,307)],'#aaa1aa',.7,False)
for yy in [313,393,490]:
    c.saveState();c.setDash(3,3);path([(1170,yy),(1180,yy)],'#97859d',1.05,False);c.restoreState()
path([(1181,313),(1181,490)],'#97859d',.9,False);path([(1181,393),(1211,393)],'#97859d',1.1)
for n,col in enumerate([amber,green,violet]):
    path([(170+n*3,551),(170+n*3,575-n*2),(418+n*4,575-n*2),(418+n*4,548)],col,1.2)

for q,n in enumerate([0,1,2,3]):
    v=Image.open(next(D.parent.glob('*07'))/'failure_views'/f'{n:02d}.jpg').crop((240,0,480,240))
    tile(1225+(q%2)*69,322+(q//2)*68,v,65,65)
tile(1256,352,Image.open(next(D.parent.glob('*07'))/'failure_views'/'04.jpg').crop((240,0,480,240)),69,69)
txt(1293,475,'Paired outcomes',18)
path([(1292,484),(1292,502)]);rect(1202,502,186,60,'#ffffff');txt(1295,523,'Yield and rework',17,'#8a292a');txt(1295,548,'Time per qualified part',15)
c.showPage();c.save()
doc=pymupdf.open(dst);doc[0].get_pixmap(matrix=pymupdf.Matrix(2,2)).save(D/'figures/fig2-architecture.png')

