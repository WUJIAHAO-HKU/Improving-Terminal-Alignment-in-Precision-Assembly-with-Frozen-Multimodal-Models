"""Build round-03 figure plates and the result narrative from the scored actions."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image, ImageFont, ImageDraw
from policy import HERE,read

def main():
    summary=read(HERE/'summary.json')
    results=summary['budgets']
    cases={c['id']:c for c in read(HERE/'case-outcomes.json')}
    examples=read(HERE/'failure_views.json')
    fig,ax=plt.subplots(figsize=(7.8,4.6))
    for label,field,color in [('Risk ranking + action gate','gated','#166a66'),('Same ranking, always switch','unconditional','#b77732'),('Clearance only','clearance','#68789a'),('View only','view','#9b788b')]:
        ax.plot(list(range(0,101,10)),[results[str(k)][field]/3 for k in range(11)],'o-',ms=3,label=label,color=color)
    ax.axhline(summary['always']/3,color='#303030',ls='--',label='Always measure + switch')
    ax.axhline(summary['always']/3-5,color='#727272',lw=.8,ls=':',label='Noninferiority margin (point scale)')
    ax.set(xlabel='Extra measurements per 100 parts',ylabel='Strict seating success (%)',title='Independent assembly scenes · 30 batches of 10')
    ax.legend(frameon=False,ncol=2,fontsize=8);ax.grid(axis='y',alpha=.15)
    fig.tight_layout();fig.savefig(HERE/'budget-frontier.png',dpi=200);plt.close(fig)
    n=len(examples)//2
    board=Image.new('RGB',(1250,214*n),'white');draw=ImageDraw.Draw(board);font=ImageFont.truetype('msyh.ttc',18)
    details=[]
    tasks={'square':'方孔','round':'圆孔','dual':'持件轴孔'}
    for i in range(n):
        ex=examples[2*i];r=cases[ex['id']]; top=214*i
        draw.text((6,top+1),f"{r['id']}  {ex['category']}",font=font,fill='#20333c')
        im=Image.open(HERE/'frames'/(r['id']+'.jpg'));im.thumbnail((170,170));board.paste(im,(6,top+36))
        vals=[]
        for j,(mode,title) in enumerate([('direct','原动作'),('always','补测动作')]):
            out=r['scores'][mode];heading=f"{title}  {'就位' if out['success'] else '失败'}   末态高度 {out['height']:.1f} mm"
            x=240+500*j
            draw.text((x,top+1),heading,font=font,fill='#20333c')
            im=Image.open(HERE/'failure_views'/f'{2*i+j:02d}.jpg');im.thumbnail((465,170));board.paste(im,(x,top+36))
            vals.append(f"{out['action']} mm，末态高度 {out['height']:.2f} mm，横向偏差 {out['lateral']:.2f} mm")
        details.append(f"- **{r['id']} · {ex['category']}**。{tasks[r['task']]}，间隙 {r['gap']:g} mm，俯角 {r['angle']:g}°，装夹抬高 {r['mount']:.1f} mm，批内测量优先级第 {r['ranks']['risk']}。原动作 {vals[0]}。补测动作 {vals[1]}。")
    board.save(HERE/'failure-cases.jpg',quality=94)
    paras=['# 实验 03｜测量后是否保留原动作','',
        f"独立仿真共 300 件。纯 RGB 原动作成功 {summary['direct']}/300，每件都测并采用新动作成功 {summary['always']}/300，每件都测并启用接受门控成功 {summary['full_gate']}/300。理想纠偏成功 {summary['oracle']}/300。三类几何共用同一严格就位判据框架。",'',
        '## 两个预设预算','']
    for k in (8,6):
        b=results[str(k)];v=b['vs_always'];gate=b['vs_unconditional']
        paras+= [f"**少测 {100-10*k}%**。测 {b['measured']} 次，风险排序与动作门控成功 {b['gated']}/300（{b['gated']/3:.1f}%）。比始终测量相差 {v['diff']:+.2f} 个百分点，单侧 95% 配对 t 下限 {v['lower']:+.2f}，批次 bootstrap 下限 {v['bootstrap_lower']:+.2f}，单侧非劣 p = {v['p_noninferior']:.4g}。按预设顺序判定为**{b['confirmatory']}**。逐例胜/负为 {v['wins']}/{v['losses']}。",
        f"相同名单一律采用补测动作为 {b['unconditional']}/300。门控保留原动作 {b['kept']} 次，挽回 {b['rescued']} 件，误拒 {b['wrong_reject']} 件。同预算净增益 {gate['diff']:+.2f} 个百分点（双侧 95% 区间 {gate['ci'][0]:+.2f} 至 {gate['ci'][1]:+.2f}）。它接受了 {b['accepted']} 个补测动作，其中 {b['harmful_accept']} 次让原本可成功的动作变为失败。未选中测量的零件中，{b['skip_harm']} 件本可由补测挽回。",
        f"只按公差、只按视角选件后直接用补测动作分别为 {b['clearance']}/300 和 {b['view']}/300。相对全量测量也启用门控的对照，差值 {b['vs_full_gate']['diff']:+.2f} 个百分点（描述性）。",'']
    paras+=['![测量预算与严格就位成功率](budget-frontier.png)','',
        '## 动作接受的上限与失败案例','',
        f"全量配对回放中，补测把 {summary['measurement_alone']['wins']} 件从失败变成成功，也把 {summary['measurement_alone']['losses']} 件从成功变成失败。若事后总能选对两动作中可行的一个，能成功 {summary['any_works']}/300；两者都失败的有 {summary['both_fail']} 件。事后选择只用来估计两动作间可利用的差异。",
        '','![实验 03 输入及末态回放](failure-cases.jpg)','',
        '案例按每批测 6 件的策略、按类别取第一个未展示的编号。原动作与补测动作均从同一初始状态执行。自由释放任务的高度相对桌面，持件夹具的高度相对柱顶。','',*details,'',
        '## 实验与统计口径','',
        '场景生成、深度测量、两动作执行和失败回放在傲飞 1 号完成。300 个种子及六个俯角与实验 01、02 去重，三类几何沿用。每批 10 件，每类至少 3 件；装夹抬高 6–48 mm，接近高度 34–52 mm。仅测试末段平移；圆孔最紧公差在前轮观察到积分步长敏感性。模型标识 gpt-6.2-sol，单场景两次独立匿名图像请求，正式数据统一使用实验 02 的提示。早期调度曾试用简写提示和双输出提示，全部排除。','',
        '测量前排序和测量后接受规则的参数只用实验 02 拟合，锁定于实验 03 评分前。非劣界为绝对 5 个百分点，单侧 5%，按 20% 再 40% 固定顺序检验。配对统计单位为 30 个批次，正式检验依赖批均值的近似正态；另附 50,000 次整批重抽样。由于门控可改变已测样本的动作，实验 02 的有界 e 检验不能直接移用。两个实验的正式判据不同。表外预算与强对照只做描述。','',
        '测量节省按部署时读取额外 RGB-D 的次数计算；实验为配对评分离线收集了全部 300 组读数。未计入额外模型推理时延。单次直接/补测请求也包含解码随机性，本设计不能把两种候选的全部差异归因于深度本身。','',
        '逐例数据见 case-outcomes.json；全部预算及配对统计见 summary.json；protocol.txt、policy-lock.json、isolated-responses/ 和 scores.json 分别保存冻结协议、权重与排序、推理原文和仿真末态。']
    strong=results['6']['vs_full_gate']
    budget=results['6']['vs_always']
    paras+=['','**论文结论的边界**。少测 40% 时，相对始终测量且直接换动作，单侧下限仅高出非劣界 '
        f"{budget['lower']+5:.2f} 个百分点。相对始终测量也启用门控，下限为 {strong['lower']:.2f} 个百分点，跨过 −5 的边界。"
        '两个预算最直接的证据来自同名单消融：门控使成功数分别净增 12 件和 9 件。'
        '少测 40% 时，方孔成功 77/101（始终换动作 85/101），圆孔 81/101（75/101），持件轴孔 63/98（63/98）。总体非劣不能外推为每类工件均非劣。']
    (HERE/'实验报告.md').write_text('\n'.join(paras)+'\n',encoding='utf8')
if __name__=='__main__': main()
