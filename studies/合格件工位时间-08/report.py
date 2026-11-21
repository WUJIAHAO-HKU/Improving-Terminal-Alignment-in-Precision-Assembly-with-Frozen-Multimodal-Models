from timing import D,read
from deployment import METHODS,envelope,coefficients,station
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image
grp=read(D/'summary.json')['groups'];g=grp['all']
O=D/'output';dest=O/'pdf';dest.mkdir(parents=True,exist_ok=True)
c=Canvas(str(dest/'每个合格件的工位占时与部署边界.pdf'),pagesize=(595,842))
c.setTitle('混流装配中每个合格件的工位占时与部署边界')
for name,path in [('r','msyh.ttc'),('b','msyhbd.ttc')]:pdfmetrics.registerFont(TTFont(name,''+path))
names=['纯 RGB 几何','Sol 少测组','Sol 主预算','Sol 全测']
def txt(x,y,s,n=10,b=False,color='#153445'):
    f='b' if b else 'r';assert x+pdfmetrics.stringWidth(s,f,n)<576,(s,x)
    c.setFillColor(HexColor(color));c.setFont(f,n);c.drawString(x,842-y,s)
def rule(y):
    c.setStrokeColor(HexColor('#c6d7d4'));c.line(38,842-y,557,842-y)
def section(y,s):txt(38,y,s,14,True,'#006654')
def lines(y,items):
    for j,s in enumerate(items):txt(38,y+18*j,s)
def page(n,title,sub):
    txt(38,42,'混流装配工位    /    实验 08     ·     逐件配对成本分析',10,True,'#006654')
    txt(38,85,title,23,True);txt(38,110,sub,10);rule(130)
    rule(796);txt(38,816,'方孔 150 件，圆孔 90 件    ·    30 个原始批次    ·    仿真配对分析',9);txt(520,816,f'{n} / 3',9)
def table(y,x,heads,rows,step=28):
    c.setFillColor(HexColor('#e3f0ec'));c.rect(38,842-y-8,519,24,fill=1,stroke=0)
    for px,s in zip(x,heads):txt(px,y,s,9,True)
    for j,r in enumerate(rows,1):
        for px,s in zip(x,r):txt(px,y+step*j,str(s),10)
        rule(y+step*j+8)
def cross(a,b):return g['comparisons'][a+'_'+b]['cross_minutes']
def svalue(m,r):return station(grp,m,r,100,0)
page(1,'每交付一个合格件，占用工位多少秒？','同一批零件、同一首次就位判据，比较已标定几何法与三档冻结 Sol 策略。')
section(163,'每件都交付，首次失败计入返工')
lines(190,['计量单位为秒 / 最终合格件。假设首次失败后经一次综合返工最终合格，返工占用本工位。',
           '表中列出可比较的决策与返工占时。完整工位时间还要加各方案共有的取放、运动、',
           '释放、判定时间及共同设置摊销。当前无现场计时，全部按增量报告。'])
rows=[]
for m,name in zip(METHODS,names):
 v=g[m];rows.append([name,v['measured'],v['calls'],v['ok'],f"{v['base']:.2f}",f"{100*v['f']:.1f}%"])
table(291,[43,153,220,293,367,480],['方法','补测件数','逻辑调用','首次就位','决策秒/件','返工比例'],rows)
section(457,'相同设置时间，不同返工负担')
table(491,[43,188,278,370,470],['每次失败占线','几何','Sol 少测','Sol 主预算','Sol 全测'],
 [[f'{r} 分钟']+[f'{svalue(m,r):.1f}' for m in METHODS] for r in [5,30,60,90]],25)
lines(631,[f"按历史日志估计，几何与全测的平均时间在每次失败占线约 {cross('geo','sol10'):.1f} 分钟时相交。",
           '在当前配比、相同设置与串行调用下，四种策略的最短时间由几何与全测两条线给出。',
           '少测组及主预算组仍可用于补测容量有限、或几何法需额外占线调试的工位。'])
section(723,'为什么用 240 件作分母')
lines(751,['仅纳入按同一协议验证过几何基线的方孔与圆孔。三档分别实际补测 124、182、240 件。',
           '少测两组继承原十件混流批的名单；既未重排，也未给排除的持件任务重新分配配额。'])
c.showPage()
page(2,'换型、配比与调用延迟如何改变选择','彩色区域给出四种方案中平均占时最短的一种。横纵轴都是占用瓶颈工位的时间。')
img=O/'deployment-frontier.png'; iw,ih=Image.open(img).size
c.drawImage(str(img),32,842-156-531*ih/iw,width=531,height=531*ih/iw)
yy=367
section(yy,'把“高混流”换算成每件设置差额')
lines(yy+29,['设一次新建或重新验证配方，几何相对 Sol 多占线 H 分钟，之后可累计复用 L 件。',
              '图 B 纵轴为 H/L。已验证配方切换且可直接复用时，该次差额可为零。两边都需',
              '设置，计入的是净差；离线编程工时须与阻塞工位的调试时间分开。'])
def threshold(r):
    vals=[svalue(m,r) for m in METHODS[1:]];v=min(vals);i=vals.index(v)
    return names[i+1],(v-svalue('geo',r))/60
table(485,[42,158,271,419],['失败占线','最快 Sol 策略','所需设置差/件','100 件所需设置差'],
 [[f'{r} 分钟',threshold(r)[0],f'{threshold(r)[1]:.2f} 分钟',f'{100*threshold(r)[1]:.1f} 分钟'] for r in [5,15,30]],24)
section(603,'产品比例与推理耗时的敏感性')
for j,(lab,share,k) in enumerate([('方孔为主（80%）',.8,1),('圆孔为主（方孔 20%）',.2,1),('基准配比，推理耗时减半',.625,.5)]):
    env=envelope(grp,share,k)
    line=' → '.join(names[METHODS.index(m)] if n==0 else f'{l:.1f} 分后 {names[METHODS.index(m)]}' for n,(l,_,m) in enumerate(env))
    txt(38,632+j*23,lab+'　'+line,10)
lines(724,['配比结果只重加权原样本的形状分层，未重跑新批次的配额或换型顺序。调用耗时减半',
           '是情景假设，前提是候选动作质量不变。机床若可并行推理，应代入实际阻塞秒数。'])
c.showPage()
page(3,'估计的不确定性与现场使用方法','先判断良率与测量容量是否允许，再在可行方案中比较每件占线时间。')
section(167,'同一返工情景下，时间差有多确定？')
rows=[]
for r in [5,30,60,90]:
    st=g['comparisons']['geo_sol10']['grid'][str(r)];lo,hi=st['ci']
    rows.append([f'{r} 分钟',f"{st['delta_s']:+.1f}",f'{lo:+.1f} 至 {hi:+.1f}'])
table(207,[44,198,372],['失败占线','全测减几何（秒/件）','配对 95% 区间'],rows,25)
lines(343,['按 30 个原始批次进行 10,000 次配对自助重采样。区间给定同一返工时间和设置时间。',
           '它表征样本与其日志的批间变动。服务商负载漂移、修复率和真实返工耗时仍需外部测量。',
           '交点是样本均值推算；若区间跨零，应将该情景列为方案排序尚不确定。'])
section(433,'部署计算式与容量约束')
lines(462,['每合格件秒数 = 共同运动秒数 + 决策秒数 + 首次失败比例 × 每次返工占线秒数',
           '　　　　　　　 + 本方案占线设置秒数 / 配方累计复用件数。',
           '比较同一设置与运动时，共同项可抵消。若有报废或返工未必成功，须重新计入实际',
           '合格产出；返工在另一工位时，只将本工位被阻塞的部分代入，并另查返工站容量。',
           '对目标节拍 C 秒/件，所选方法的总占时须低于 C 才有平均余量；排队波动另行评估。',
           f'若每 240 件最多补测 182 件且设置相同，主预算比几何省时的点估计门槛为 {cross("geo","sol8"):.1f} 分钟。'])
section(606,'哪些时间经过实测')
lines(634,['采用 05 轮逐件 RGB、RGB-D 采集时间和 Sol 请求墙钟（含重试）；同件第一请求共享。',
           '重计已标定几何的纯 RGB 路径，含解码、定位与纠偏。240 件各运行 3 次取中位数，',
           '每次核对原动作。另计 Sol 本地观测质量、选件和接受规则时间。未计仿真积分墙钟。',
           '本地 CPU、仿真采集与远端服务耗时来自不同环节；不构成实物工位节拍实测。',
           '比较限于冻结 Sol、已知工件、受控末端平移。高混流本身不保证采用大模型更快。'])
txt(38,765,'复算数据见同目录的逐件记录、计时原始值、统计脚本及部署情景计算器。',9)
c.showPage();c.save()

