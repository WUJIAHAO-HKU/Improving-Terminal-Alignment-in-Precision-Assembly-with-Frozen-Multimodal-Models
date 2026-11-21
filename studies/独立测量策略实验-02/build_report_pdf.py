"""Typeset the round-02 report with full results and the locked round-03 protocol."""
from pathlib import Path
from html import escape
import json
import re
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak

d=Path(__file__).resolve().parent
pdfmetrics.registerFont(TTFont('Yahei','msyh.ttc',subfontIndex=0))
styles={name:ParagraphStyle(name,fontName='Yahei',fontSize=size,leading=lead,wordWrap='CJK',spaceAfter=space,textColor=colors.HexColor(color)) for name,size,lead,space,color in [('title',21,29,10,'#173f42'),('section',15,21,8,'#173f42'),('head',11,16,4,'#315659'),('body',9.3,15,5,'#28373b'),('caption',8,12,8,'#4d6267')]}
s=[]
def p(t,style='body'):
    s.append(Paragraph(escape(t),styles[style]))
def pic(path,width,height):
    w,h=ImageReader(str(path)).getSize()
    scale=min(width*mm/w,height*mm/h)
    s.append(Image(str(path),w*scale,h*scale))
def table(data):
    t=Table(data,hAlign='CENTER')
    t.setStyle(TableStyle([('FONTNAME',(0,0),(-1,-1),'Yahei'),('FONTSIZE',(0,0),(-1,-1),8.3),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dcebe7')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f2f6f6')]),('ALIGN',(0,0),(-1,-1),'CENTER'),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4)]))
    s.extend([t,Spacer(1,8)])
summary=json.loads((d/'summary.json').read_text())
p('精密装配中，测量预算该花在哪里？','title')
p('独立测试 02  ·  GPT-6.2 Sol  ·  300 个仿真场景','head')
p('每批 10 件中选 6 件补测时，公差规则成功 123 次，视角规则和联合规则各成功 121 次；始终测量成功 141 次。上一轮数据拟合的联合规则在新样本上没有超过两个简单规则。')
pic(d/'architecture-final.png',174,76)
p('图 1　末段装配方法示意。此图为生成式架构示意，实测数据见第 2–4 页。','caption')
p('从直接控制到动作接受','section')
p('实验 01 中，直接 Sol 成功 70/120，始终测量 104/120，按需测量 96/120。方孔在 2 mm 为 8/8，在 1 mm 为 7/8，首次跌破预设的 90% 线。圆孔和持件夹具在最宽的 4 mm 已低于这条线。每档仅 8 例，数据只能定位观测档位。')
p('实验 02 改用 30 个独立批次，每批 10 件。在看到结果前固定排序，然后在同一批内分配相同测量次数。任务包括方孔套柱、圆孔套柱、持件轴孔。单边间隙为 0.25、0.5、1、2、4 mm，视角为 8°、14°、26°、38°、45°。夹具抬高 10–42 mm，接近高度 36–50 mm。')
p('公差规则优先小间隙，视角规则优先大俯角。联合规则用间隙、俯角和初始图像梯度预测补测收益，仅用实验 01 的 120 个样本拟合。所有策略共用同一场景的两种候选动作，分别在独立提示中获得，并用同一执行器回放。')
p('本轮给下一轮留下了两个不同的问题：哪些零件值得测量，测完后哪些新动作值得执行？第 5 页给出独立验证方案。')
s.append(PageBreak())
p('同一测量预算下的严格就位率','title')
pic(d/'budget-frontier.png',170,102)
p('图 2　横轴为每 100 件的额外测量次数，纵轴为严格就位率。虚线是始终采用补测动作的参照。','caption')
arr=[['每批测量','总次数','公差','视角','联合','拟合仅公差','拟合仅视角']]
for k in range(3,10):
    v=summary['budgets'][str(k)]['counts']
    arr.append([k,30*k]+[v[m] for m in ('clearance','view','joint','fit_clearance','fit_view')])
table(arr)
p('表内结果为 300 件中的成功数。仅 RGB 成功 114/300，始终测量 141/300，理想纠偏 300/300。拟合对照采用与联合规则相同的学习器。')
p('60% 主预算下，联合减公差为 −0.67 个百分点（双侧 95% 区间 −4.93 至 3.60，逐件胜/负 21/23）；联合减视角为 0.00 个百分点（−2.77 至 2.77，胜/负 9/9）。两项单侧优效检验 Holm 校正后 p 均为 1。')
s.append(PageBreak())
p('哪些节省比例得到非劣证据','title')
p('非劣界为严格就位率最多下降 5 个百分点。实验 02 采用以批次为单位的单侧 e 检验，e ≥ 20 通过；按少测 10% 至 70% 的顺序检验，首次失败即停止后续正式判定。')
arr=[['少测','联合减始终 / pp','胜 / 负','单侧 t 下限 / pp','e 值','序贯判定']]
for k in range(9,2,-1):
    b=summary['budgets'][str(k)]; v=b['vs_always']
    arr.append([f'{100-10*k}%',f"{v['diff_pp']:.2f}",f"{v['wins']} / {v['losses']}",f"{v['lower95_pp']:.2f}",f"{b['e']:.4g}",'通过' if b['ni_pass'] else '未通过' if b['eligible'] else '仅描述'])
table(arr)
p('已确认的最大节省比例为 10%。少测 20% 时联合策略少成功 10 件，证据不足；少测 40% 时少成功 20 件，该档只作描述。','head')
p('60% 测量预算的分任务结果','section')
arr=[['几何','件数','仅 RGB','公差','视角','联合','始终测量']]
for t,n in [('square','方孔'),('round','圆孔'),('dual','持件夹具')]:
    b=summary['by_task'][t]; arr.append([n]+[b[m] for m in ('n','direct','clearance','view','joint','always')])
table(arr)
p('圆孔的联合规则仅成功 37/98，公差规则为 49/98；持件夹具中联合规则为 36/101，公差规则为 26/101。汇总均值掩盖了两组方向相反的差异。')
p('所有场景均保留。两种螺母任务采用理想末段平移后自由释放，持件任务采用几何进给夹具。结论覆盖已测几何和装夹范围；完整抓取链、双臂闭环、真实传感器节拍和真机仍待验证。')
s.append(PageBreak())
p('失败案例：同一零件，两种动作','title')
pic(d/'failure-cases.jpg',164,131)
p('图 3　实验 02 的输入和末态回放。案例取自主预算每批测 6 件，排名第 7 及以后跳过测量。','caption')
report=(d/'实验报告.md').read_text(encoding='utf8')
for line in report.splitlines():
    if line.startswith('- **B'):
        p(line[2:].replace('**',''),'caption')
s.append(PageBreak())
p('实验 03：先分配测量，再接受动作','title')
p('研究问题','section')
p('同一场景先由冻结的 Sol 仅凭 RGB 给出原动作。获准补测的零件再获得两项有噪声的平面读数，由独立请求给出新动作。即使某件零件已经测量，控制器仍可执行原动作。这使“选哪件测量”和“是否采纳新动作”可以分别检验。')
p('测试集与冻结规则','section')
p('300 个新种子，30 批 × 10 件，沿用三类几何。每批各类至少 3 件；五档间隙独立抽样，俯角从 6°、12°、22°、34°、42°、50° 中抽取。夹具抬高 6–48 mm，接近高度 34–52 mm。具体装夹高度重新采样，与旧高度范围部分重叠。')
p('使用实验 02 的 300 件拟合两道岭回归规则。第一道根据间隙、俯角、图像梯度和几何类别预测测量收益。第二道根据两动作的差异及深度读数预测换动作的净收益，仅在预测值大于零时接受。训练第一道时按开发批次留一估计第二道决策；新测试集标签不参与拟合。')
p('两项主要比较','section')
p('每批测 8 件和 6 件，与每件都测、都采用新动作配对比较。先检验少测 20%，通过后再正式检验 40%。非劣界为 −5 个百分点，正式判据为 30 个批次配对均值差的单侧 95% t 下限大于该界。另报批次 bootstrap 下限。上一轮 e 检验使用“已测样本的动作必然相同”所导出的差值上界，不能原样套用。')
p('同预算消融共用完全相同的测量名单，唯一改变是启用或关闭动作接受。分别统计保留原动作挽回的成功和误拒新动作导致的失败，并与全量测量也启用门控的强对照比较。')
p('预算按部署策略需要的额外传感器采集次数核算。离线评估对全部场景都采集并回放两种候选，以便逐例配对。这里的 20% 和 40% 表示传感器预算，模型调用次数、时延和整机成本需单独核算。')
def footer(c,doc):
    c.setFont('Yahei',8);c.setFillColor(colors.HexColor('#51676c'))
    c.drawString(18*mm,11*mm,'通用模型装配诊断　|　独立测量策略实验 02')
    c.drawRightString(192*mm,11*mm,str(doc.page))
out=d/'output/pdf/独立测量策略实验报告.pdf'
doc=SimpleDocTemplate(str(out),pagesize=A4,leftMargin=18*mm,rightMargin=18*mm,topMargin=15*mm,bottomMargin=20*mm,title='独立测量策略实验 02')
doc.build(s,onFirstPage=footer,onLaterPages=footer)
