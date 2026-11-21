"""Build the internal paired-action research edition from canonical study folders."""
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from collections import Counter
import json,hashlib
D=Path(__file__).resolve().parent
out=D.parent/'JMS论文/output/terminal-alignment-dataset-v0.1.zip'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def stream(rows):return ''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows)
def main():
    records=[];labels=[];images={};seeds=set()
    def observe(n,r,p,split,actions,acquisition):
        key=f"{n}/{r['id']}";source=(split,r['seed'])
        frame=f"observations/{key}.png" if p.suffix=='.png' else f"observations/{key}.jpg"
        images[frame]=p
        records.append(dict(id=key,cohort=n,partition=split,shape=r['task'],batch=r.get('batch'),image=frame,clearance_mm=r['gap'],pitch_deg=r.get('angle',r.get('pitch')),acquisition=acquisition))
        labels.append(dict(id=key,scene_seed=r['seed'],model_requested='gpt-6.2-sol',action_units=['mm','mm'] if n!='09' else ['mm','mm','degrees'],candidates=actions))
        return records[-1]
    for n in ('01','02','03','04','05'):
        d=next(D.parent.glob('*'+n));d=d/'validated' if n=='01' else d
        rows=read(d/('test-outcomes.json' if n=='01' else 'case-outcomes.json'))
        split={'01':'diagnostic','02':'development','03':'development','04':'historical_test','05':'historical_test'}[n]
        for r in rows:
            y=r.get('scores',r.get('outcomes')); acq={'kind':'two_plane_depth','near_mm':r['depth']['near'],'far_mm':r['depth']['far']}
            entry=observe(n,r,d/'frames'/(r['id']+'.jpg'),split,{k:{'action':y[v]['action'],'seated':bool(y[v]['success'])} for k,v in [('rgb','direct'),('depth','always')]},acq)
            responses=d/('isolated-responses' if n in ('03','04') else 'responses')
            prompt=read(responses/f"{r['id']}--gpt-6.2-sol--direct.json")['prompt']
            entry['prompt']=prompt
    r9=read(D/'scenes.json');a9=read(D/'actions.json');s9={r['id']:r for r in read(D/'scores.json')}
    for j,r in enumerate(r9):
        i=r['id'];top=f'observations/09/{i}-top.png';images[top]=D/'frames'/(i+'-top.png')
        # One seeded generator stream with a deterministic draw index per pose.
        entry=observe('09',dict(r,seed=f'2026112109:{j}'),D/'frames'/(i+'-rgb.png'),'exploratory', {k:{'action':a9[i][k],'seated':s9[i][k]['ok']} for k in ('rgb','repeat','view')},{'kind':'overhead_rgb','image':top})
        entry['prompt']=read(D/'responses'/f'{i}-rgb.json')['prompt']
    assert len({r['id'] for r in records})==len(records)==len(labels)==1450
    card='''终端对准配对数据集 v0.1｜内部研究版
场景索引 observations.jsonl；候选动作、动作单位与严格就位结果在 evaluator/labels.jsonl。评测时先只提供主图与工艺参数。仅在策略选择测量后向模型提供 acquisition 内的深度摘要或第二视角，不向模型暴露 evaluator、文件名中的条件、种子或未执行候选的结果。该版为白盒复核包，不提供盲测服务。
01 是 24 个场景种子各自复用五档间隙的 120 个条件。02、03 合计 600 件历史开发数据；04、05 分别是 400 和 300 件历史测试数据，结果已知，不是未来方法的盲测集。06–08 是已有场景的再分析或附加模型回复，保存在八轮源数据包，不重复计入这里。09 是另外 30 个试验性条件；其 scene_seed 值为共享生成器种子加抽样序号。
六类仿真夹具均为末端对准。旧任务动作是水平平移，新任务增加绕竖直轴的转角。前五轮补测为上下平面深度摘要，第九轮补测为俯视图。不同传感方式、动作维数和夹具应分别报告。旧 held 任务为约束式下降，其余的自由释放也不含抓取或完整机械臂控制。09 提供可见标志点和相机标定。支持六类合计，不应视为六类均通过非劣检验。
建议指标为各任务直接成功率、等调用的信息收益、对相同候选保留首动作的净收益、测量比例、按批次配对的成功率差。原始测量耗时和旧统计设计请参见八轮源包。这里的 09 为小规模描述性测试。未授予第三方素材或托管模型输出的再分发许可。公开发布前需完成来源与条款核查，明确许可并另建未公开的测试条件。
'''
    temp=out.with_suffix('.partial');digests=[]
    with ZipFile(temp,'w',ZIP_DEFLATED,compresslevel=2) as z:
        def put(k,b):
            b=b.encode('utf8') if isinstance(b,str) else b
            z.writestr(k,b);digests.append(f'{hashlib.sha256(b).hexdigest()}  {k}\n')
        put('README.txt',card);put('observations.jsonl',stream(records));put('evaluator/labels.jsonl',stream(labels))
        for k,p in images.items():put(k,p.read_bytes())
        for k in ['rig.py','collect.py','policy.py','decide.py','scenes.json','actions.json','choices.json','scores.json','summary.json','protocol-lock.json','runtime.json']:
            put('pilot09/'+k,(D/k).read_bytes())
        for p in sorted((D/'responses').glob('*.json')):put('pilot09/responses/'+p.name,p.read_bytes())
        z.writestr('SHA256.txt',''.join(digests))
    with ZipFile(temp) as z:
        assert z.testzip() is None and all(z.read(n.partition('  ')[2].strip()) is not None for n in digests)
    temp.replace(out)
    print(len(records),len(images),out.stat().st_size)
if __name__=='__main__':main()

