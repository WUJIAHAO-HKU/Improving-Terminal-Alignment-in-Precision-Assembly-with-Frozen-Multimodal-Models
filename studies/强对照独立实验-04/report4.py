"""Typeset the evidence, budget frontier, and actual simulator replays in a CJK PDF."""
from collections import Counter
from pathlib import Path
from xml.sax.saxutils import escape
from PIL import Image,ImageDraw,ImageFont
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph,Spacer,Table,TableStyle,SimpleDocTemplate,PageBreak,Image as PDFImage
from rules4 import D,OLD,read

FONT='msyh.ttc'
names={'square':'方孔','round':'圆孔','dual':'持件轴孔'}
def plot(s):
    plt.rcParams['font.family']=font_manager.FontProperties(fname=FONT).get_name()
    plt.rcParams['axes.unicode_minus']=False
    fig,ax=plt.subplots(figsize=(8.6,4.0))
    for field,label,col in [('ours','新排序＋新门控','#116b67'),('oldrank_newgate','旧排序＋新门控','#b77330'),('old','旧排序＋旧门控','#747f9b')]:
        ax.plot(range(0,101,10),[s['budgets'][str(k)][field]/4 for k in range(11)],label=label,color=col,marker='o',ms=3.5)
    ax.axhline(s['strong']/4,ls='--',c='#28343d',label='强对照：全测＋新门控')
    ax.axhline(s['strong']/4-5,ls=':',c='#777777',label='强对照点估计减 5 个百分点')
    ax.set(xlabel='每 100 件的额外测量次数',ylabel='严格就位率（%）')
    ax.grid(axis='y',alpha=.17);ax.legend(fontsize=8,frameon=False,ncol=2)
    fig.tight_layout();fig.savefig(D/'budget-frontier.png',dpi=200);plt.close(fig)
def montage(cases,examples):
    groups=examples[::2]
    board=Image.new('RGB',(1300,220*len(groups)),'white')
    draw=ImageDraw.Draw(board);font=ImageFont.truetype(FONT,19)
    for i,ex in enumerate(groups):
        r=cases[ex['id']];y=220*i
        draw.text((5,y+3),r['id']+'  '+ex['category'],font=font,fill='#1f3537')
        im=Image.open(D/'frames'/(r['id']+'.jpg'));im.thumbnail((172,172));board.paste(im,(5,y+37))
        for j,(mode,label) in enumerate([('direct','原动作'),('always','补测动作')]):
            score=r['scores'][mode];x=282+j*506
            draw.text((x,y+3),f"{label}　{'就位' if score['success'] else '失败'}　末态高度 {score['height']:.1f} mm",font=font,fill='#1f3537')
            im=Image.open(D/'failure_views'/f'{i*2+j:02d}.jpg');im.thumbnail((476,172));board.paste(im,(x,y+37))
    board.save(D/'failure-cases.jpg',quality=95)
def main():
    s=read(D/'summary.json');cases={r['id']:r for r in read(D/'case-outcomes.json')};dev=read(D/'development-audit.json')
    examples=read(D/'failure_views.json');assert examples==read(D/'to_capture.json')
    plot(s);montage(cases,examples)
    pdfmetrics.registerFont(TTFont('MSYH',FONT,subfontIndex=0))
    styles=[ParagraphStyle(str(i),fontName='MSYH',fontSize=size,leading=lead,spaceAfter=space,wordWrap='CJK',textColor=colors.HexColor(col)) for i,(size,lead,space,col) in enumerate([(10,16,7,'#233436'),(14,21,8,'#174f4d'),(21,28,9,'#174f4d'),(8.4,13,5,'#405858')])]
    story=[]
    def p(v,i=0):story.append(Paragraph(escape(v),styles[i]))
    def pic(path,w,h):
        a,b=ImageReader(str(path)).getSize(); fac=min(w*mm/a,h*mm/b);story.extend([PDFImage(str(path),a*fac,b*fac),Spacer(1,2*mm)])
    def tab(data):
        tb=Table(data,hAlign='LEFT');tb.setStyle(TableStyle([('FONTNAME',(0,0),(-1,-1),'MSYH'),('FONTSIZE',(0,0),(-1,-1),8.5),
         ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#d8e9e6')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f3f6f5')]),
         ('ALIGN',(0,0),(-1,-1),'CENTER'),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4)]));story.extend([tb,Spacer(1,3*mm)])
    p('减少测量后，还能达到全测门控的就位率吗？',2)
    p('实验 04　|　冻结 GPT-6.2 Sol　|　40 个独立批次，共 400 件',1)
    p(f"强对照对每件都补测，并由同一道门控决定保留原动作或接受新动作，成功 {s['strong']}/400（{s['strong']/4:.1f}%）。仅 RGB 原动作成功 {s['direct']}/400，全测后直接换动作成功 {s['always']}/400。理想纠偏成功 {s['oracle']}/400。")
    arr=[['少测','实际测量','就位','差值 / pp','单侧下限 / pp','单侧 p','序贯结论']]
    for k in [8,6]:
        b=s['budgets'][str(k)];v=b['vs_strong']
        arr.append([f'{100-10*k}%',b['measured'],f"{b['ours']}/400",f"{v['diff']:+.2f}",f"{v['lower']:+.2f}",f"{v['p']:.4g}" if v['p'] is not None else '—',b['status']])
    tab(arr)
    p('差值为省测组减强对照，单位为百分点。非劣界为 −5。确认顺序为先少测 20%、再少测 40%，若第一档未通过，第二档仅描述。',3)
    for k in [8,6]:
        b=s['budgets'][str(k)];v=b['vs_strong']
        p(f"少测 {100-10*k}% 时，两策略逐例胜／负为 {v['wins']}／{v['losses']}。批次 bootstrap 单侧 95% 下限为 {v['boot']:+.2f} 个百分点。已测零件中，门控保留了 {b['kept']} 个原动作，挽回 {b['good_keep']} 件，同时误拒 {b['wrong_reject']} 个本可成功的修正。")
    p('实验口径',1)
    p('新种子生成三类几何。每批 10 件，每类至少 3 件；五档单边间隙从 0.25 至 4 mm。俯角从此前未见的 5°、11°、23°、35°、43°、49° 中抽取。装夹抬高 6–48 mm，接近高度 34–52 mm，具体值重新抽样，与旧范围有重叠。')
    p('服务器执行每例原动作、补测动作及理想纠偏共 1,200 次，全部样本进入分母。Sol 候选来自 800 次独立匿名图像推理，原动作看不到深度。资金与时延未计入；节省百分比按部署时额外深度采集数核算。')
    story.append(PageBreak());p('开发集复盘｜120 个跳过样本中的损失',2)
    p('上一轮测 180/300 件。预算外有 26 件原动作失败而补测动作成功，其中 19 件为方孔、7 件为圆孔。若对全部零件启用上一轮门控，14 件会接受成功修正，12 件仍会误拒；另外有 2 件因跳过有害修正而保住成功。故预算组比旧强对照净少 12 件，221 对 233。')
    for label in ['漏测·强对照会采用','漏测·强对照也会拒绝','跳过有害修正','已测误拒']:
        items=[x for x in dev if x['label']==label]
        p(f"{label}（{len(items)} 件）",1)
        p('、'.join(r['id'] for r in items),3)
    p('第三轮已测误拒仅 1 件。C23P03 的圆孔单边间隙 4 mm、俯角 42°。原动作 [−8.0, −8.7] mm 后悬停，补测动作 [−8.7, 2.4] mm 后就位，旧门控却保留了原动作。这个错误同时发生在省测组和全测门控组。')
    p('据此冻结的两项改动',1)
    p('分配测量时，除图像梯度、间隙和俯角外，加入免费可得的 RGB 原动作、动作超过开发集典型范围的程度及几何交互；每批先保障三类各一件，再按预测收益分配。上一轮在 101 个方孔中仅测 11 件，漏掉了强对照会挽回的 9 件。')
    p('接受新动作时，加入原动作和新动作各自的越界量、修正方向与俯角的关系，以及修正量相对深度视差的尺度。预测净增益大于零才换动作。两道岭回归仅使用前两轮共 600 件开发样本，测量前模型的目标通过按开发批次留一得到。')
    story.append(PageBreak());p('测量预算曲线与规则消融',2)
    pic(D/'budget-frontier.png',174,90)
    p('图 1　每一档均对同一批 400 件回放。点估计与界线的距离描述成功率；非劣判定使用第一页的配对置信下限。',3)
    arr=[['每批测几件','旧排序＋旧门控','旧排序＋新门控','新排序＋新门控','全测＋新门控']]
    for k in range(11):
        b=s['budgets'][str(k)];arr.append([k,b['old'],b['oldrank_newgate'],b['ours'],s['strong']])
    tab(arr)
    change=s['strong_change'];p(f"全测时的新／旧门控成功数分别为 {s['strong']} 和 {s['oldstrong']}；新减旧 {change['diff']:+.2f} 个百分点，双侧 95% 配对区间 [{change['ci'][0]:+.2f}, {change['ci'][1]:+.2f}]。旧规则在同批新样本上重放；跨轮成功率受样本组成影响。",3)
    story.append(PageBreak());p('少测 40%｜按几何拆解预算损失',2)
    b=s['budgets']['6'];v=b['vs_strong']
    tab([['几何','样本','已测','预算组就位','强对照就位','漏测且强对照挽回']]+[[names[t],x['n'],x['selected'],x['ours'],x['strong'],x['skip_loss']] for t,x in b['by_task'].items()])
    p(f"跳过的 160 件中，有 {b['skip_potential']} 件的补测动作本可将失败变为成功。其中 {b['skip_shared_reject']} 件全测门控也会拒绝，另 {b['skip_relative_loss']} 件构成相对强对照的损失。跳过有害修正挽回 {b['skip_relative_gain']} 件。已测件采用相同门控，对两组差值的贡献严格为零。")
    p(f"固定新门控，仅替换排序，在这个预算的成功数变化为 {b['ours']-b['oldrank_newgate']:+d}；固定旧排序，仅替换门控，变化为 {b['oldrank_newgate']-b['old']:+d}。这是描述性消融，不能单独识别各个输入特征的贡献。")
    p('推断范围及复核方式',1)
    p('差异以每批十件的配对就位率差为单位，取 40 批平均。单侧 95% t 下限使用 39 个自由度；对批次整体有放回抽样 50,000 次作敏感性分析。其余预算、按任务拆分和历史规则消融均为描述性结果。')
    p('估计对象为指定三类几何及其随机条件下的末段就位。自由释放套柱与持件几何夹具均在仿真中执行。本实验没有估计换用其他工件、全流程抓取或真机时的成功率，也没有把模型解码随机性与补测信息的作用完全分离。')
    p('复核材料',1)
    p('protocol.txt 记录检验顺序和非劣界。policy-lock.json 保存测前锁定的权重及源码摘要。decisions.json 和 before-replay.json 保存执行前的逐件排名、接受决策和文件校验值。development-audit.json 与 case-outcomes.json 分别给出开发集归因以及本轮逐件动作和末态。',3)
    story.append(PageBreak());p('少测 40%｜真实仿真回放',2)
    pic(D/'failure-cases.jpg',174,125)
    p('图 2　每类取按编号排序的首例。左列为决策前输入，其余列分别为两个候选动作的末态双视角。套柱高度相对桌面，持件夹具高度相对柱顶。',3)
    for e in examples[::2]:
        r=cases[e['id']];x=r['scores']['direct'];y=r['scores']['always']
        p(f"{r['id']}　{e['category']}。{names[r['task']]}，{r['gap']:g} mm、{r['angle']:g}°，批内排名 {r['rank']}/10。原动作 {x['action']} mm，补测动作 {y['action']} mm；末态横向偏差分别为 {x['lateral']:.2f} 和 {y['lateral']:.2f} mm。",3)
    def footer(canvas,doc):
        canvas.setFont('MSYH',8);canvas.setFillColor(colors.HexColor('#57696a'));canvas.drawString(18*mm,11*mm,'通用模型装配诊断　|　强对照独立实验 04');canvas.drawRightString(192*mm,11*mm,str(doc.page))
    out=D/'output/pdf/全测门控强对照独立验证.pdf';out.parent.mkdir(parents=True,exist_ok=True)
    SimpleDocTemplate(str(out),pagesize=A4,topMargin=15*mm,bottomMargin=18*mm,leftMargin=18*mm,rightMargin=18*mm,title='全测门控强对照独立验证').build(story,onFirstPage=footer,onLaterPages=footer)
if __name__=='__main__':main()
