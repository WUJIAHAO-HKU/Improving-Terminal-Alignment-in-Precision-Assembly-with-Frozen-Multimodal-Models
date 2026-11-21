# Reproducing the paired decision tables

Use a fresh checkout or extract the public ZIP in a writable directory. From its root:

**Windows PowerShell**

```powershell
python -m venv --without-pip .venv-review
.venv-review/Scripts/python.exe -E -s -B reviewer/reproduce.py
```

**Linux and macOS**

```sh
python3 -m venv --without-pip .venv-review
.venv-review/bin/python -E -s -B reviewer/reproduce.py
```

No packages are installed. The entry point resolves data relative to its own file. The final line should report 72 verified numeric cells across 12 rows. The script writes table1.txt, table2.txt and audit.json beside itself.

## What is recalculated

Scenes are joined by cohort, model and scene ID. Each cohort has 20 batches of five. The first branch is used unless the list selects the part and the gate accepts the overhead branch. Failed starts stay in the denominator. Inputs include the frozen family gains, disagreement scores, per-scene original and revised gate decisions and both executed simulator endpoints. Ties are broken by ascending scene ID. Expected cells are read only after computing the results.

Table 1 spends four views per batch. Its columns cross original and revised allocation with original and revised acceptance. Expected successes in column order are 66/74/70/79 for four-fixture Sol, 44/45/52/53 for four-fixture Terra, 81/81/82/82 for kit Sol and 33/33/35/35 for kit Terra.

Table 2 fixes revised acceptance and compares family-only, disagreement-only and combined rankings at four and three views per batch. The combined totals at 80/60 views are 79/78 (four-fixture Sol), 53/48 (four-fixture Terra), 82/84 (kit Sol) and 35/34 (kit Terra). Its remaining columns identify changes of list and outcome relative to family alone. audit.json retains the added, removed, rescued and lost scene IDs.

## Other stages

The reviewer replay uses recorded actions and does not require model access, robot software or live inference. For independent-rule analyses inspect stage 15's analysis15.py, policy15.py and allocation_replay.py. Earlier translation and geometry studies retain their own analysis, policies and inputs under studies/. Run historical stage scripts from their own directory after reading the entry point. Dependencies vary by stage (e.g., NumPy, SciPy, OpenCV, MuJoCo and robosuite). Historical model names identify the requested service; a new call need not regenerate archived responses. The public clean-environment verification covers Tables 1 and 2, not a full simulator rerun.

Live collection and transport utilities use example SSH aliases assembly-sim-a/b/c. Configure your own environment, directories, authentication and Python runtime before any live run. Local replay is sufficient to verify the paper tables. Publication hashes can be checked from the root with `sha256sum -c SHA256SUMS` on systems providing that utility.

## Independent four-fixture Franka simulation

From the same environment run `python franka-transfer/reproduce.py`. For the underlying 400 physical labels and all 1,800 decisions, follow the [archive audit instructions](franka-transfer/README.md).

### Fixed-list action acceptance after Table 15

Run `python franka-transfer/retention.py` from the repository root (standard Python). The depth analysis joins the stage-06 locked selection list, depth acceptance flags and original/depth seating endpoints. The Franka analysis joins the revised four-of-five selection and branch decisions to paired physical outcomes. A rescue keeps a successful first action when the second fails; a false rejection keeps a failed first action when the second succeeds. The hindsight ceiling chooses the better endpoint only among measured parts and leaves the first action on every unmeasured part. It describes the two archived actions on each fixed list.
