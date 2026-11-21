"""Attach visibility, geometry comparisons, decision decomposition and recorded request costs."""
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
import json,hashlib
import numpy as np
from report12 import D,P,MODELS,read
def main():
    occ=read(D/'visibility.json');f=lambda v:sum(v[k][0] for k in ['cover_','pin_primary'])/max(1,sum(v[k][1] for k in ['cover_','pin_primary']))
    coverage=[f(v) for v in occ.values()];n=sum(x>0 for x in coverage);q=np.quantile(coverage,[.5,1])*100
    tex=f'A rendering audit compared the same oblique image with the guard visible and hidden. It covered pixels of the loose part or the intended mating features in {n}/100 scenes (median {q[0]:.1f}\\\\%, maximum {q[1]:.1f}\\\\% of their combined visible area). The other scenes retained the same guard distribution. '
    dat=dict(visible_overlap=n,median=max(0,float(q[0])),maximum=float(q[1]),models={})
    lines=[]
    for m in MODELS:
        summary=read(D/(m+'-summary.json'));cs=read(D/(m+'-choices.json'));t=summary['totals'];rs=summary['cases']
        retained=badretain=goodretain=missed=spared=0;grips=0
        calls=[read(p) for p in (D/'responses'/m).glob('*.json')]
        assert len(calls)==500
        for r in rs:
            i=r['id'];sel=cs[i]['rank']<=4;out=read(D/'sim'/m/i/'outcomes.json');g=read(D/'sim'/m/i/'grip.json');grips+=int(g['lifted'] and g['bilateral'])
            gain=int(out['overhead']['ok'])-int(out['first']['ok'])
            if not sel and cs[i]['accept']['overhead']:
                missed+=int(gain==1);spared+=int(gain==-1)
            if sel and not cs[i]['accept']['overhead']:
                retained+=1;badretain+=int(gain==1);goodretain+=int(gain==-1)
        dat['models'][m]=dict(bilateral_lifts=grips,overhead_80_retained=retained,rejected_better=badretain,retained_better=goodretain,missed_helpful=missed,skipped_harmful=spared,technical_attempts=sum(v['attempts'] for v in calls),valid_calls=len(calls))
        for mod,label in [('repeat','Repeated RGB'),('depth','Depth'),('overhead','Top RGB')]:
            lines.append(' & '.join([m.split('-')[-1].capitalize(),label,str(t[mod+'_4_switch']),str(t[mod+'_4_gate']),str(t[mod+'_4_geo'])])+r'\\')
    (D/'four-audit.json').write_text(json.dumps(dat,indent=2),encoding='utf8')
    tab=r'''\begin{table}[!htbp]\centering\small
\caption{Equal-call comparison for the four single-part fixtures. Each model policy spends 80 extra requests on the same 100 scenes. The geometric placement controller receives the indicated sensor inputs on the same list, with no placement-model calls.}\label{tab:robot4switch}
\begin{tabular}{@{}llrrr@{}}\toprule Model & Extra input & Always switch & Permit retention & Geometry\\\midrule
'''+ '\n'.join(lines)+'\n'+r'\bottomrule\end{tabular}\end{table}'+'\n'
    p=P/'robot-four.tex';s=p.read_text(encoding='utf8')
    if 'rendering audit compared' not in s:
        s=s.replace('A frozen ranker',tex.strip()+'\n\nA frozen ranker')
        s=s.replace(r'\paperfig{fig9',tab+'\n'+r'\paperfig{fig9')
        p.write_text(s,encoding='utf8')
if __name__=='__main__':main()
