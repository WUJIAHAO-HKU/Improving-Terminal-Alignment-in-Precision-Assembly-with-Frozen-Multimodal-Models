from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.enums import TA_CENTER,TA_LEFT
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Image,Table,TableStyle,PageBreak,KeepTogether
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm
from pathlib import Path
import json
root=Path(Path(__file__).resolve().parent)
out=root/"output/pdf/独立测量策略实验报告.pdf"
pdfmetrics.registerFont(TTFont("MSYH",r"msyh.ttc",subfontIndex=0))
pdfmetrics.registerFont(TTFont("Arial","arial.ttf"))
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name="CNTitle",fontName="MSYH",fontSize=22,leading=30,alignment=TA_CENTER,textColor=colors.HexColor("#1C2430"),spaceAfter=8))
styles.add(ParagraphStyle(name="CNSub",fontName="MSYH",fontSize=10,leading=16,alignment=TA_CENTER,textColor=colors.HexColor("#627080"),spaceAfter=18))
styles.add(ParagraphStyle(name="CNH",fontName="MSYH",fontSize=15,leading=22,textColor=colors.HexColor("#273B4A"),spaceBefore=12,spaceAfter=6))
styles.add(ParagraphStyle(name="CNH2",fontName="MSYH",fontSize=11,leading=17,textColor=colors.HexColor("#3D5B67"),spaceBefore=7,spaceAfter=4))
styles.add(ParagraphStyle(name="CN",fontName="MSYH",fontSize=9,leading=15,textColor=colors.HexColor("#27313A"),spaceAfter=5))
styles.add(ParagraphStyle(name="CNSmall",fontName="MSYH",fontSize=7.7,leading=11,textColor=colors.HexColor("#4D5962"),spaceAfter=3))
styles.add(ParagraphStyle(name="Caption",fontName="MSYH",fontSize=7.7,leading=11,alignment=TA_CENTER,textColor=colors.HexColor("#65747E"),spaceBefore=3,spaceAfter=8))
def P(s,style="CN"): return Paragraph(s,styles[style])
def header_footer(canvas,doc):
    canvas.saveState();canvas.setFont("MSYH",7);canvas.setFillColor(colors.HexColor("#72808A"))
    canvas.drawString(18*mm,12*mm,"Independent assembly measurement-policy study")
    canvas.drawRightString(192*mm,12*mm,f"{doc.page}")
    canvas.setStrokeColor(colors.HexColor("#D8E0E4"));canvas.line(18*mm,16*mm,192*mm,16*mm);canvas.restoreState()
story=[]
story += [P("风险感知测量与动作接受机制","CNTitle"),P("独立装配策略实验报告 · 第二轮测试设计与第一轮实测结果","CNSub")]
story += [Image(str(root/"output/pdf/architecture-final.png"),width=174*mm,height=75*mm),P("图 1  末段装配中的冻结 Sol、几何风险判断、一次测量和动作执行流程。", "Caption")]
story += [P("执行摘要","CNH"),P("上一轮实验显示，Sol 的直接动作在精密装配中存在与公差和视角相关的误差。始终测量达到 141/300，直接控制为 114/300。基于上一轮数据锁定的三种测量优先级在新的 300 个场景上比较。主预算每批 10 件测 6 件时，联合方法成功 121/300，始终测量 141/300，未超过只看公差或只看视角。按预注册的非劣检验，联合方法只有在节省 10% 测量时通过确认，节省 20% 和 40% 未通过。实验暴露出一个新的方法问题：补测动作可能破坏原本会成功的直接动作，因此下一轮增加动作接受门控。")]
story += [P("一、上一轮实验发现","CNH"),P("上一轮用独立测试种子扫描 4、2、1、0.5 和 0.25 mm 单边间隙，并改变观察视角和装夹高度。直接 Sol 在方孔套柱上从 2 mm 的 8/8 降到 1 mm 的 7/8。三任务合计，直接控制 70/120，始终测量 104/120，按需测量 96/120。按需策略少消费 40% 的额外测量，但成功率相对始终测量低 6.7 个百分点。32° 斜视产生了八个可由补测挽回的漏测案例。")]
story += [PageBreak(),P("二、上一轮预算曲线","CNH"),Image(str(root/"budget-frontier.png"),width=166*mm,height=98*mm),P("图 2  第一轮独立测试中，测量预算与严格就位成功率。按需策略在 40% 和更高的测量节省下没有达到始终测量的非劣界。","Caption")]
data=[["每批测量数","节省","只看公差","只看视角","联合","始终测量"],["9/10","10%","140/300","138/300","140/300","141/300"],["8/10","20%","138/300","132/300","131/300","141/300"],["6/10","40%","123/300","121/300","121/300","141/300"],["3/10","70%","116/300","114/300","119/300","141/300"]]
t=Table(data,colWidths=[25*mm,22*mm,31*mm,31*mm,25*mm,30*mm]);t.setStyle(TableStyle([("FONTNAME",(0,0),(-1,-1),"MSYH"),("FONTSIZE",(0,0),(-1,-1),7.8),("LEADING",(0,0),(-1,-1),11),("BACKGROUND",(0,0),(-1,0),colors.HexColor("#DDEBE6")),("TEXTCOLOR",(0,0),(-1,0),colors.HexColor("#173E3A")),("GRID",(0,0),(-1,-1),.35,colors.HexColor("#B9C8CB")),("ALIGN",(0,0),(-1,-1),"CENTER"),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#F5F8F8")]),("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5)]));story += [t,Spacer(1,5)]
story += [PageBreak(),P("三、上一轮失败案例","CNH"),Image(str(root/"failure-cases.jpg"),width=174*mm,height=100*mm),P("图 3  同一输入下的直接动作和始终测量动作。案例包括联合方法漏测、补测后反而失败、联合方法超过简单规则，以及两种动作均失败。","Caption")]
story += [P("代表性案例","CNH2"),P("B00P00 为圆孔、2 mm、26°。联合规则漏测，直接动作最终高度 168.3 mm，补测动作落到 10.0 mm。B00P09 为方孔、1 mm、45°。直接动作成功，始终测量动作失败，说明测量后的 Sol 动作并非总是更可靠。B08P04 为方孔、2 mm、45°。直接动作失败，补测成功，联合方法选中了有价值的测量。B00P01 为圆孔、0.25 mm、8°。公差规则排序为第一，联合排序为第八，联合漏测。")]
story += [PageBreak(),P("四、下一轮调整后的主线","CNH"),P("下一轮不再把“是否测量”作为唯一决策。系统先决定是否使用一次补测，再决定测量后是否接受新的动作。若补测后的动作风险不低于原动作，系统保留原动作。目标是在全新的工件、视角和装夹高度上，验证在少测 20% 和少测 40% 时是否仍能相对始终测量通过非劣检验。")]
story += [P("四种策略","CNH2"),P("只看公差，优先最小间隙。只看视角，优先最大倾角。风险感知测量，利用间隙、视角和观测质量决定是否测量。风险感知测量与动作接受，先测量，再在原动作和补测动作中选择安全裕度更高的一个。始终测量作为上限参考。")]
story += [P("五、下一轮独立实验设计","CNH"),P("使用 30 个全新工作批次，每批 10 个全新场景，共 300 个场景。每批平衡五档间隙和五个未见视角，装夹抬高 10–42 mm，接触前移动件高度 36–50 mm。所有优先级在模型回答前锁定。每个场景用一张匿名 RGB 图像调用冻结的 GPT-6.2 Sol，补测动作使用渲染 RGB-D 平面读数。场景、测量、执行和评分分开记录。每种策略在同一批次内选择固定数量的场景，保证测量预算完全相同。")]
story += [P("非劣检验","CNH2"),P("非劣界预设为严格就位率相对始终测量最多下降 5 个百分点。按照少测 10%、20%、30%、40%、50%、60%、70% 的固定顺序检验。首次未通过后停止确认更激进预算，后续档位仅报告描述性结果。主预算检验少测 40%。")]
story += [P("六、数据记录与可复现性","CNH"),P("主要指标为严格就位率。配对单位为独立工作批次，报告联合减两个简单规则的配对差、95% 置信区间和 Holm 校正后的优效性检验。逐场景保存模型提示、模型回答、测量等级、候选动作、最终高度、横向误差和成功标签。圆孔、方孔采用自由释放终末判定，持件任务采用几何进给夹具，不能解释为完整双臂真机闭环。")]
story += [P("七、当前结论和待验证问题","CNH"),P("上一轮已经证明补测具有潜在价值，但尚未证明一个简单的测量优先级能以较少测量稳定复现始终测量的效果。下一轮的关键不是继续调一个触发阈值，而是验证动作接受门控是否能避免补测后反而失败，并确定在 20% 和 40% 测量节省下是否存在统计上可确认的非劣区间。")]
story += [P("附录：实验文件","CNH"),P("完整实验报告、预注册协议、预算结果、逐例结果、模型请求记录和失败图像保存在本项目的独立测量策略实验目录。PDF 中的图 1 为架构示意，图 2 和图 3 来自上一轮实测数据。")]
doc=SimpleDocTemplate(str(out),pagesize=A4,rightMargin=18*mm,leftMargin=18*mm,topMargin=15*mm,bottomMargin=20*mm,title="风险感知测量与动作接受机制")
doc.build(story,onFirstPage=header_footer,onLaterPages=header_footer)
print(out)

