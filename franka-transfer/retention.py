"""Audit retention against compulsory replacement on a fixed list of measured parts."""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def depth_cases():
    study, = (ROOT / "studies").glob("*-06")
    def load(name):
        return json.loads((study / name).read_bytes())
    selected = [s for batch in load("lock.json")["selected"] for s in batch]
    measured = set(selected)
    assert len(selected) == len(measured) == 240
    gates = load("gates.json")
    scores = {(r["id"], r["mode"]): int(r["success"]) for r in load("scores.json")}
    assert measured <= gates.keys() and len(gates) == 300
    for scene in gates:
        yield scene, scene in measured, scores[scene,"original"], scores[scene,"depth"], gates[scene]["depth_accept"]

def franka_cases(model):
    directory = ROOT / "franka-transfer" / "results"
    def read(name):
        with (directory / name).open(encoding="utf-8-sig", newline="") as stream:
            return list(csv.DictReader(stream))
    endpoints = {r["scene"]: r for r in read("paired-outcomes.csv") if r["model"] == model}
    for r in read("decisions.csv"):
        if (r["model"],r["quota"],r["allocation"],r["gate"]) != (model,"4","new","new"):
            continue
        pair = endpoints[r["scene"]]
        first, second = int(pair["first"]), int(pair["overhead"])
        use_second = r["branch"] == "overhead"
        assert int(r["success"]) == (second if use_second else first)
        yield r["scene"], bool(int(r["measured"])), first, second, use_second

def summarize(cases):
    ids = set()
    rescued = rejected = switches = gated = ceiling = measured = 0
    for scene, selected, first, second, accept in cases:
        assert scene not in ids and first in (0,1) and second in (0,1)
        ids.add(scene)
        measured += selected
        switches += second if selected else first
        gated += second if selected and accept else first
        ceiling += max(first,second) if selected else first
        rescued += selected and not accept and first > second
        rejected += selected and not accept and first < second
    assert gated - switches == rescued - rejected and ceiling >= max(gated,switches)
    return len(ids),measured,rescued,rejected,switches,gated,ceiling

if __name__ == "__main__":
    print("cohort,starts,measured,rescued_by_retention,false_rejections,always_switch,allow_retention,fixed_list_ceiling")
    for label, cases in [("Sol-depth",depth_cases()), ("Sol-Franka",franka_cases("gpt-6.2-sol")),
                         ("Terra-Franka",franka_cases("gpt-6.1-terra"))]:
        print(label,*summarize(cases),sep=",")
