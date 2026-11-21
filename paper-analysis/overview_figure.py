"""Typeset the assembly overview in the native 1440 x 1174 reference coordinates."""
from pathlib import Path
import json, math
from PIL import Image,ImageOps
import pymupdf
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
D=Path(__file__).resolve().parent
O=D/'figures'; H=1322
def project(n):return next(D.parent.glob('*'+n))
def read(n):return json.loads(n.read_text(encoding='utf-8-sig'))
for n,f in [('Sans','arial'),('Bold','arialbd'),('Serif','times'),('Italic','timesi'),('Hand','comic')]:
    pdfmetrics.registerFont(TTFont(n,''+f+'.ttf'))
c=Canvas(str(O/'fig1-overview.pdf'),pagesize=(1440,H));c.setTitle('Selective measurement and action acceptance')
art=Image.open(O/'fig1-illustrations.png').convert('RGB')
ink='#162f45';navy='#184b71';blue='#416d83';cyan='#50aaba';pink='#cd8190';red='#a71f37';green='#699147';edge='#a7c4ca';paper='#ffffff';gray='#888888'
def box(x,y,w,h,fill=paper,stroke=ink,r=5,lw=1):
    c.setLineWidth(lw);c.setStrokeColor(HexColor(stroke));c.setFillColor(HexColor(fill));c.roundRect(x,H-y-h,w,h,r,stroke=1,fill=1)
def label(x,y,s,sz=20,font='Sans',col=ink,align='center',angle=0):
    c.saveState();c.translate(x,H-y);c.rotate(angle);c.setFillColor(HexColor(col));c.setFont(font,sz)
    {'center':c.drawCentredString,'left':c.drawString,'right':c.drawRightString}[align](0,-sz*.32,s);c.restoreState()
def poly(pts,col=gray,lw=1.8,arrow=True,dash=None):
    c.saveState();c.setStrokeColor(HexColor(col));c.setLineWidth(lw)
    if dash:c.setDash(dash)
    p=c.beginPath();p.moveTo(pts[0][0],H-pts[0][1])
    for x,y in pts[1:]:p.lineTo(x,H-y)
    c.drawPath(p);c.restoreState()
    if arrow:
        x,y=pts[-1];a,b=pts[-2];theta=math.atan2(y-b,x-a);p=c.beginPath();p.moveTo(x,H-y)
        for k in [-.45,.45]:p.lineTo(x-9*math.cos(theta+k),H-y+9*math.sin(theta+k))
        p.close();c.setFillColor(HexColor(col));c.drawPath(p,fill=1,stroke=0)
def image(im,x,y,w,h):
    c.drawImage(ImageReader(im),x,H-y-h,w,h,mask='auto')
def crop(bounds,x,y,w,h):image(art.crop(bounds),x,y,w,h)
metal=Image.open(O/'fig1-metal.png').convert('RGB')
assert metal.size==art.size
def metal_crop(bounds,x,y,w,h):image(metal.crop(bounds),x,y,w,h)
def strip(x,y,s,angle=0):
    c.saveState();c.translate(x,H-y);c.rotate(angle);w=pdfmetrics.stringWidth(s,'Bold',19)+18
    c.setFillColor(HexColor('#b5acad'));c.roundRect(-w/2+3,-16,w,29,6,fill=1,stroke=0)
    c.setFillColor(HexColor('#fff05a'));c.roundRect(-w/2,-12,w,28,5,fill=1,stroke=0)
    c.setFillColor(HexColor(navy));c.setFont('Bold',19);c.drawCentredString(0,-5,s);c.restoreState()
def panel(x,y,w,h,title):
    box(x,y,w,h,stroke=edge,r=26,lw=2);wid=pdfmetrics.stringWidth(title,'Hand',26)+20
    box(x+(w-wid)/2,y-9,wid,18,paper,paper,0,.1);label(x+w/2,y,title,26,'Hand',blue)
def block(x,y,w,h,s,fill,fs=23):
    box(x,y,w,h,fill,'#454549',8,1.3);label(x+w/2,y+h/2,s,fs,'Serif','#202429')
def chip(x,y,s,col='#ddeaf1'):
    box(x,y,24,24,col,blue,3,1);label(x+12,y+12,s,16,'Italic',blue)
def eye(x,y):
    t=c.beginPath();t.moveTo(x-22,H-y);t.curveTo(x-9,H-y+18,x+8,H-y+18,x+22,H-y);t.curveTo(x+9,H-y-15,x-9,H-y-15,x-22,H-y)
    c.setStrokeColor(HexColor('#3885ab'));c.setLineWidth(3);c.drawPath(t);c.setFillColor(HexColor('#3885ab'));c.circle(x,H-y,7,fill=1,stroke=0)
def arrow_curve(x,y,w=37,h=24):
    p=c.beginPath();p.moveTo(x,H-y);p.curveTo(x+w,H-y+11,x+w+5,H-y-h/2,x+w-2,H-y-h)
    c.setStrokeColor(HexColor('#827a93'));c.setLineWidth(2);c.drawPath(p);poly([(x+w,y+h-8),(x+w-2,y+h)],'#827a93',1.5)
# a: five separately registered illustrations, two callouts and a highlighted decision.
metal_crop((44,65,444,390),13,55,201,177);metal_crop((27,505,473,832),30,265,185,157)
metal_crop((523,149,1245,850),267,146,333,300);metal_crop((1323,62,1724,389),645,56,198,177)
metal_crop((1280,509,1740,840),683,264,186,157)
poly([(66,182),(93,261)],'#427b95',2);poly([(721,179),(695,244),(706,258)],'#427b95',2)
label(595,90,'Moving bore',23,'Bold',pink,'right');label(596,115,'Initial lateral offset',19,'Sans',pink,'right')
poly([(540,130),(540,162),(510,200)],pink,1.2,False,[4,3])
label(221,362,'Fixed peg',21,'Bold',cyan,'left');label(221,387,'Partly occluded',16,'Sans',cyan,'left')
poly([(320,360),(369,360),(417,360)],cyan,1.2,False,[4,3])
poly([(405,331),(395,294),(377,281)],'#4a9e6e',1.25)
poly([(417,333),(426,298),(446,281)],'#4a9e6e',1.25)
label(369,258,'Align centers',16,'Bold','#2e8758',angle=-35)
poly([(230,441),(301,465),(565,465),(633,440)],red,2.4);strip(430,464,'Measure before release?')
for x,s,t in [(122,'Initial RGB','proposal'),(777,'One selected','correction')]:
    label(x,451,s,23,'Bold',navy);label(x,479,t,23,'Bold',navy)
label(432,545,'(a) Terminal alignment under occlusion',29,'Sans',blue)
# b: mirrored stacks; arrows on the by-pass routes carry the first action.
for x,bg,top,mid,last,symbol in [(919,'#f4f9fa','Sense or skip','Quota rule','RGB proposal','s'),(1170,'#fcf6f6','Keep or replace','Gain rule','Depth proposal','g')]:
    box(x,121,237,343,bg,'#e3e9e9',8,.6)
    for y,hh,st,fill in [(169,58,top,'#f0ccce'),(244,30,mid,'#f0f6ec'),(332,58,last,'#cee7ec'),(407,30,'Frozen model','#f0f6ec')]:
        block(x+36,y,188,hh,st,fill,21)
    for y1,y2 in [(469,438),(407,391),(332,276),(244,229),(169,143)]:poly([(x+81,y1),(x+81,y2)],ink,1.3)
    poly([(x+64,449),(x+17,449),(x+17,141),(x+63,141)],ink,1.2)
    label(x+84,140,'○',17,'Sans',blue);label(x+84,140,'+',14,'Sans',blue);label(x+149,142,'Quota threshold' if x<1000 else 'Gain > 0?',15,'Italic',blue)
    for j,st in enumerate(['I','c','v'] if x<1000 else ['I','z','a']):chip(x+50+j*29,471,st)
label(1035,80,'Before measurement',26,'Italic',blue);label(1290,80,'After measurement',26,'Italic',pink)
label(1035,510,'RGB and process data',19,'Sans',red);label(1292,510,'RGB and depth',19,'Sans',red)
poly([(1105,328),(1220,219)],red,2);strip(1153,283,'If measured',39)
label(1161,545,'(b) Two decisions, one action',29,'Sans',blue)
# c: two adjacent rounded explanatory compartments.
panel(7,629,650,331,'(c) Allocate the sensing budget');panel(682,629,752,331,'Choose the correction')
eye(49,682);eye(112,682);label(82,715,'RGB view',23,'Serif',cyan)
poly([(139,691),(191,691)]);block(193,659,191,121,'',paper)
label(289,683,'Visible cues',24,'Serif');label(289,713,'Clearance and view',17,'Serif')
for j,ht in enumerate([7,13,22,31,22,13,7]):box(232+j*16,758-ht,9,ht,'#75c0c9','#65abb4',1,.6)
crop((1030,643,1234,841),522,658,86,86);label(565,768,'Quota',20,'Serif',green)
poly([(385,706),(432,746),(449,746)]);poly([(525,715),(484,745),(465,745)]);label(453,777,'Score',18,'Serif',cyan)
poly([(85,731),(85,804)]);crop((42,510,469,830),40,810,103,87);label(90,931,'Part type',22,'Serif',green)
box(194,810,446,115,paper,'#74797a',9,1.25)
label(417,834,'Expected gain from measuring this part',20,'Serif');label(416,867,'Priority score and remaining quota',20,'Serif',blue)
label(418,899,'Measure now or keep the first action',18,'Serif',green)
poly([(453,785),(453,807)]);poly([(127,850),(183,751),(191,743)],gray,1.2);label(412,937,'Selective measurement',19,'Serif',cyan)
P5=project('05')
for j,i in enumerate(['E01P02','E00P05','E00P01']):
    image(ImageOps.fit(Image.open(P5/'frames'/(i+'.jpg')),(100,132)),708+82*j,652,79,111)
label(742,797,'Part',20,'Serif','#b38f5d');label(742,821,'prompt',20,'Serif','#b38f5d')
block(790,777,135,70,'RGB + depth','#dcecf8',20);poly([(858,850),(858,875)]);poly([(742,840),(742,877)])
block(699,882,255,69,'Same frozen model','#fdebd2',25)
box(1008,652,236,94,paper,'#73797b',9,1.25);label(1125,673,'Candidate actions',21,'Serif')
for j,(st,fill) in enumerate([('First: RGB','#d6eafd'),('Second: RGB-D','#d8edc6')]):
    box(1020,689+23*j,27,17,fill,ink,3,1.3);label(1146,699+23*j,st,17,'Serif',blue if j==0 else green)
poly([(954,913),(971,883),(992,708),(1008,697)]);poly([(1126,747),(1126,765)],gray,1.15);poly([(1126,819),(1126,835)],gray,1.15);poly([(1376,836),(1420,836),(1420,695),(1411,695)],gray,1.35)
block(1305,658,105,74,'Execute','#fff4c9',21)
crop((1310,72,1720,393),1302,747,100,80)
label(1126,786,'Candidate disagreement',18,'Serif',blue);label(1126,813,'Depth-plane separation',18,'Serif',cyan)
box(1000,836,423,115,paper,'#74797a',8,1.3);label(1210,854,'Action acceptance',22,'Serif')
for j,(st,fill,co) in enumerate([('Gain ≤ 0    Keep first action','#dfedfa',blue),('Gain > 0    Use second action','#e6f2d9',green)]):
    box(1021,874+33*j,36,22,fill,ink,3,1.2);label(1225,886+33*j,st,19,'Sans',co)
# Matched operating points from the equal-call experiment (study 06).
result=read(project('06')/'summary.json')
n=result['n']
panel(7,985,1426,330,'(d) First-pass seating at equal model-call budget')
label(446,1034,'300 parts   ·   240 second calls   ·   540 calls per policy',19,'Sans',blue)
keys=['rgb_switch','depth_switch','depth_gate']
names=['Repeat RGB · switch','Add depth · switch','Add depth · allow retention']
counts=[result['sol'][key]['ok'] for key in keys]
x0=288; scale=4.45
for tick in (0,25,50,75,100):
    x=x0+tick*scale
    poly([(x,1060),(x,1228)],'#e2e8ea',0.8,False)
    label(x,1242,str(tick)+'%',14,'Sans',gray)
for j,(name,ok,fill) in enumerate(zip(names,counts,['#f6afb3','#d1efb9','#acd0e8'])):
    y=1080+59*j; rate=100*ok/n
    label(x0-15,y,name,19,'Sans',ink,'right')
    box(x0,y-14,rate*scale,28,fill,ink,0,1.15)
    label(x0+rate*scale+9,y,f'{rate:.1f}%  ({ok}/{n})',17,'Bold',navy,'left')
poly([(x0,1225),(x0+100*scale,1225)],ink,1,False)
poly([(850,1016),(850,1301)],edge,1,False)
stages = ['initial','descent','seated']
tile = 144
for col, stage in enumerate(stages):
    label(972 + 149*col + tile/2,1008,stage.capitalize(),18,'Bold',blue)
for row,(case,title) in enumerate([('E00P02','Square bore'),('E00P05','Round bore')]):
    y = 1020 + 147*row
    label(961,y+tile/2,title,17,'Bold',blue,'right')
    for col,stage in enumerate(stages):
        with Image.open(O/'task-process'/f'{case}-{stage}.png') as frame:
            image(frame,972 + 149*col,y,tile,tile)
c.showPage();c.save()
doc=pymupdf.open(O/'fig1-overview.pdf');doc[0].get_pixmap(matrix=pymupdf.Matrix(2,2)).save(O/'fig1-overview.png')
doc[0].get_pixmap().save(D/'tmp/pdfs/fig1-preview.png')

