"""Render the paired simulation comparison and matched replay views."""
from io import BytesIO
from pathlib import Path
import json
from PIL import Image, ImageDraw
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

D=Path(__file__).resolve().parent
P=D.parent/'工位补充实验-05'
O=D/'output'/'pdf'
O.mkdir(parents=True,exist_ok=True)
def read(name):
    return json.loads((D/name).read_text(encoding='utf-8'))
s=read('summary.json'); b=s['budgets']; cases=read('case-outcomes.json')
pdfmetrics.registerFont(TTFont('ya','msyh.ttc'))
pdfmetrics.registerFont(TTFont('yb','msyhbd.ttc'))
w,h=595,842
c=Canvas(str(O/'孔柱中心定位与几何纠偏基线.pdf'),pagesize=(w,h))
c.setTitle('孔柱中心定位与几何平移纠偏｜仿真对照实验')
ink='#172E41'; accent='#006F69'; muted='#486373'
def txt(x,y,t,size=10,color=ink,bold=False):
    c.setFillColor(HexColor(color));c.setFont('yb' if bold else 'ya',size);c.drawString(x,h-y,t)
def line(x1,y1,x2,y2,color='#D6DFE0'):
    c.setStrokeColor(HexColor(color));c.line(x1,h-y1,x2,h-y2)
def page(k,title,sub):
    txt(40,38,'精密装配研究   /   工位仿真   /   实验 07',10,accent,True)
    txt(40,83,title,24,ink,True);txt(40,111,sub,10,muted)
    line(40,131,555,131)
    line(40,797,555,797);txt(40,817,'同件配对    ·    自由释放    ·    独立于标定集',9,muted);txt(509,817,f'{k} / 3',9,muted)
def section(y,t):txt(40,y,t,14,accent,True)
def lines(y,ss):
    for j,t in enumerate(ss):txt(40,y+j*18,t,10)
def table(y,heads,rows,xx,step=26):
    c.setFillColor(HexColor('#E5F1EF'));c.rect(40,h-y-7,515,23,fill=1,stroke=0)
    for x,t in zip(xx,heads):txt(x,y,t,9,accent,True)
    for j,row in enumerate(rows,1):
        for x,t in zip(xx,row):txt(x,y+j*step,t,10)
        line(40,y+j*step+8,555,y+j*step+8)
page(1,'孔柱中心定位能做到什么程度？','在同一批方孔、圆孔及相同测量名单上，对照几何平移与冻结 Sol 的动作。')
section(169,'主结果　两种方法在 46 件上给出不同的就位结果')
lines(197,['沿用原混流工位每 10 件测 8 件的名单。在纳入的 240 件中，实际补测 182 件（75.8%）。',
           '标定几何基线就位 194 件（80.8%），Sol 允许保留原动作时就位 200 件（83.3%）。',
           'Sol 减几何为 +2.5 个百分点，30 批配对双侧 95% 区间为 −2.3 至 +7.3 个百分点。',
           '逐件比较，174 件都成功，20 件仅几何成功，26 件仅 Sol 成功，20 件都失败。'])
section(302,'预算曲线　严格首次就位件数 / 240')
rows=[]
for k,name in [('0','只用 RGB'),('6','原批测 6/10'),('8','原批测 8/10'),('10','全部测量')]:
    v=b[k]; n=v['counts'];rows.append((name,str(v['measured']),str(n['cv_raw']),str(n['cv']),str(n['sol_switch']),str(n['sol'])))
table(337,['测量名单','实测件数','几何·未校准','几何·校准','Sol·均换','Sol·可保留'],rows,[45,150,221,314,400,475])
section(490,'怎样读这组对照')
lines(520,['只用 RGB 时，校准几何比 Sol 直接动作多就位 19 件。同一 182 件得到补测后，',
           'Sol 一律换用第二动作时成功 186 件；允许保留原动作后，净增加 14 件。',
           '几何方法在只用 RGB 和主预算时都成功 194 件。深度补测未提高其总体成功数。',
           '去掉开发集残差校准后，主预算几何成功数从 194 降为 134。比较应采用校准版。',
           '依据主比较的区间，目前不能判定 Sol 在目标预算下优于校准几何。'])
section(654,'范围与判据')
lines(682,['30 个批次各取 5 个方孔和 3 个圆孔，排除使用持件夹具的 60 个场景。根据原名单',
           '取交集，未补足配额。各方法从相同姿态执行一次水平平移，再由 MuJoCo 模拟释放。',
           '成功同时要求终态高度在 8 至 12.5 mm 之间，倾角小于 4°，侧偏不超过单边间隙',
           '加 0.35 mm，且末段稳定。理想真值纠偏成功 240/240。'])
c.showPage()
page(2,'平移纠偏的实现与适用范围','几何分层与间隙分层均使用同一份 182 件补测名单。')
section(164,'两中心反投影到各自的水平面')
lines(192,['利用相机俯角、内参、工件 CAD 和材料外观拟合孔轮廓。屏蔽工件遮挡区域，',
           '用可见柱顶及侧边拟合柱心；将两条像素射线各自反投影，以水平坐标差给出动作。',
           '补测时可用的额外输入和 Sol 相同，均为两个带噪深度平面读数。几何法用实验 03',
           '的 202 个历史场景估计高度先验及系统偏差；实验 05 的测试种子与其无交集。',
           '执行前锁定代码和参数，估计器没有读取测试真值偏移或装夹高度。所有件均生成定位。'])
section(312,'装配形状与单边间隙')
sub=b['8']['subset']
rr=[]
for k,name in [('square','方孔'),('round','圆孔'),('gap4','4.00 mm'),('gap2','2.00 mm'),('gap1','1.00 mm'),('gap0.5','0.50 mm'),('gap0.25','0.25 mm')]:
    v=sub[k];rr.append([name,str(v['n']),str(v['measured']),str(v['cv']),str(v['sol']),f"{v['sol']-v['cv']:+d}"])
table(345,['分组','件数','实测','几何就位','Sol 就位','Sol 净增'],rr,[46,150,228,301,389,469],22)
section(548,'动作误差与就位率衡量不同的环节')
lines(576,['在主预算下，执行前平移残差（到理想纠偏的欧氏距离）的中位数，几何为 1.41 mm，',
           'Sol 为 0.65 mm；第 90 百分位分别为 4.37 和 3.59 mm。接触和释放也会影响终态。',
           '在 1.0 和 0.5 mm 的间隙上，Sol 各多成功 5 件。在 0.25 mm 上两者各成功 6/23，',
           '只有 1 件共同成功。该层有 5 件仅几何成功，也有 5 件仅 Sol 成功。'])
section(679,'比较边界')
lines(707,['几何法额外使用精确 CAD、材料外观和有真值的离线标定，代表工件资料齐备的工位。',
           '测量名单由既有 Sol 策略给定；本实验比较同名单下的动作，不估计几何法自选件的效果。',
           '测试批已用于先前研究，本轮是新增基线的配对回放。视角和间隙分层均作描述性分析。'])
c.showPage()
page(3,'同件回放中的成功与失败','每类取按编号排序的首个样本。输入图的青圈为估计孔心，橙色十字为估计柱心。')
txt(42,153,'执行前 RGB 与中心估计',10,muted,True)
txt(208,153,'几何动作后的终态',10,muted,True)
txt(386,153,'Sol 动作后的终态',10,muted,True)
for j,((label,i),title) in enumerate(zip(s['examples'].items(),['仅几何成功','仅 Sol 成功','两者均失败','两者均成功'])):
    y=165+j*152
    v=cases[i];dec=v['decisions']['8']; m=dec['modes']
    inp=Image.open(P/'frames'/(i+'.jpg')).convert('RGB')
    d=ImageDraw.Draw(inp);u,vv=v['localization'][m['cv']]['hole_uv'];px,py=v['localization'][m['cv']]['peg_uv']
    d.ellipse((u-8,vv-8,u+8,vv+8),outline='#00FAE5',width=4)
    d.line((px-10,py,px+10,py),fill='#FF8722',width=4);d.line((px,py-10,px,py+10),fill='#FF8722',width=4)
    for a,img in enumerate([inp]+[Image.open(D/'failure_views'/f'{j*2+t:02d}.jpg').crop((240,0,480,240)) for t in (0,1)]):
        c.drawImage(ImageReader(img),[42,214,390][a],h-y-80,80,80)
    ty=y+99
    txt(42,ty,title+'   '+i,11,accent,True)
    typ='方孔' if v['task']=='square' else '圆孔'; sensor='有补测' if dec['measured'] else '仅 RGB'
    txt(218,ty,f"{typ}   ·   {v['gap']:g} mm   ·   {v['angle']:g}°   ·   {sensor}",10)
    for a,method in enumerate(['cv','sol']):
        r=v['outcomes'][m[method]];err=dec['geometric_error' if a==0 else 'sol_error']
        txt(42+a*243,ty+20,f"{['几何','Sol'][a]}　动作残差 {err:.2f} mm，终高 {r['height']:.2f} mm",9)
    line(40,ty+32,555,ty+32)
txt(40,782,'终态取同一侧视角。输入图上的中心为算法估计值，判据使用物理回放的终态。',9,muted)
c.showPage();c.save()

