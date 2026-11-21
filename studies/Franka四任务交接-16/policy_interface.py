"""Franka four-task policy adapter v1. Python 3.10+, standard library only."""
import json
import math
from pathlib import Path

GAINS = json.loads(Path(__file__).with_name("gain.json").read_text(encoding="utf-8-sig"))

def distance(a, b, length, wrap=False):
    delta = a["yaw"] - b["yaw"]
    if wrap:
        delta = (delta + 90) % 180 - 90
    return math.hypot(a["x"] - b["x"], a["y"] - b["y"]) + length / 2 * math.radians(abs(delta))

def rank_batch(model, rows, allocation, quota):
    """Five public rows from one model and batch. No overhead observations at this stage."""
    if allocation not in ("old", "new") or quota not in (3, 4, 5):
        raise ValueError("Expected old/new allocation and quota 3/4/5")
    if len(rows) != 5 or len({r["scene_id"] for r in rows}) != 5 or len({r["batch_id"] for r in rows}) != 1:
        raise ValueError("Expected five distinct scenes from one batch")
    gains = GAINS["four_" + model]
    scores = {}
    for r in rows:
        if r["gap"] <= 0 or r["size"] <= 0:
            raise ValueError("Clearance and recipe dimension must be positive")
        raw = distance(r["first"], r["eye_ref"], r["size"]) / r["gap"] if r["eye_valid"] else 1e6
        scores[r["scene_id"]] = raw if allocation == "old" else gains[r["task"]] + .035 * min(max(raw, 0), 10) / 10
    ids = sorted(scores, key=lambda i: (-scores[i], i))
    return {i: {"rank": rank, "score": scores[i], "measure": rank <= quota} for rank, i in enumerate(ids, 1)}

def choose_action(row, measure, gate, top=None, top_ref=None, top_valid=False):
    """A skipped part takes its first action. Ties retain first."""
    if gate not in ("old", "new"):
        raise ValueError("Expected old/new gate")
    if not measure:
        return {"selected": "first", "action": row["first"], "revised": False}
    if top is None or (top_valid and top_ref is None):
        raise ValueError("Missing measured candidate or valid reference")
    ref = dict(top_ref if top_valid else row["eye_ref"])
    if gate == "new" and top_valid and row["task"] == "dshaft":
        shift = .14 * row["size"]
        angle = math.radians(ref["yaw"])
        ref["x"] += shift * math.cos(angle)
        ref["y"] += shift * math.sin(angle)
    before = distance(row["first"], ref, row["size"], wrap=gate == "new")
    after = distance(top, ref, row["size"], wrap=gate == "new")
    revised = after < before
    return {"selected": "overhead" if revised else "first", "action": top if revised else row["first"],
            "revised": revised, "distance_first_mm": before, "distance_overhead_mm": after}

