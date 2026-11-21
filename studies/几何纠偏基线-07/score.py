from server import samples,Rig,GAPS,read,dump
rows=samples(); actions=read('actions.json');out=[]
for task in ['square','round']:
    for gap in GAPS:
        rig=Rig(task,gap)
        for r in rows:
            if r['task']!=task or r['gap']!=gap:continue
            for mode,a in actions[r['id']].items():
                out.append(dict(id=r['id'],mode=mode,**rig.rollout(r,*a)))
        rig.e.close()
        print(task,gap,len(out),flush=True)
dump('scores.json',out)
