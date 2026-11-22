# V4 paired-action-risk result

## Locked question
Can a post-measurement controller choose between the frozen model's direct and measured placements more reliably than the fixed model--sensor gate when the 80% measurement list, candidate actions and model-call budget are unchanged?

## Protocol
- 920 V1--V3 rows used only for calibration.
- Two separate ridge risk models predict direct and measured seating probability.
- The candidate with the larger predicted probability is executed. Exact ties fall back to the fixed gate.
- 400 new starts, 40 independent ten-part batches, 320 measured parts, 80% list.
- V4 lock hash: `b29797017c42664ce0683622b00e1692706fa2ba3867976f3a0307c1a3839875`.

## Result
- Fixed gate: 95/400.
- Paired-risk rule: 99/400.
- Gain: 1.00 seat per 100 starts.
- Paired 95% CI: [0.28, 1.97] seats per 100 starts.
- Two-sided paired t-test: p=0.044. One-sided superiority p=0.022.
- Changed decisions: 23. Rescued: 4. Rejected: 0.
- Square: 56/200 vs 53/200. Round: 35/120 vs 34/120. Dual: 8/80 vs 8/80.

## Typical rescues
- `X17P00` (square, gap 2.0): fixed `measured` chose 0, paired-risk `direct` chose 1; p_direct=0.25726118601666487, p_measured=0.20127645653986354; direct=[4.0, 0.0], measured=[4.8, -55.7].
- `X32P03` (square, gap 2.0): fixed `direct` chose 0, paired-risk `measured` chose 1; p_direct=0.5489491302245961, p_measured=0.5909770869760119; direct=[20.5, 0.0], measured=[14.3, 0.0].
- `X14P01` (square, gap 1.0): fixed `direct` chose 0, paired-risk `measured` chose 1; p_direct=0.5396766303669925, p_measured=0.5751990727101193; direct=[-5.7, 0.0], measured=[-3.4, 0.0].
- `X19P07` (round, gap 4.0): fixed `direct` chose 0, paired-risk `measured` chose 1; p_direct=0.30470605895610825, p_measured=0.31184476011348367; direct=[-14.2, 30.0], measured=[-7.0, -12.0].


No changed V4 case was falsely rejected. The result supports a narrow claim about comparing two executable candidates after a measurement. It does not establish that one threshold or one acceptance rule transfers unchanged across sensors or robot interfaces.
