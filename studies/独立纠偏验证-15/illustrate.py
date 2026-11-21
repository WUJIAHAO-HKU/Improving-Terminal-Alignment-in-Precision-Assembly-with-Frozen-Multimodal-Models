from paper15 import D,P,rd
from PIL import Image
import matplotlib.pyplot as plt
def main():
    fig,axes=plt.subplots(3,3,figsize=(6.8,5.4),layout='constrained')
    for row,(m,i,name) in enumerate([('gpt-6.2-sol','H006','Sol, D-flat'),('gpt-6.1-terra','H001','Terra, narrow slot'),('gpt-6.2-sol','H025','Sol, narrow slot')]):
        f=D/'four/sim'/m/i;v=rd(f/'outcomes.json')
        for col,path in enumerate([D/'four/initial'/i/'00-eye.png',f/'branch-first/02-eye.png',f/'branch-overhead/02-eye.png']):
            ax=axes[row,col];img=Image.open(path);ax.imshow(img.crop((86,75,410,298)));ax.set_xticks([]);ax.set_yticks([])
            if not row:ax.set_title(['Before grasp','First command','Overhead command'][col],fontsize=9)
            if col:
                val=v[['first','overhead'][col-1]];ax.set_xlabel(('Seated' if val['ok'] else 'Failed')+f" at {val['height']:.1f} mm",fontsize=8)
            else:ax.set_xlabel(i+' • '+name,fontsize=8)
    fig.savefig(P/'figures/fig13-revision-cases.pdf');plt.close(fig)
    p=P/'independent-rules-panda.tex';s=p.read_text();s=s.replace(r'\section{Articulated-arm simulation',r'\paperfig{fig13-revision-cases.pdf}{Fresh paired rollouts. The revised gate rescued the D-flat sleeve in H006; revised allocation supplied the useful overhead view in H001. H025 illustrates a loss under the revised policy. Endpoint images show the actual simulated release.}{freshPaired}'+'\n'+r'\section{Articulated-arm simulation');p.write_text(s,encoding='utf8')
if __name__=='__main__':main()
