"""Pre-study sizing from the previously released CSV. Usage: python sizing.py decisions.csv"""
import csv,sys
from collections import defaultdict
from statistics import mean, variance, pvariance
from math import sqrt,ceil
with open(sys.argv[1],encoding='utf-8-sig',newline='') as f:
    records=list(csv.DictReader(f))
for model in sorted({r['model'] for r in records}):
    for gate in ('switch','retain'):
        sums=defaultdict(list)
        for b in range(20):
            main=[r for r in records if r['model']==model and int(r['batch'])==b and r['quota']=='4' and r['allocation']==r['gate']=='new']
            full={r['scene']:r for r in records if r['model']==model and int(r['batch'])==b and r['quota']=='5' and r['allocation']==r['gate']=='new'}
            assert len(main)==len(full)==5
            for skip in full:
                diff=0
                for r in main:
                    name=r['scene']; change=int(r['overhead'] if gate=='switch' else full[name]['success'])-int(r['first'])
                    diff+=(int(r['measured'])-int(name!=skip))*change
                sums[b].append(20*diff)
        sd=sqrt(variance([mean(v) for v in sums.values()])+mean([pvariance(v) for v in sums.values()]))
        print(model,gate,'SD',round(sd,4),'batches for target three using t approx 2:',ceil((2*sd/3)**2))
