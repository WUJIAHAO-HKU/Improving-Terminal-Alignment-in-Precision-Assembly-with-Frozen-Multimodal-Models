"""Rebuild the Franka transfer table and paired examples using only standard Python."""
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, stdev

ROOT = Path(__file__).resolve().parent
MODELS = ("gpt-6.2-sol", "gpt-6.1-terra")
T975_19 = 2.093024054408263  # 97.5th percentile for 19 degrees of freedom

def read_csv(name):
    with (ROOT / "results" / name).open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))

def rebuild():
    rows = read_csv("decisions.csv")
    outcomes = read_csv("paired-outcomes.csv")
    pairs = {(r["model"], r["scene"]): r for r in outcomes}
    expected_ni = {(r["model"], int(r["saving_pct"])): r for r in read_csv("noninferiority.csv")}
    assert len(rows) == 1800 and len(pairs) == len(outcomes) == 200
    groups = defaultdict(dict)
    for row in rows:
        model, scene, quota = row["model"], row["scene"], int(row["quota"])
        pair = pairs[model, scene]
        assert all(row[k] == pair[k] for k in ("first","overhead","batch","task","lifted"))
        group = groups[model, quota, row["allocation"], row["gate"]]
        assert scene not in group
        selected = int(row["rank"]) <= quota
        assert int(row["measured"]) == selected
        assert selected or row["branch"] == "first"
        assert int(row["success"]) == int(pair[row["branch"]])
        group[scene] = row
    assert len(groups) == 18 and all(len(group)==100 for group in groups.values())
    print("Model,views,full_gated,budget_gated,pp_difference,lower_97.5_pp,decision,same_list_switch,same_list_retain")
    for model in MODELS:
        full = groups[model,5,"new","new"]
        assert all(int(r["lifted"]) for r in full.values())
        full_count = sum(int(r["success"]) for r in full.values())
        first_passed = False
        for quota in (4,3):
            budget = groups[model,quota,"new","new"]
            by_batch = defaultdict(list)
            measured = Counter()
            switched = 0
            for scene,row in budget.items():
                pair = pairs[model,scene]
                batch = row["batch"]
                by_batch[batch].append(int(row["success"]) - int(full[scene]["success"]))
                measured[batch] += int(row["measured"])
                switched += int(pair["overhead"] if int(row["measured"]) else pair["first"])
            assert len(by_batch)==20 and all(len(v)==5 for v in by_batch.values())
            assert all(n==quota for n in measured.values())
            differences = [100*mean(v) for v in by_batch.values()]
            delta = mean(differences)
            sd = stdev(differences)
            lower = delta - T975_19*sd/math.sqrt(20)
            status = "pass" if sd>0 and lower> -5 else ("did not pass" if sd>0 else "inconclusive (zero variance)")
            if quota==4:
                first_passed = status=="pass"
            elif not first_passed:
                status = "descriptive only"
            seated = sum(int(r["success"]) for r in budget.values())
            ref = expected_ni[model,100-20*quota]
            assert (seated,full_count,status)==(int(ref["budget_success"]),int(ref["full_success"]),ref["status"])
            assert abs(lower-float(ref["lower_97_5_pp"]))<1e-5
            print(f"{model},{20*quota},{full_count},{seated},{delta:.2f},{lower:.2f},{status},{switched},{seated}")
        print("Valid overhead references:",model,sum(int(pairs[model,s]["top_valid"]) for s in full),"/ 100")
    for model,scene in [(MODELS[0],"F063"),(MODELS[1],"F082"),(MODELS[1],"F062"),(MODELS[1],"F001")]:
        a,b=(groups[model,4,g,g][scene] for g in ("old","new"))
        folder=ROOT/"records"/scene/model
        receipts=[json.loads((folder/k/"receipt.json").read_bytes()) for k in ("first","overhead")]
        assert all(r["checkpoint_id"]==a["checkpoint_id"]==b["checkpoint_id"] for r in receipts)
        for k,r in zip(("first","overhead"),receipts):
            assert int(r["success"])==int(b[k])
        print(scene,model,"old/new:",a["branch"],b["branch"],"measured:",b["measured"],
              "first/overhead height mm:",*[round(r["endpoint"]["part_mm"][2],2) for r in receipts])
if __name__=="__main__":
    rebuild()
