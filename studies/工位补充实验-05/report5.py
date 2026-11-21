"""Create a standalone report from locked selections and observed server outputs."""
import math
from pathlib import Path
from xml.sax.saxutils import escape
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from PIL import Image
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate,Paragraph,Table,TableStyle,Image as Pic,Spacer,PageBreak
from rules4 import D,read,save
font='msyh.ttc'
labels={'full':'整批排序','strong':'全测门控','stream_natural':'流式·自然','stream_first':'流式·方孔先','stream_last':'流式·方孔后','gap':'最小间隙','abrank':'排序去公差','abboth':'两道均去公差','random':'随机抽测','strat':'按几何分层','strong_ab':'全测·去公差门控','direct':'仅 RGB'}
def main():
    s=read(D/'summary.json');B=s['budgets'];ref=read(D/'square-refined.json')
    rows={r['id']:r for r in read(D/'case-outcomes.json')};ex=read(D/'failure_views.json')
    plt.rcParams['font.family']=font_manager.FontProperties(fname=font).get_name();plt.rcParams['axes.unicode_minus']=False
    fig,axes=plt.subplots(1,2,figsize=(9.3,3.4),sharey=True)
    for ax,k in zip(axes,['8','6']):
        for method,col in [('full','#17695f'),('stream_natural','#b16b28')]:
            b=B[k][method];x=np.arange(0,3601,10);ax.plot(x,(b['saved_base_s']-x*b['extra_fail'])/3/60,color=col,label=labels[method])
        ax.axhline(0,ls='--',color='#636363',lw=1);ax.set_title('少测 '+str((10-int(k))*10)+'%');ax.set_xlabel('每个首次失败的综合返工占时（秒）');ax.grid(alpha=.15)
    axes[0].set_ylabel('相对全测节省的忙时（分/百件）');axes[0].legend(frameon=False)
    fig.tight_layout();fig.savefig(D/'rework-frontier.png',dpi=195);plt.close(fig)
    pdfmetrics.registerFont(TTFont('Yahei',font,subfontIndex=0))
    st=[ParagraphStyle(str(i),fontName='Yahei',fontSize=sz,leading=lead,spaceAfter=gap,wordWrap='CJK',textColor=colors.HexColor(color)) for i,(sz,lead,gap,color) in enumerate([(9.5,15,6,'#263b40'),(14,21,8,'#176257'),(19,26,10,'#194847'),(8.3,13,6,'#415454')])]
    story=[]
    def p(txt,i=0):story.append(Paragraph(escape(txt),st[i]))
    def tb(data):
        t=Table(data,hAlign='LEFT');t.setStyle(TableStyle([('FONTNAME',(0,0),(-1,-1),'Yahei'),('FONTSIZE',(0,0),(-1,-1),8.7),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#daebe7')),('ALIGN',(0,0),(-1,-1),'CENTER'),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f4f7f6')]),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4)]));story.extend([t,Spacer(1,3*mm)])
    def pic(f,w,h):
        with Image.open(f) as im:a,b=im.size
        scale=min(w*mm/a,h*mm/b);story.append(Pic(str(f),a*scale,b*scale))
    def hnum(n):return f'{n:.1f}'
    p('混流装配工位：测量预算、返工与首次就位',2)
    p('JMS 补充实验 05　|　独立仿真 300 件 · 30 批',1)
    p(f"新场景每批包含 5 个方孔、3 个圆孔和 2 个持件轴孔。全测并允许保留 RGB 原动作成功 {B['8']['strong']['ok']}/300，纯 RGB 成功 {B['8']['direct']['ok']}/300，理想纠偏为 {s['oracle']}/300。新种子和六个俯角与前面各轮去重。")
    p('工位节拍与返工成本',1)
    p('实际计时来自两处：本机 14 路并行发起独立 Sol 图像请求，并记录从启动到返回（含重试）的墙钟时间；傲飞 1 号对每件采集 RGB、额外 RGB-D 并回放两候选动作。下面是软件阶段耗时，服务器物理仿真执行用的是墙钟秒。')
    ar=[['计时阶段','均值 / 秒','中位数 / 秒','P90 / 秒']]
    for key,name in [('rgb','初始 RGB'),('rgbd','附加 RGB-D 与平面估计'),('direct_call','原动作模型调用'),('measurement_call','补测模型调用'),('execution','动作仿真回放')]:
        a=s['timing'][key];ar.append([name,*[f"{a[k]:.3f}" for k in ['mean','median','p90']]])
    tb(ar)
    p('串行工位模型将各阶段服务时间相加，首次失败再增加综合返工占时 R。每个失败件最终修复为合格品；部署的移动、夹取、人工处理及真实网络负载没有现场日志。每百件忙时为总服务和返工时间除以 3。所得节拍是条件估计。')
    tb([['R=120 秒情景','测量数','首次就位','忙时 / 分每百合格件','比全测少 / 分']]+[[labels[m]+(' '+str(int(k)*10)+'%' if m!='strong' else ''),B[k][m]['measured'],B[k][m]['ok'],hnum(B[k]['station'][m]['120']['0']['busy_per100']/60),hnum(B[k][m]['saving_min100']['120'][0])] for k,m in [('8','strong'),('8','full'),('8','stream_natural'),('6','full'),('6','stream_natural')]])
    p('表中策略后的百分数为测量比例；不同表内的“少测比例”为其补数。盈亏区间与到件等待见下一页。',3)
    story.append(PageBreak());p('何时省测能缩短工位忙时？',2)
    pic(D/'rework-frontier.png',175,71)
    p('图 1　正值表示省测组占用工位的时间更短。设 S 是省测节省的首次处理总时间，ΔF 是省测增加的失败数，则每百合格件节省 (S−R×ΔF)/3 秒。横轴使用假设的返工占时。',3)
    for k in ['8','6']:
        for m in ['full','stream_natural']:
            b=B[k][m];delta=b['extra_fail'];saved=b['saved_base_s'];cut=b['break_even_s']
            text=f"交点 R={cut:.0f} 秒，低于交点时省时" if delta>0 and cut>=0 else ('整个扫描区间都省时' if saved>=0 and delta<=0 else '见带符号的成本曲线')
            a,lo,hi=b['saving_min100']['120']
            p(f"少测 {100-10*int(k)}% · {labels[m]}：首次处理总计节省 {saved/60:.1f} 分钟，首次失败变化 {delta:+d} 件；{text}。R=120 秒时，节省 {a:.1f} 分/百件（批配对 95% 区间 {lo:.1f} 至 {hi:.1f}）。",3)
    p('到件等待与首件交付',1)
    p('批内先看齐十个原动作再选件；流式按到件顺序完成当前件。固定到件间隔，单工位无重叠。表中等待为从到件到完工减去自身服务时间，包含批内等候。R 固定为 120 秒。')
    arr=[['策略（少测20%）','间隔 / 秒','等待 / 秒每件','流动时间 / 秒每件','总历时 / 分每百件']]
    for m in ['strong','full','stream_natural']:
        for sp in ['30','90']:
            z=B['8']['station'][m]['120'][sp];arr.append([labels[m],sp,hnum(z['wait']),hnum(z['flow']),hnum(z['elapsed_per100']/60)])
    tb(arr)
    p('假设无在制品上限，无外部工位争抢；长队列反映到件速度超过此模型的服务能力。候选动作从同一初态分别回放，失败后换另一动作的可恢复数仅是理想复位诊断。',3)
    story.append(PageBreak());p('同预算制造基线与公差消融',2)
    p('制造基线和仅排序消融共用同一动作门控、候选动作和执行记录。随机抽测均匀选择；分层按批内几何比例以最大余数法配额，类内均匀选择。另对这两个随机基线精确计算所有可能抽样的期望成功数。')
    arr=[['策略','测240件 / 成功','测180件 / 成功']]
    for m in ['full','random','strat','gap','abrank','abboth','strong_ab']:
        arr.append([labels[m],str(B['8'][m]['ok']),str(B['6'][m]['ok'])])
    for m,n in [('random_expected','随机抽测（期望）'),('strat_expected','按几何分层（期望）')]:
        arr.append([n,hnum(B['8'][m]['expected_ok']),hnum(B['6'][m]['expected_ok'])])
    tb(arr)
    p('全测·去公差门控一行在两列均测 300 件，仅用于核对消融后全测参照的变化。完整方法沿用上一轮已冻结权重。去公差版本按同样的数据与训练流程重新拟合，移除公差、交互项及相应按间隙归一化项。Sol 提示仍含零件尺寸，这项消融检验外层决策显式使用公差的价值。',3)
    p('主比较：少测 20%，完整排序减对照',1)
    arr=[['对照','差值 / pp','双侧 95% 批配对区间','Holm 校正单侧 p']]
    for m,n in [('random_expected','随机期望'),('strat_expected','分层期望'),('gap','最小间隙'),('abrank','仅排序去公差')]:
        v=B['8']['comparisons'][m];arr.append([n,f"{v['diff']:+.2f}",f"{v['ci'][0]:+.2f} 至 {v['ci'][1]:+.2f}",f"{v['holm']:.4g}"])
    tb(arr)
    p('单侧优效性以完整策略更优为方向，四项共同校正，单位为 30 个独立批次。随机单次结果只作直观对比。40% 节省及双阶段消融为描述性。')
    story.append(PageBreak());p('逐件到达：混流顺序与预算耗尽',2)
    p('流式控制器只使用当前零件分数和剩余预算。阈值为开发集分数分布的 1−剩余预算/剩余件数 分位数。预算不足时停止测量；当余件数等于余下配额时全部测量。每批恰测 8 件或 6 件。将方孔集中在批首或批尾时，类内原有次序不变，阈值与权重不变。')
    arr=[['少测','顺序 / 策略','首次就位','方孔就位 /150','相对全测 / pp','单侧下限 / pp','判定']]
    for k in ['8','6']:
        for m in ['full','stream_natural','stream_first','stream_last']:
            b=B[k][m];v=b['vs_strong'];arr.append([str(100-int(k)*10)+'%',labels[m],b['ok'],b['square'],f"{v['diff']:+.2f}",f"{v['lower']:+.2f}",b.get('status','描述')])
    tb(arr)
    p('非劣对象为全测且同门控；界值为 −5 个百分点，按自然流式顺序先检验少测 20%、再检验少测 40%。单侧 95% 批配对 t 下限须严格超过界值。重排仍是同一组零件，不能当作额外独立试验。')
    p('方孔分层：自然顺序、少测 40%',1)
    arr=[['单边间隙 /mm','方孔数','全测就位','整批就位','流式就位','流式已测']]
    for g in ['4','2','1','0.5','0.25']:
        a=B['6']['stream_natural']['sq_by_gap'][g];arr.append([g,a['n'],B['6']['strong']['sq_by_gap'][g]['ok'],B['6']['full']['sq_by_gap'][g]['ok'],a['ok'],a['measured']])
    tb(arr)
    z=B['6']['stream_natural'];p(f"流式组跳过本可由强对照挽回的方孔 {len(z['square_missed'])} 件，同时避开有害修正 {len(z['square_saved'])} 件。分层样本量有限，单个间隙的百分比仅供诊断。",3)
    story.append(PageBreak());p('方孔回放与返工可恢复性',2)
    for i,e in enumerate(ex[::2]):
        row=rows[e['id']];dire=row['outcomes']['direct'];mea=row['outcomes']['always']
        p(f"{e['id']}　{e['category']}　|　{row['gap']:g} mm、{row['angle']:g}°",1)
        imgs=[]
        for j in [2*i,2*i+1]:
            f=D/'failure_views'/f'{j:02d}.jpg';imgs.append(Pic(str(f),76*mm,38*mm))
        story.append(Table([imgs],hAlign='LEFT'))
        p(f"左为原动作双视角，右为补测动作双视角。末态高度 {dire['height']:.2f} / {mea['height']:.2f} mm，横向偏差 {dire['lateral']:.2f} / {mea['lateral']:.2f} mm。",3)
    z=B['6']['stream_natural'];p(f"自然流式少测 40% 时，共有 {z['fail']} 件首次失败。理想复位后改用另一候选，配对回放中 {z['alternate_rescues']} 件可成功，其余 {z['fail']-z['alternate_rescues']} 件两个动作均失败。实际拆卸、定位和人工修复时长仍属未知。",3)
    story.append(PageBreak());p('方孔数值复核与复现资料',2)
    a=[r for r in ref if r['mode']!='oracle'];assert a and all(rows[r['id']]['task']=='square' for r in a)
    ar=[['单边间隙','候选回放数','两步长判定一致','原成功→失败','原失败→成功']]
    num=[]
    for g in [.5,.25]:
        v=[x for x in a if x['gap']==g];pairs=[(rows[r['id']]['outcomes'][r['mode']]['success'],r['success']) for r in v]
        num.append(dict(gap=g,n=len(v),same=sum(i==j for i,j in pairs),lost=sum(i>j for i,j in pairs),gained=sum(i<j for i,j in pairs)))
        u=num[-1];ar.append([g,u['n'],u['same'],u['lost'],u['gained']])
    tb(ar);save('square-check-summary.json',num)
    p(f"在 0.5 和 0.25 mm 的全部方孔上另做数值敏感性回放，积分步长减半为 {ref[0]['dt']*1000:.2f} ms、总积分步数加倍，稳定性判定从末 50 步变为末 100 步，以保持相同的物理观察时长。这是数值设置敏感性检查，正式统计使用统一原始判据。")
    from evaluate5 import stats
    decision=read(D/'decisions.json')
    refined={(r['id'],r['mode']):r['success'] for r in ref}
    def succeeded(key,mode):
        return refined.get((key,mode),rows[key]['outcomes'][mode]['success'])
    sensitivity=[]
    for k in ['8','6']:
        diffs=[];n_policy=0;n_full=0
        for batch in decision['batches']:
            selected=set(batch['selections'][k]['stream_natural'])
            delta=0
            for key in batch['orders']['natural']:
                mode='always' if rows[key]['accept'] else 'direct'
                full=succeeded(key,mode);budget=succeeded(key,mode if key in selected else 'direct')
                n_policy+=budget;n_full+=full;delta+=int(budget)-int(full)
            diffs.append(delta/10)
        v=stats(diffs)
        sensitivity.append(dict(k=int(k),policy=n_policy,full=n_full,lower=v['lower']))
    save('square-policy-sensitivity.json',sensitivity)
    p('只替换紧公差方孔的精细步长结果，其余件保留主评估结果，并保持所有选件及接受决定不变。该分析用于检查原非劣结论对就位标签的敏感性。',3)
    tb([['自然流式少测','流式成功 /300','全测成功 /300','单侧下限 / pp']]+[[f"{100-10*r['k']}%",r['policy'],r['full'],f"{r['lower']:+.2f}"] for r in sensitivity])
    p('范围与限制',1)
    p('方孔/圆孔是受控平移后的自由释放，持件任务为几何进给；没有测量机械臂抓取全过程。生成、执行、失败回放在傲飞 1 号完成。RGB-D 深度读数未经现场标定。批组成固定为 5:3:2；与前一轮的较均衡配比以及真实生产批组成均有差别。')
    p('每件采集两份独立推理响应供离线配对。软件调用耗时受到并发、远端排队和服务波动影响。服务器端回放墙钟不是机械运动时间。工位时间、附加返工时间和到件间隔的单位均为秒；若给出工位每小时综合费率，可用分钟数 ÷60 × 费率估计对应货币成本。')
    p('逐件复核',1)
    p('protocol.txt 与 study-lock.json 记录事前协议及权重；decisions.json 记录每批各策略选择和混流顺序；case-outcomes.json 提供原始读数、动作、严格就位标签及计时；summary.json 收录各策略在全部返工和到件情景下的忙时、等待与流动时间；square-refined.json 为紧公差数值复核回放。',3)
    def foot(c,d):
        c.setFont('Yahei',8);c.setFillColor(colors.HexColor('#526966'));c.drawString(18*mm,11*mm,'JMS 装配工位补充实验 05');c.drawRightString(192*mm,11*mm,str(d.page))
    out=D/'output/pdf/混流装配工位补充实验.pdf';out.parent.mkdir(parents=True,exist_ok=True)
    SimpleDocTemplate(str(out),pagesize=A4,leftMargin=18*mm,rightMargin=18*mm,topMargin=15*mm,bottomMargin=17*mm,title='混流装配工位补充实验').build(story,onFirstPage=foot,onLaterPages=foot)
if __name__=='__main__':main()
