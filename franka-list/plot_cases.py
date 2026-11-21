"""Render the manuscript case figure directly from the public simulation archives."""
from pathlib import Path
import io
import json
import tarfile
import sys
import numpy as np
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

root = Path(__file__).resolve().parent
cases = [('L028','gpt-6.2-sol','Sol  /  two-dowel cover'),('L003','gpt-6.1-terra','Terra  /  connector'),('L067','gpt-6.1-terra','Terra  /  connector')]
fig, panels = plt.subplots(2, 3, figsize=(7.2, 2.85), gridspec_kw={'height_ratios':[1.1,1]})
for col,(scene, model, title) in enumerate(cases):
    with tarfile.open(root/'archives'/f'batch-{int(scene[1:])//5:02}.tgz') as batch:
        image = Image.open(io.BytesIO(batch.extractfile(scene+'/initial-eye.png').read()))
        ax = panels[0,col]
        ax.imshow(image.crop((100,120,390,290)))
        ax.set_title(scene+'  |  '+title,fontsize=9,loc='left')
        ax.axis('off')
        ax = panels[1,col]
        ax.axhspan(6.6,7.5,color='#d9e9e3')
        for x,branch in enumerate(('first','overhead')):
            row = json.load(batch.extractfile(f'{scene}/{model}/{branch}/receipt.json'))
            height = row['endpoint']['part_mm'][2]
            color = '#166452' if row['success'] else '#aa4939'
            ax.plot(x,height,marker='o' if row['success'] else 'x',color=color,markersize=6,mew=1.4)
            ax.annotate(f'{height:.2f}',(x,height),xytext=(0,5),textcoords='offset points',ha='center',fontsize=8)
        ax.set_xlim(-.5,1.5);ax.set_ylim(4,23)
        ax.set_xticks([0,1],['First (kept)','Overhead'],fontsize=8)
        ax.tick_params(axis='both',labelsize=8,length=2)
        ax.set_yticks([7,14,21])
        if col==0:ax.set_ylabel('Released height (mm)',fontsize=8)
        else:ax.set_yticklabels([])
        ax.spines[['top','right']].set_visible(False)
fig.legend(handles=[Line2D([],[],marker='o',ls='',color='#166452',label='Seated'),Line2D([],[],marker='x',ls='',color='#aa4939',label='Failed')],loc='lower center',ncol=2,frameon=False,fontsize=8)
fig.subplots_adjust(left=.08,right=.99,bottom=.22,top=.90,wspace=.26,hspace=.20)
fig.savefig(sys.argv[1],bbox_inches='tight')
