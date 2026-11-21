# Improving Terminal Alignment in Precision Assembly with Frozen Multimodal Models

Experimental data and analysis code for *When to Measure and When to Revise an Action*. The study asks how to spend a fixed quota of additional views across a mixed batch, then whether to execute the revised placement. The released robot trajectories and fastener traces were obtained in simulation.

## Reproduce Tables 1 and 2 (manuscript page 8)

From the repository root, run `python reviewer/reproduce.py` with Python 3.8 or newer. The script needs only the Python standard library. In a few seconds it verifies input hashes, reconstructs all twelve rows, compares 72 numeric entries with the published tables, prints both tables and writes per-scene outcomes and changes of list. See [the reproduction instructions](REPRODUCING.md) for clean-environment commands, denominators and the expected results.

## Data map

- [reviewer/](reviewer/) contains the exact inputs for the two main mechanism tables. Four fixtures and multi-component kits each contribute 100 unique scenes, paired across models. Replays of two actions on one scene are paired observations.
- [dataset-v0.1/](dataset-v0.1/) contains the indexed terminal-alignment benchmark, observations and separate evaluator labels. It covers 1,450 conditions, including development and repeated-clearance scenes.
- [studies/](studies/) retains the experiment directories and their original relative layout for cross-stage analysis. The suffix is the study number. Stages 01–04 cover tolerance sweeps and measurement/acceptance development and validation. Stages 05–08 cover workstation conditions, equal-call controls, geometric correction and blocking time. Stage 09 covers orientation. Stage 10 was a planning directory. Stages 11–14 cover the simulated gripper, four unmarked fixtures, 20 assembly recipes and keyed connectors. Stage 15 contains the locked revisions, independent cohorts and articulated-arm simulations. Stage 16 contains the collaborator interface and example. Its contents are handoff materials, not additional completed experiments.
- [paper-analysis/](paper-analysis/) contains supporting numerical evidence and figure-generation code. Some original illustration and report builders reference presentation assets outside the data release.
- [documentation/](documentation/) retains cohort notes and the logical-request audit. Older notes describe the original bundle names. Their data are unpacked under the corresponding study directories.

The archive includes initial and post-grasp images, available depth and simulator states, recorded model requests and responses, candidate poses, batch decisions, physical endpoints, timing records and retained videos. Different stages retain different fields. Historical hashes refer to original files before publication edits. The root SHA256SUMS covers the released files. Private connection settings, caches, wheels and redundant transport archives are omitted. Source platform paths in provenance records are made repository relative. See [licensing and provenance](LICENSE.md).

## Interpretation

On four independent fixtures both models met the five-percentage-point noninferiority margin at 80 overhead views per 100 parts. The same guarantee was not established on multi-component kits. Family-level gains were more consistently useful than initial disagreement for allocating views. The 41.7-minute full-sensing crossover assumes equal setup and successful on-station repair in a separate 240-part simulation study.
