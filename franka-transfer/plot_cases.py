from pathlib import Path
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image
import sys
def draw(destination):
    base=Path(__file__).resolve().parent/"records"
    rows=[("F063","gpt-6.2-sol","Sol F063","Connector"),("F001","gpt-6.1-terra","Terra F001","Narrow slot"),("F082","gpt-6.1-terra","Terra F082","D-flat sleeve")]
    fig,axes=plt.subplots(2,3,figsize=(8,3.9))
    for j,(scene,model,title,task) in enumerate(rows):
        for i,branch in enumerate(("first","overhead")):
            folder=base/scene/model/branch
            receipt=json.loads((folder/"receipt.json").read_bytes())
            ax=axes[i,j]
            with Image.open(folder/"final-eye.png") as img:ax.imshow(img)
            ax.set_xticks([]);ax.set_yticks([])
            for spine in ax.spines.values():spine.set_visible(False)
            state="Seated" if receipt["success"] else "Failed"
            ax.set_xlabel(f"{state}   {receipt['endpoint']['part_mm'][2]:.2f} mm",fontsize=9,color="#12634e" if receipt["success"] else "#993c30",labelpad=2)
            if i==0:ax.set_title(title+"   "+task,fontsize=10,pad=4)
            if j==0:ax.set_ylabel("First action" if i==0 else "Overhead action",fontsize=9)
    fig.subplots_adjust(left=.045,right=.997,bottom=.065,top=.93,hspace=.22,wspace=.045)
    fig.savefig(destination,bbox_inches="tight",pad_inches=.02)
if __name__=="__main__":
    draw(sys.argv[1])
