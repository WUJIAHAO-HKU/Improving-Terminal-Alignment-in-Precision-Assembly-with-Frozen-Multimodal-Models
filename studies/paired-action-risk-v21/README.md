# Paired-action-risk V4 independent test

This folder is a sanitized, model-free reproduction package for the final action-acceptance experiment in the precision-assembly study. It contains no server address, account, token, SSH key, or local workstation path.

## Locked design

- Calibration archive: 920 historical rows from V1--V3. No V4 outcomes were used to fit or choose the rule.
- Rule: fit separate calibrated ridge models for the direct and measured candidate actions. On a listed part, execute the candidate with the larger predicted seating probability. Exact ties fall back to the fixed model--sensor score gate. Unlisted parts execute the direct action.
- Independent test: 400 new starts in 40 ten-part batches, 320 listed parts, 80% measurement coverage, the same candidates and calls as the fixed comparator.
- Lock hash: `b29797017c42664ce0683622b00e1692706fa2ba3867976f3a0307c1a3839875` for `v4-lock.json`.

## Reproduction

Install Python 3.10 or newer and SciPy, then run:

```bash
python reproduce_v4.py
```

The script checks the batch structure, recomputes the paired batch confidence interval and writes `reproduced-results.json`. It does not call a model endpoint. Expected result is 95/400 for the fixed comparator and 99/400 for paired-risk acceptance, a gain of 1.00 seat per 100 starts, 95% CI [0.28, 1.97], two-sided paired p=0.044 and one-sided p=0.022. Four parts are rescued and no changed part is falsely rejected.

`examples.json` records the four rescued cases with the two candidate actions, calibrated probabilities and endpoint labels. `v4_yield.pdf` and `v4_paired_deltas.pdf` are derived figures. The full archived response and frame files remain in the private experiment directory and are not required for this reproduction.
