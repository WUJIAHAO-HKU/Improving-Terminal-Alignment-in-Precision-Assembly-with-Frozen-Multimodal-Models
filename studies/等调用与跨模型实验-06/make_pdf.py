"""Print the locked contrasts, absolute outcomes and per-geometry transfer results."""
from pathlib import Path
from xml.sax.saxutils import escape
from PIL import Image
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, Image as Picture, PageBreak
from experiment import D,P,read,TARGETS

def main():
    s=read(D/'summary.json');sol=s['sol'];comp=s['sol_comparisons']
    rows={r['id']:r for r in read(D/'case-outcomes.json')}
    pdfmetrics.registerFont(TTFont('Yahei','msyh.ttc',subfontIndex=0))
    story=[];styles=[ParagraphStyle(str(i),fontName='Yahei',fontSize=size,leading=lead,spaceAfter=space,wordWrap='CJK',textColor=colors.HexColor(col)) for i,(size,lead,space,col) in enumerate([(9.6,15.5,7,'#26393a'),(13,20,8,'#175752'),(20,27,10,'#174844'),(8.4,13.4,6,'#425857')])]
    def p(msg,i=0):story.append(Paragraph(escape(msg),styles[i]))
    def tab(arr):
        tbl=Table(arr,hAlign='LEFT');tbl.setStyle(TableStyle([('FONTNAME',(0,0),(-1,-1),'Yahei'),('FONTSIZE',(0,0),(-1,-1),8.5),('ALIGN',(0,0),(-1,-1),'CENTER'),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dbeae6')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f2f6f5')]),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4)]));story.extend([tbl,Spacer(1,3*mm)])
    fmt=lambda r:f"{r['diff']:+.2f} [{r['ci'][0]:+.2f}, {r['ci'][1]:+.2f}]"
    p('精密装配中的额外观测与冻结迁移',2);p('实验 06　|　等调用 RGB 对照 · Terra 与 Luna 跨模型验证',1)
    primary=comp['depth_switch-rgb_switch']
    p(f"相同的 300 个工位场景、同一张选中 240 件的名单。均直接采用第二动作时，第二次 RGB 推理成功 {sol['rgb_switch']['ok']}/300，RGB-D 推理成功 {sol['depth_switch']['ok']}/300。附加深度的配对差为 {fmt(primary)} 个百分点（双侧 95% 区间）。")
    tab([['第一次输入','第二次输入','动作接受规则','调用数','额外测量','执行第二动作','严格就位']]+[
        ['RGB',obs,rule,300 if key=='direct' else 540,240 if obs=='RGB-D' else 0,sol[key]['accepted'],f"{sol[key]['ok']}/300"]
        for key,obs,rule in [('direct','无','执行原动作'),('rgb_switch','RGB','一律替换'),('depth_switch','RGB-D','一律替换'),('rgb_gate','RGB','RGB 可见打分器'),('depth_shared','RGB-D','同一 RGB 打分器'),('depth_gate','RGB-D','原冻结深度门控')]])
    p('两个候选看同一画面。第二次 RGB 使用与第一次完全相同的提示、相机参数和工艺尺寸；RGB-D 增加两项有噪声的深度平面读数。两种第二次请求均独立，未向模型展示首答。其余 60 件固定原动作。')
    p('配对效应分解',1)
    arr=[['比较（前者减后者）','差值及 95% 区间 / pp','胜 / 负']]
    for key,name in [('rgb_switch-direct','纯重采样（不选择）'),('depth_switch-rgb_switch','增加深度（一律换，主对比）'),('rgb_gate-rgb_switch','RGB 组启用选择'),('depth_gate-depth_switch','深度组启用原门控'),('depth_shared-rgb_gate','增加深度（同一可见打分器）'),('depth_gate-rgb_gate','两个可部署门控系统的总差')]:
        r=comp[key];arr.append([name,fmt(r),f"{r['wins']} / {r['losses']}"])
    tab(arr)
    p(f"pp 表示绝对百分点，区间按 30 个配对批次计算。主对比单侧优效 p={primary['super_p']:.4g}；其余效应作描述。两组门控增益的差中之差为 {fmt(s['gate_interaction'])} 个百分点，门控设计和输入均可能贡献此差异。",3)
    story.append(PageBreak());p('第二次 RGB 如何选择动作？',2)
    p('纯 RGB 组使用一个动作成功率打分函数，输入仅含工艺间隙、零件几何、机位俯角、初始 RGB 图像梯度和候选平移量。分别给首动作与第二动作打分，仅当第二个分数更高时替换。权重用实验 02、03 的 600 个开发场景的纯 RGB 动作与标签拟合；不需要历史第二次 RGB 标签。')
    p('训练样本中的理想纠偏曾用于标定冻结的动作幅值范围；部署时该范围是常数。纯 RGB 打分器不读取场景真值、深度、仿真执行结果或另一组的选择。既有 RGB-D 门控还能使用观察到的平面间距和两动作的差异。将两路径都交给同一个纯 RGB 打分器的补充对比，可控制接受规则的差异。')
    chosen=s['examples'];names={'depth_only':'仅增加深度后就位','rgb_only':'仅第二次 RGB 动作就位','rgb_keep_rescue':'保留原动作挽回成功','rgb_keep_harm':'保留原动作错失成功'}
    for key,ids in chosen.items():
        if not ids:continue
        i=ids[0];r=rows[i];c=r['candidates']
        p(f"{i}　{names[key]}",1)
        p(f"单边间隙 {r['gap']:g} mm，俯角 {r['angle']:g}°。原动作 {c['original']['action']} mm，二次 RGB 动作 {c['repeat']['action']} mm，RGB-D 动作 {c['depth']['action']} mm。对应就位结果依次为 "+' / '.join('成功' if c[n]['success'] else '失败' for n in ['original','repeat','depth'])+'。',3)
    p(f"以上每类取首个匹配 ID。名单上有 {s['rgb_repeat_identical']}/240 件两次纯 RGB 输出的数值完全一致。等调用指每条策略的有效决策调用。计入失败重试，并复用相同历史首答后，两条路径的请求尝试数分别为 {s['sol_attempts_540']['repeat']}（纯 RGB）与 {s['sol_attempts_540']['measured']}（RGB-D）。",3)
    story.append(PageBreak());p('冻结迁移：两种目标模型的三组结果',2)
    p('目标模型生成自己的纯 RGB 与 RGB-D 两个候选。直接、流式预算和全测强对照都使用目标模型的候选。排序特征、岭回归权重、动作幅值范围、流式阈值参考分布、配额耗尽逻辑和深度门控直接沿用 Sol 实验 04/05 的冻结版本。')
    ar=[['模型','组别','有效调用','额外测量','成功数 /300','差值 / pp¹','单侧 97.5% 下限','判定']]
    for model in TARGETS:
        z=s['transfer'][model];name=model.split('-')[-1].title()
        ar.append([name,'纯 RGB',300,0,z['direct'],'—','—','—'])
        for k in ['8','6']:
            b=z['budgets'][k];v=b['vs_strong'];ar.append([name,f'少测 {100-10*int(k)}%',b['calls'],int(k)*30,b['ok'],f"{v['diff']:+.2f}",f"{v['lower975']:+.2f}",b['status']])
        ar.append([name,'全测＋门控',600,300,z['strong'],'0','—','参照'])
    tab(ar);p('¹ 预算组减同模型全测强对照。每模型分配单侧 2.5% 显著性水平，非劣界 −5 个百分点；先少测 20%，通过后再正式判 40%。逐例胜负和未校正单侧 95% 下限在 summary.json 中。',3)
    for model in TARGETS:
        z=s['transfer'][model];a=z['budgets']['8'];b=z['budgets']['6']
        p(f"{model}　迁移后的实际收益",1)
        p(f"少测 20% 相对直接控制为 {fmt(a['vs_direct'])} 个百分点；少测 40% 相对直接为 {fmt(b['vs_direct'])}。全测时一律换动作就位 {z['always_switch']}/300，沿用 Sol 门控为 {z['strong']}/300（接受 {z['accepted']} 个第二动作）。")
        p(f"本模型的 80% 名单与原 Sol 名单重叠 {a['overlap']}/240 件；若强制使用原 Sol 名单，成功 {a['same_sol_list']}/300。60% 档对应重叠 {b['overlap']}/180 件，固定名单成功 {b['same_sol_list']}/300。",3)
    tab([['模型','几何','场景数','直接','少测20%','少测40%','全测门控']]+[[m.split('-')[-1],name,
        s['transfer'][m]['by_task'][task]['n'],s['transfer'][m]['by_task'][task]['direct'],
        s['transfer'][m]['budgets']['8']['by_task'][task],s['transfer'][m]['budgets']['6']['by_task'][task],
        s['transfer'][m]['by_task'][task]['strong']] for m in TARGETS for task,name in [('square','方孔'),('round','圆孔'),('dual','持件')]])
    story.append(PageBreak());p('如何解释这些结果',2)
    p('实验复用了第五轮的 30 个批次（每批 5 方孔、3 圆孔、2 持件几何夹具）。选件只看当前及过往可得信息；Sol 的比较固定原自然到达顺序、相同的首动作和测量名单。样本编号、图片摘要、冻结参数和统计方案在新增推理前写入锁文件。')
    p('主机制比较以第二次纯 RGB 独立重采样作为等调用对照。它检验一次独立重问的效果；没有让模型读取上一次答案、分析执行反馈或展开显式反思。旧的深度请求和本轮新增的 RGB 请求发生在不同时间，沿用同一请求标识和推理强度，服务端版本及解码随机性无法完全固定。该轮是对已有样本和旧主线的配对补充。')
    p('预算与迁移',1)
    p('对单个未测场景，直接和预算策略都只需一次 RGB 请求；选中的场景额外一次请求。全测强对照为每件两次。数据收集为获得潜在回放结果，两目标模型均生成完整 600 个候选。冻结迁移表示目标模型沿用在 Sol 上开发的规则，未在目标模型上校准；非劣检验仅相对各自全测门控，绝对成功率及相对直接控制的增益须同时阅读。')
    p('服务器复核',1)
    p('傲飞 1 号在相同 MuJoCo/robosuite 初态与判据下执行 2,040 次回放。600 个历史 Sol 候选的严格成功、官方成功、稳定性、末态高度、横向偏差和倾角逐项复核一致。新增模型标识为 gpt-6.1-terra、gpt-6-luna 和 gpt-6.2-sol；实际部署接口可能更新。就位衡量末端纠偏，不覆盖机器人完整抓取或真实工位返工。')
    p('核查文件',1)
    p('protocol.txt 和 lock.json 保存冻结方案、240 件名单、RGB 打分器权重及输入散列；gates.json 与 masks.json 保存评分前逐件接受决定和模型名单；responses/ 保存全部新增请求和输出；scores.json、summary.json 和 case-outcomes.json 分别给出物理末态、配对统计与逐件动作。',3)
    def footer(c,doc):
        c.setFont('Yahei',8);c.setFillColor(colors.HexColor('#536968'));c.drawString(18*mm,11*mm,'装配模型验证　|　等调用对照与冻结迁移');c.drawRightString(192*mm,11*mm,str(doc.page))
    out=D/'output/pdf/等调用RGB与跨模型冻结迁移.pdf';out.parent.mkdir(parents=True,exist_ok=True)
    SimpleDocTemplate(str(out),pagesize=A4,leftMargin=18*mm,rightMargin=18*mm,topMargin=15*mm,bottomMargin=18*mm,title='等调用 RGB 与跨模型冻结迁移').build(story,onFirstPage=footer,onLaterPages=footer)
if __name__=='__main__':main()
