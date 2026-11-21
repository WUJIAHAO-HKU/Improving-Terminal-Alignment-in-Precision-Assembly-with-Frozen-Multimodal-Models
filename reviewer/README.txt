Reproduce manuscript Tables 1 and 2 | Precision assembly

Extract the complete ZIP to a writable folder. From that folder run
    python reproduce.py
Python 3.8 or later, standard library only. No model keys, network, robot, GPU or
simulator installation are needed. The script prints both tables, checks 72
numeric cells against the manuscript and writes table1.txt, table2.txt and
audit.json. Expected cells were transcribed programmatically from the LaTeX
tables. They are read only after all results have been calculated.

Input provenance: independent locked revision, four fixtures (four/) and 20 kit
recipes (kits/), 100 unique scenes per cohort, paired across Sol and Terra.
scenes.json supplies scene and batch IDs. gain.json supplies frozen historical
gains. Model choices files supply initial disagreement, category, old/new gate
decisions and reference ranks. The first and overhead simulator endpoints
come from sim/<model>/<scene>/outcomes.json (ok) or runs/<model>/<scene>/
results.json (complete). Checked hashes cover the distributed raw inputs and
policy15.py. No aggregate experiment results serve as calculation inputs.

In each batch of five, select the highest four or three scores. Resolve ties
by ascending scene ID. Use the overhead endpoint only when selected and the
specified gate accepted it. Otherwise count the first endpoint. Table 1 crosses
the two rankings with the two archived gates. Table 2 fixes revised acceptance.
Swaps counts additions to the family-only list, rescued and lost count changes
in final outcomes. audit.json includes every ID in each change set and ranks
and both endpoints per case. This package replays recorded decisions. It does
not recreate inference, camera geometry or robot trajectories from scratch.
