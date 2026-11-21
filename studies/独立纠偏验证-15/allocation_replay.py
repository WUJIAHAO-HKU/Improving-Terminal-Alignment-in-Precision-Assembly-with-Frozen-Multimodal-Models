"""Replay frozen measurement lists. Run beside four/, kits/ and independent-results.json."""
import json
from collections import defaultdict
from pathlib import Path
from policy15 import score

ROOT = Path(__file__).resolve().parent
MODELS = ("gpt-6.2-sol", "gpt-6.1-terra")
RULES = ("family", "disagreement", "combined", "capped_disagreement")

def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

def replay(cohort, model, reference):
    folder = ROOT / cohort
    choices = read(folder / (model + "-choices.json"))
    gains = read(folder / "gain.json")[cohort + "_" + model]
    scenes = read(folder / "scenes.json")
    batches = defaultdict(list)
    rows = {}
    for scene in scenes:
        key = scene["id"]
        c = choices[key]
        assert c["batch"] == scene["batch"] and key not in rows
        batches[c["batch"]].append(key)
        discrepancy = c["old_pre"]
        gain = gains[c["cat"]]
        priorities = dict(family=gain, disagreement=discrepancy,
                          combined=score(discrepancy, gain), capped_disagreement=score(discrepancy, 0))
        assert priorities["combined"] == c["new_pre"]
        if cohort == "four":
            outcome = read(folder / "sim" / model / key / "outcomes.json")
            field = "ok"
        else:
            outcome = read(folder / "runs" / model / key / "results.json")
            field = "complete"
        first, top = (int(outcome[k][field]) for k in ("first", "overhead"))
        rows[key] = dict(batch=c["batch"], family=c["cat"], first=first, overhead=top,
                         accept=c["new_accept"], priority=priorities, rank={})
    assert len(rows) == 100 and len(batches) == 20
    for keys in batches.values():
        assert len(keys) == 5
        for rule in RULES:
            ordered = sorted(keys, key=lambda key: (-rows[key]["priority"][rule], key))
            for rank, key in enumerate(ordered, 1):
                rows[key]["rank"][rule] = rank
                if rule in ("disagreement", "combined"):
                    assert rank == choices[key]["old_rank" if rule == "disagreement" else "new_rank"]
    archive = {v["id"]: v for v in reference["rows"]}
    summary = {}
    for quota in (4, 3):
        selected = {rule: {k for k,v in rows.items() if v["rank"][rule] <= quota} for rule in RULES}
        seated = {rule: {k for k,v in rows.items() if
                         (v["overhead"] if k in selected[rule] and v["accept"] else v["first"])} for rule in RULES}
        assert all(len(s) == quota * len(batches) for s in selected.values())
        assert seated["combined"] == {k for k,v in archive.items() if v[f"new_new_{quota}"]}
        assert seated["disagreement"] == {k for k,v in archive.items() if v[f"old_new_{quota}"]}
        cross = {k: sum(v[k + "_" + str(quota)] for v in archive.values())
                 for k in ("old_old", "old_new", "new_old", "new_new")}
        contrasts = {}
        for rule in RULES:
            added = selected["combined"] - selected[rule]
            removed = selected[rule] - selected["combined"]
            rescued = seated["combined"] - seated[rule]
            lost = seated[rule] - seated["combined"]
            assert len(added) == len(removed) and (rescued | lost) <= (added | removed)
            contrasts[rule] = {label: sorted(s) for label,s in
                               (("added",added),("removed",removed),("rescued",rescued),("lost",lost))}
        # Average over all uniform tie resolutions at each batch cutoff.
        expected_family = 0.0
        for keys in batches.values():
            gains_in_batch = [rows[k]["priority"]["family"] for k in keys]
            cutoff = sorted(gains_in_batch, reverse=True)[quota - 1]
            open_slots = quota - sum(g > cutoff for g in gains_in_batch)
            tie_probability = open_slots / gains_in_batch.count(cutoff)
            for key, g in zip(keys, gains_in_batch):
                prob = 1.0 if g > cutoff else tie_probability if g == cutoff else 0.0
                r = rows[key]
                expected_family += r["first"] + prob * r["accept"] * (r["overhead"] - r["first"])
        summary[quota] = dict(seated={r:len(s) for r,s in seated.items()},cross=cross,combined_vs=contrasts,
                              family_expected_under_random_ties=expected_family)
    return dict(rows=rows, summary=summary)

if __name__ == "__main__":
    ref = read(ROOT / "independent-results.json")
    out = {}
    for cohort in ("four","kits"):
        out[cohort] = {}
        for model in MODELS:
            result = replay(cohort, model, ref[cohort][model])
            out[cohort][model] = result
            for q,entry in result["summary"].items():
                print(cohort, model, q, entry["seated"], entry["cross"],
                      {r: tuple(len(v[k]) for k in ("added","rescued","lost")) for r,v in entry["combined_vs"].items()})
    (ROOT / "allocation-replay.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
