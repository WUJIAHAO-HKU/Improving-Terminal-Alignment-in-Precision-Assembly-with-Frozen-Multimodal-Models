from pathlib import Path
D=Path(__file__).resolve().parent/'franka-registered'
p=D/'station.py';s=p.read_text().replace('20270341+31*k','20270461+43*k').replace('order=rng.permutation(4)[:len(bom)]','order=rng.permutation(4)[:len(bom)];stock=rng.permutation(np.arange(110,990))[:len(bom)]')
s=s.replace("dict(name=name,x=dx","dict(name=name,stock=int(stock[j]),nest=int(order[j]),x=dx")
p.write_text(s,encoding='utf8')
p=D/'episode.py';s=p.read_text(encoding='utf-8-sig')
s=s.replace("if k=='place':return a.place(j,xy(act['pick'],p['h']),xy(act['base'],.008)+[p['x'],p['y']])", """if k=='place':
        fixture=np.round(np.array(c['target'])/.0005)*.0005
        # Fixture center and staging pockets are commissioned coordinates read before execution.
        # All inspected workpieces remain unmarked. Empty pockets are legal model choices.
        nominal=[[.38,-.135],[.49,-.14],[.62,-.13],[.64,.005]][act['nest']]
        pk=next((np.round(np.array(v['src'])/.0005)*.0005 for v in c['parts'] if v['nest']==act['nest']),nominal)
        return a.place(j,pk,fixture+[p['x'],p['y']])""")
s=s.replace("return a.tighten(j,xy(act['socket'],p['z']+p['h']+.006),.8)","fixture=np.round(np.array(c['target'])/.0005)*.0005;physical=act['socket'];return a.tighten(physical,fixture+[c['bolts'][physical],0],.8)")
p.write_text(s,encoding='utf8')
p=D/'trial.py';s=p.read_text(encoding='utf-8-sig').replace('franka-station-rule15','franka-registered-rule15')
a=s.index('                for key in');b=s.index('                return v,raw',a)
s=s[:a]+"""                if v['op']=='place':assert type(v['nest']) is int and 0<=v['nest']<4
                else:assert v['socket'] in (0,1)
"""+s[b:]
a=s.index("        text='You operate");b=s.index('        act,raw=',a)
s=s[:a]+"""        inventory=sorted([(x['nest'],x['stock']) for x in p])
        text=f'You supervise a simulated Franka Panda from this current unmarked camera view and calibrated production records. Product {c["title"]}. The station accepts registered fixture skills. Input inventory (nest ID, stock number) {inventory}. Full BOM in process order '+str([(x['name'],x['stock']) for x in p])+'. No tools. Reply JSON only. '
        if j<len(p):
            text+=f'Operation {j+1}: grasp the stock belonging to {p[j]["name"]}, then place it at its CAD mating column. The runtime uses surveyed nest and fixture coordinates. Choose the nest ID corresponding to that stock. Return {{"op":"place","nest":integer}}.'
        else:
            text+=f'Next controlled tightening operation: use the {"left" if j==len(p) else "right"} flange fastener. Calibrated driver channel 0 is left and channel 1 is right. Return {{"op":"tighten","socket":integer}}.'
"""+s[b:];p.write_text(s,encoding='utf8')

