"""Package exact scene splits, paired actions, sensory inputs and outcome records with checksums."""
import hashlib,json,shutil,tarfile,collections
from zipfile import ZipFile,ZIP_DEFLATED,ZIP_STORED
from pathlib import Path
from catalog import RECIPES
D=Path(__file__).resolve().parent;A=D.parent
S12=A/'机械臂四任务独立验证-12';S14=A/'机械键位连接器验证-14';P=A/'JMS论文';O=P/'output'
M=['gpt-6.2-sol','gpt-6.1-terra']
def rd(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def validate(d,n,kit=False):
    scenes=rd(d/'scenes.json');assert len(scenes)==n and len({v['id'] for v in scenes})==n
    for p,h in rd(d/'lock.json')['sha256'].items():assert hashlib.sha256((d/p).read_bytes()).hexdigest()==h
    for m in M:
        paths=list((d/'responses'/m).glob('*.json'));assert len(paths)==5*n,(m,len(paths))
        for p in paths:
            v=rd(p);imgs=v['inputs'] if kit else v['input_images']
            assert v['model']==m and all((d/k).is_file() for k in imgs) and v['raw'].strip()
        vals=rd(d/(m+'-summary.json'));assert len(vals['rows' if kit else 'cases'])==n
        choices=rd(d/(m+'-choices.json'));assert all(sum(x['rank']<=k for x in choices.values())==n*k//5 for k in (3,4,5))
        for r in scenes:
            out=rd(d/('runs' if kit else 'sim')/m/r['id']/('results.json' if kit else 'outcomes.json'))
            assert len(out)==7
def package():
    for d,n,k in [(S12,100,False),(D,100,True),(S14,25,False)]:validate(d,n,k)
    dest=O/'assembly-robot-dataset-v0.2.zip';tmp=dest.with_suffix('.building')
    digest={}
    def add(z,p,n):
        assert n not in digest
        data=p.read_bytes();digest[n]=hashlib.sha256(data).hexdigest()
        z.writestr(n,data,compress_type=ZIP_STORED if p.suffix in ('.zip','.mp4','.jpg','.png') else ZIP_DEFLATED,compresslevel=3 if p.suffix not in ('.zip','.mp4','.jpg','.png') else None)
    def write_text(z,n,text):z.writestr(n,text,compress_type=ZIP_DEFLATED);digest[n]=hashlib.sha256(text.encode()).hexdigest()
    with ZipFile(tmp,'w',allowZip64=True) as z:
        add(z,O/'closed-loop-robot-trajectories.zip','01-twin-pilot/episodes.zip')
        for d,root,sub in [(S12,'02-four-fixtures',['initial','sim','responses']), (D,'03-twenty-recipes',['observations','runs','responses','recordings']), (S14,'04-keyed-connector',['initial','sim','responses'])]:
            files=[f for f in d.iterdir() if f.is_file() and f.suffix in ('.json','.py') and f.name not in ('commission.json','inspect-commission.json','egl_check.py','construct.py')]
            if d==D:
                files=[p for p in files if p.name not in ('terra_prepare.py','terra_replay.py','dataset_release.py','finalize_paper.py')]
            for p in sorted(files):add(z,p,root+'/'+p.name)
            for subdir in sub:
                for p in sorted((d/subdir).rglob('*')):
                    if p.is_file() and p.suffix in ('.json','.mp4','.jpg','.png','.npy','.npz'):
                        add(z,p,root+'/'+p.relative_to(d).as_posix())
        text="""# 仿真机械臂装配配对数据集 v0.2

本包单独收录夹爪通过接触带动零件的仿真机械臂实验。早期直接施加末端位移的 1,450 个条件见独立的 v0.1 文件。两者的成功率分母应分别计算。

01 为无标记双销。4 个正常场景和 2 个故障注入场景由 Sol、Terra 分别执行，内含 12 段连续视频，25 帧/秒。两种模型在相同扰动下的 R01 可配对观看。记录含各步指令、实际轨迹、双侧接触和松爪后结果。

02 为双销、窄槽、D 形和双插口选位的 100 个独立样本，每类 25 个。04 为机械键位防错版另 25 个样本，错误插口的定位销尺寸过大。两批均由两个模型控制夹爪。03 为 20 个多零件装配配方，每种 5 个工装尺寸与姿态样本；每个装配体含固定底座和 2–7 个夹爪抓取的零件。配方、前置关系、物料顺序见 catalog.py。模型利用配方和近似料位，预测抓取点和放置基准。首件实物理放置后重拍，剩余动作由模型成组下达。完整装配、单件是否到位和中途停止分开记录。

每个目录以 scenes.json 的 id、model 和 mode 连接原始观测、独立模型输出及配对候选执行结果。图像原点为左上，距离毫米，角度度。responses 保存模型标识、实际提示、回复、输入文件及尝试次数；模型名称是请求标识。锁定的代码与哈希、三种预算、是否接受、每个动作以及几何估计均可追溯。受调用配额的模型组比较逻辑调用；几何基线共享模型抓取或首件，后续定位的模型调用数较少。分支复用相同抓取状态，动作相同时可共用执行结果。分支、帧和单个零件不应作为新的独立样本。

复算时在解包后的相应子目录运行 python analyze.py gpt-6.2-sol 或 python summarize13.py gpt-6.2-sol；Terra 换成 gpt-6.1-terra。读取归档结果即可复算，不需要调用模型。重跑物理和推理需 MuJoCo 3.8.1、相应的图像和数值库、模型访问和适配后的运行环境。scenes.json、终态、几何真值、QA 和 outcome 仅供模拟器和评价器使用。只可将原提示列出的输入提供给模型。为保护独立测试集，避免使用所附结果调参后再次将这一批称作全新验证。SHA256SUMS 为未压缩文件摘要。数据当前供作者内部审阅，公开许可待作者确定。
"""
        write_text(z,'README-zh.md',text)
        md=collections.defaultdict(dict)
        for d,key in [(S12,'02'),(D,'03'),(S14,'04')]:
            for m in M:
                logs=[rd(p) for p in (d/'responses'/m).glob('*.json')]
                md[key][m]={'logical_acquisitions':len(logs),'transport_attempts':sum(v['attempts'] for v in logs)}
        write_text(z,'logical-request-audit.json',json.dumps(md,indent=2))
        z.writestr('SHA256SUMS',''.join(f'{h}  {n}\n' for n,h in sorted(digest.items())),compress_type=ZIP_DEFLATED)
    with ZipFile(tmp) as z:
        assert z.testzip() is None
        for n,h in digest.items():assert hashlib.sha256(z.read(n)).hexdigest()==h
    tmp.replace(dest)
    print(dest.name,dest.stat().st_size,len(digest),hashlib.sha256(dest.read_bytes()).hexdigest(),flush=True)
if __name__=='__main__':package()

