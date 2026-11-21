"""Print the four paired-audit rows from the supplied part-level records."""
from collections import Counter, defaultdict
import csv
from pathlib import Path

counts = defaultdict(Counter)
with Path(__file__).with_name("budget-audit.csv").open(newline="") as handle:
    for row in csv.DictReader(handle):
        measured = int(row["measured"])
        accepts = int(row["post_gate_accepts"])
        gain = int(row["depth_seated"]) - int(row["rgb_seated"])
        key = (row["cohort"], int(row["quota_per_10"]))
        counts[key][measured, accepts, gain] += 1

print("cohort quota skipped_rescue skipped_harm retained_rescue retained_harm")
for (cohort, quota), c in sorted(counts.items(), key=lambda pair: (pair[0][0], -pair[0][1])):
    print(cohort, quota, c[0, 1, 1], c[0, 1, -1], c[1, 0, 1], c[1, 0, -1])
