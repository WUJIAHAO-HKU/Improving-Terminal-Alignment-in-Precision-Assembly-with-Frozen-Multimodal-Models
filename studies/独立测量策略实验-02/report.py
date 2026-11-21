"""Generate a stand-alone report, failure illustrations and an audit of held-out sampling."""
from pathlib import Path
import json,math
from collections import Counter
import numpy as np
from PIL import Image,ImageDraw,ImageFont
D=Path(__file__).resolve().parent
def read(n):return json.loads((D/n).read_text(encoding='utf-8-sig'))
def main():
    s=read('summary.json');rows=read('case-outcomes.json');by=s['budgets'];c=by['6']['counts'];always=s['baselines']['always'];examples=read('failure_views.json')
    prev=D.parent/'独立公差实验-01'/'validated'
    old= json.loads((prev/'manifest.json').read_text());oldstress=json.loads((prev/'stress-manifest.json').read_text())
    assert not ({r['seed'] for r in rows}&{r['seed'] for r in old+oldstress})
    assert not ({r['angle'] for r in rows}&{r['angle'] for r in old})
    assert min(r['height'] for r in rows)>max(r['height'] for r in old)
    primary=by['6']['comparisons']
    saved=[(10-int(k))*10 for k,b in by.items() if b['ni_pass']]
    best=max(saved,default=0)
    labels={'clearance':'只看公差','view':'只看视角','joint':'联合','fit_clearance':'同学习器仅公差','fit_view':'同学习器仅视角'}
    tasks={'square':'方孔套柱','round':'圆孔套柱','dual':'持件轴孔几何夹具'}
    rr=['# 独立测试：按公差和图像质量分配测量预算','',
        f"主预算下每批 10 件测 6 件，共 180/300 次。只看公差成功 {c['clearance']}/300，只看视角 {c['view']}/300，联合 {c['joint']}/300，始终测量 {always}/300。连续通过预设非劣检验的最大已测节省比例为 {best}%（零表示所有少测档位均未得到确认）。",
        '','![预算与就位成功率](budget-frontier.png)','','## 设计',
        '30 个独立工作批次，每批 10 个新种子。批内平衡五档间隙和五档新视角，配对比较相同额外测量次数。五档间隙为 0.25、0.5、1、2、4 mm，视角为 8、14、26、38、45°。固定装夹体抬高 10–42 mm，接触前移动件中心高于柱顶 36–50 mm。此前测试夹具未抬高，接近高度为 12–34 mm。几何和控制约束与上一轮相同。每幅图像独立、匿名送入请求标识 gpt-6.2-sol 的推理接口。物理场景、额外深度观测、执行和评分运行于傲飞 1 号。每个回合两种潜在动作都实际推理、回放，四种策略的在线测量数按预锁定决策计数。',
        '','公差规则优先最小间隙，视角规则优先最大倾角。联合规则使用间隙、视角和初始 RGB 中心区域亮度梯度能量预测补测的成功收益；线性岭回归仅在上一轮 120 个样本上拟合。未读取测试夹具高度、真实偏移或补测深度。先对同批的十张初始图排序再分配预算；本实验没有验证逐件流式阈值或实际生产节拍。',
        '','## 相同预算的比较','',
        '|每 10 件测几件|总测量次数|公差|视角|联合|同学习器仅公差|同学习器仅视角|始终测量|',
        '|---:|---:|---:|---:|---:|---:|---:|---:|']
    for k in sorted(by,key=int):
        b=by[k];rr.append('|'+ '|'.join(map(str,[k,30*int(k),*[b['counts'][m] for m in labels],always]))+'|')
    rr+=['','主预算预先固定为 60%。下列差异单位均为百分点。95% 区间为双侧批次配对 t 区间，优效性检验为单侧并做 Holm 两项校正。']
    for m in ['clearance','view']:
        z=primary[m];rr.append(f"- 联合减{labels[m]}：{z['diff_pp']:+.2f}，区间 [{z['ci_pp'][0]:.2f}, {z['ci_pp'][1]:.2f}]，校正 p={z['holm_p']:.4g}，配对胜/负 {z['wins']}/{z['losses']}。")
    rr+=['','## 与始终测量的非劣检验','','边界为严格就位率相差不超过 5 个百分点。采用预先登记的单侧 5% 水平分布无关 e 检验（拒绝阈值 20），从省 10% 依次向下检验，首次未通过以后停止正式判定。所附单侧 t 下限用于描述，不代替正式判据。','',
        '|省测量|联合−始终（百分点）|联合胜 / 负|单侧 t 下限|e 值|固定序贯结论|','|---:|---:|---:|---:|---:|---|']
    for k in sorted(by,key=int,reverse=True):
        b=by[k];z=b['vs_always'];status='通过' if b['ni_pass'] else ('未通过' if b['eligible'] else '仅描述')
        rr.append(f"|{(10-int(k))*10}%|{z['diff_pp']:+.2f}|{z['wins']} / {z['losses']}|{z['lower95_pp']:+.2f}|{b['e']:.4g}|{status}|")
    rr+=['','## 分任务结果（主预算）','','|任务|场景数|仅 RGB|只看公差|只看视角|联合|始终测量|','|---|---:|---:|---:|---:|---:|---:|']
    for task,sub in s['by_task'].items():rr.append('|'+tasks[task]+'|'+'|'.join(str(sub[k]) for k in ['n','direct','clearance','view','joint','always'])+'|')
    rr+=['','## 失败回放','','以下案例来自 60% 预算，按既定类别选择，优先显示自由释放的套柱任务。只有 1–6 名能分到测量。方孔、圆孔的末态高度为零件中心相对于桌面，持件夹具为相对于柱顶。']
    descriptions={'joint_skip_harms':'联合漏测','joint_measures_harms':'补测后反而失败','joint_beats_simple':'联合补测成功，至少一个简单规则漏测','simple_rescues_joint_skip':'简单规则挽回联合漏测','both_actions_fail':'两种动作都失败'}
    fig=Image.new('RGB',(1100,197*(len(examples)//2)),'white');draw=ImageDraw.Draw(fig);font=ImageFont.truetype('arial.ttf',17)
    for i in range(0,len(examples),2):
        ex=examples[i];r=next(v for v in rows if v['id']==ex['id']);y=i//2*197
        draw.text((2,y+4),r['id']+'  input',font=font,fill='black');im=Image.open(D/'frames'/(r['id']+'.jpg'));im.thumbnail((162,162));fig.paste(im,(2,y+28))
        for j,m in enumerate(['direct','always']):
            z=r['scores'][m];x=191+450*j
            draw.text((x,y+4),f"{m}: {'SEATED' if z['success'] else 'FAILED'} | final h {z['height']:.1f} mm",font=font,fill='black')
            im=Image.open(D/'failure_views'/f'{i+j:02d}.jpg');im.thumbnail((435,162));fig.paste(im,(x,y+28))
        d,b=r['scores']['direct'],r['scores']['always'];txt='、'.join(str(r['ranks'][m]) for m in ['clearance','view','joint'])
        rr+=[f"- **{r['id']} · {descriptions[ex['category']]}**。{tasks[r['task']]}，{r['gap']} mm，{r['angle']:.0f}°，夹具抬高 {r['mount']:.1f} mm。公差、视角、联合三个排名分别 {txt}。直接 / 补测动作 {d['action']} / {b['action']} mm，末态高度 {d['height']:.2f} / {b['height']:.2f} mm，末态横向偏差 {d['lateral']:.2f} / {b['lateral']:.2f} mm。"]
    fig.save(D/'failure-cases.jpg',quality=94);rr+=['','![独立测试输入与物理末态](failure-cases.jpg)','',
        f"全量仅 RGB 为 {s['baselines']['direct']}/300，准确动作参考为 {s['baselines']['oracle']}/300。方孔和圆孔为理想末段纠偏后的自由释放。轴孔夹具为持件几何进给，不代表机器人双臂闭环。各组共用物理执行器、动作和评分，未测试新工件、真机、连续在线预算调度或延迟。超出本轮所测预算的节省比例未验证。",
        '', '协议 protocol.txt；拟合系数 locked-weights.json；先于推理保存的全部决策 locked-ranks.json；每次提示和回答 responses/；逐例真值、排名、动作和物理末态 case-outcomes.json；预算结果 budget-results.csv。']
    (D/'实验报告.md').write_text('\n'.join(rr)+'\n',encoding='utf-8')
if __name__=='__main__':main()

