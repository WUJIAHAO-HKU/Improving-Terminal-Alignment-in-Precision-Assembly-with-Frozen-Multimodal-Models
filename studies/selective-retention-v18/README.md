# Selective retention v1.0

This supplement contains the prospectively locked, calibration-only action-acceptance experiment. The calibration rows are summarized in `lock.json`. `parts.csv` contains 640 de-identified part-level outcomes from 32 Sol-depth batches and 32 batches for each of two Franka overhead model cohorts. The same candidate-action lists and 80% measurement lists are used within each cohort.

The policy is fixed before the independent batches. It defaults to the measured action. It keeps the original action only when the old observable gate is positive and the model/sensor/family calibration stratum has at least eight discordant cases with an exact one-sided binomial p-value below 0.05. The fixed comparator is one complete rule selected on calibration data.

Run `python reproduce.py` with Python 3.11 or later and NumPy/SciPy installed. It writes `results.json` and reports paired batch intervals. `checks.json` records the final endpoint audit. `examples.json` points to the included failure categories without containing machine addresses or credentials.
