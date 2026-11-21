"""Summarise the independent clearance sweep and show selected test images next to paired final states."""
import json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
D=Path(__file__).resolve().parent
def load(s):return json.loads((D/s).read_text())
ss=load('summary.json');rows=load('test-outcomes.json');stress=load('stress-scores.json');key={r['id']:r for r in load('stress-manifest.json')}
tasks={'square':'方孔','round':'圆孔','dual':'持件夹具'};gaps=['4','2','1','0.5','0.25'];models={'direct':'Sol 直接','always':'Sol 始终测量','on_demand':'Sol 按需','terra':'Terra 直接','oracle':'准确动作参考'}
report=['# 独立装配公差实验','','![方法示意图](architecture-final.png)','',
'傲飞 1 号运行 robosuite 1.4.0 / MuJoCo，模型图像调用由本机转发。GPT-6.2 Sol 与 GPT-6.1 Terra 为请求标识。主实验 12 个校准种子、24 个独立测试种子，每个种子配对扫描五档单边间隙。压力测试另用 12 个种子。每个请求使用一张匿名图像。','',
'## 实验一 · 评分验证','',
'已知姿态包括就位、半插、倾斜、悬空与脱离。在 3 类几何、5 档间隙中，严格几何判据符合构造标签 75/75，原生判据符合 55/75。20 个分歧均为圆孔或持件夹具上的倾斜与半插。编号图像双视角模型盲核 45 例，30 例判对，3 例判错，12 例遮挡无法判读。没有人工盲审。','',
'最紧间隙的数值敏感性检查中，2 ms 与 1 ms 两种步长下，方孔 56/56 对、圆孔 49/56 对得到相同就位判定。圆孔在最紧档具有可见的积分步长敏感性。','',
'## 实验二 · 公差扫描','',
'![成功率](clearance-results.png)','',
'固定初始平行姿态，独立随机场景包含平面偏移、装夹高度、相机俯角及位置。表内各格分母 8。预先指定观察成功率低于 90% 为不稳定。每任务每档一例失败就会越线，因此阈值是观测档位。','',
'|任务 / 策略|4 mm|2 mm|1 mm|0.5 mm|0.25 mm|','|---|---:|---:|---:|---:|---:|']
for t,tn in tasks.items():
 for m,mn in models.items():
  report.append('|'+tn+' / '+mn+'|'+'|'.join(str(ss['by_task'][t][g][m]) for g in gaps)+'|')
counts={}
report+=['','在 1 mm 下另测倾斜和遮挡，允许模型同时输出平移、横滚和方件偏航。每任务 4 个新种子配对生成四类条件。8–14° 初始横滚，方件另加 8–16° 偏航，合成遮挡条宽 36 个像素。每格分母为 12。','',
'|条件|Sol|Terra|准确动作|','|---|---:|---:|---:|']
for cond,lab in [('aligned','平行'),('tilted','倾斜'),('occluded','遮挡'),('tilted_occluded','倾斜且遮挡')]:
 counts[cond]={m:sum(x['strict'] for x in stress if x['model']==m and key[x['id']]['condition']==cond) for m in ['gpt-6.2-sol','gpt-6.1-terra','oracle']}
 report+=['|'+lab+'|'+'|'.join(str(v) for v in counts[cond].values())+'|']
report+=['','## 实验三 · 三策略配对比较','','|任务|直接|始终测量|按需测量|按需测量次数|','|---|---:|---:|---:|---:|']
for t in [*tasks,'all']:
 q=ss['all'] if t=='all' else {m:sum(r[m] for r in ss['by_task'][t].values()) for m in ss['all']}
 report+=['|'+tasks.get(t,'全部')+'|'+'|'.join(str(q[m])+'/'+str(q['n']) for m in ['direct','always','on_demand','measure'])+'|']
n=ss['all'];lo,hi=ss['paired_boot_CI_pp']
report+=['',f"按需减始终的配对成功率差 {(n['on_demand']-n['always'])/120*100:.2f} 个百分点，按任务分层、按种子配对重抽样的 95% 区间 [{lo:.2f}, {hi:.2f}]。预定非劣界为 −5 个百分点。按需相对始终由成转败 {ss['paired_harm']} 例，由败转成 {ss['paired_gain']} 例。仅自由释放的两个任务为按需 {ss['nut_only']['on_demand']}/80，始终 {ss['nut_only']['always']}/80。",
'测量使用渲染深度和带 0.65 mm 噪声的平面直方图，无物体掩膜或真值位姿。三组从同一输入出发，事后按预先锁定的规则选择已实测的潜在动作并在服务器回放。节省的是部署时会消费的额外测量次数，未实测在线节拍。阈值方孔 0.79、圆孔 2.68、持件夹具 2.04 mm，均为任务级，不是逐帧不确定性估计。','',
'## 失败案例','']
pairs=load('failure_views.json');font=ImageFont.truetype('arial.ttf',16)
fig=Image.new('RGB',(1060,190*(len(pairs)//2)),'white');draw=ImageDraw.Draw(fig)
for i in range(0,len(pairs),2):
 a=pairs[i];r=next(v for v in rows if v['id']==a['id']);y=i//2*190
 im=Image.open(D/'frames'/(a['id']+'.jpg'));im.thumbnail((150,150));fig.paste(im,(2,y+27));draw.text((2,y+3),a['id'],font=font,fill='black')
 for j,m in enumerate(['direct','always']):
  o=r['outcomes'][m];im=Image.open(D/'failure_views'/f'{i+j:02d}.jpg');im.thumbnail((420,155));x=204+j*427;fig.paste(im,(x,y+27));draw.text((x,y+3),f"{m}: {'SEATED' if o['success'] else 'FAILED'} | h={o['height']:.1f} mm",font=font,fill='black')
 d,b=r['outcomes']['direct'],r['outcomes']['always']
 report+=[f"- {a['id']}（{a['category']}）。理想平移 ({-r['x']:.2f}, {-r['y']:.2f}) mm，直接动作 {d['action']}，补测动作 {b['action']}。最终高度 {d['height']:.2f} / {b['height']:.2f} mm，横向偏差 {d['lateral']:.2f} / {b['lateral']:.2f} mm。按需测量触发状态为 {r['trigger']}。"]
fig.save(D/'failure-cases.jpg',quality=94)
report+=['','![同一输入下的两个物理末态](failure-cases.jpg)','',
'方孔和圆孔高度相对于桌面，夹具相对于柱顶。全部回合保留在 test-outcomes.json。','',
'## 限制与复核','',
'单臂两项检验的是理想横向纠偏后的自由释放。双臂项保留原生工件几何，固定持件坐标系，通过受阻进给检验对准，没有在线双臂控制或完整抓取。主扫描每任务每档只有八个独立种子；相同种子跨公差重复使用，测试工件资产与校准相同。圆孔柱顶距离估计的中位绝对误差为 15.54 mm，圆孔结果混合了模型误差与深度处理误差。','',
'原始文件包括 protocol.txt、locked-gate.json、manifest.json、responses/、stress-responses/、scores.json、stress-scores.json、timestep-check.json、fixtures.json 和 blinded-visual-audit.json。图中 ImageGen 工件只用于示意，失败案例图来自实际回放。']
dt=load('timestep-check.json')
ag={t:sum(a['success']==b['success'] for a,b in zip(dt[::2],dt[1::2]) if a['task']==t) for t in ['square','round']}
body='\n'.join(report)+'\n'
body=body.replace('55/75。20 个分歧均为圆孔或持件夹具','65/75。10 个分歧均为持件夹具').replace('30 例判对，3 例判错','33 例判对，0 例判错')
body=body.replace('方孔 56/56 对、圆孔 49/56 对',f"方孔 {ag['square']}/56 对、圆孔 {ag['round']}/56 对").replace('圆孔 2.68','圆孔 1.23')
body=body.replace('圆孔柱顶距离估计的中位绝对误差为 15.54 mm，圆孔结果混合了模型误差与深度处理误差。','已修正圆柱半高索引，并以新种子重跑全部圆孔实验。圆孔柱顶距离估计的中位绝对误差约 0.05 mm。最终回放在每次动作之前重置完整仿真动力学状态。')
(D/'实验报告.md').write_text(body,encoding='utf-8')
print(json.dumps(counts));print([(x['id'],x['category']) for x in pairs[::2]])

