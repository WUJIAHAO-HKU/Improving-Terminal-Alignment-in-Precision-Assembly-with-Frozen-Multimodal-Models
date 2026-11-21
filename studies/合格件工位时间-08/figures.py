from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import numpy as np
from deployment import METHODS,coefficients,envelope
D=Path(__file__).resolve().parent
O=D/'output'
O.mkdir(exist_ok=True)
colors=['#1c504b','#d99c29','#3873ab','#a23d58']
labels=['RGB geometry','Sol 124/240','Sol 182/240','Sol 240/240']
def main():
    groups=json.loads((D/'summary.json').read_text(encoding='utf8'))['groups']
    fig,axes=plt.subplots(1,2,figsize=(11.4,4.1),layout='constrained')
    ax,by=axes;minutes=np.linspace(0,110,551);setups=np.linspace(0,2.2,331)
    coef=np.array([coefficients(groups,m) for m in METHODS])
    lines=coef[:,0,None]+coef[:,1,None]*60*minutes
    for y,color,name in zip(lines,colors,labels):ax.plot(minutes,y,color=color,lw=2,label=name)
    ax.legend(frameon=False,fontsize=9);ax.grid(alpha=.18);ax.set(xlabel='Blocking rework per failure (min)',ylabel='Seconds per qualified unit',title='A   Established recipes, equal setup')
    costs=np.broadcast_to(lines[:,None,:],(4,len(setups),len(minutes))).copy()
    costs[0]+=setups[:,None]*60
    by.pcolormesh(minutes,setups,np.argmin(costs,axis=0),cmap=ListedColormap(colors),vmin=-.5,vmax=3.5,shading='nearest',rasterized=True)
    by.set(xlabel='Blocking rework per failure (min)',ylabel='Extra geometry setup per unit (min)',title='B   Fastest of the four policies')
    fig.savefig(O/'deployment-frontier.pdf');fig.savefig(O/'deployment-frontier.png',dpi=190);plt.close(fig)
if __name__=='__main__':main()

