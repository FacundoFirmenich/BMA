# INVALID EXPERIMENT — AEAT v0.6.2

Status: `INVALID_EXPERIMENT_WRONG_1M_TO_1M_CONTRACT`

Date: 2026-08-09

The experiment `ES-AEAT-CH72-MONTHLY-MATCHED-GAMES-2024-V0.6.2` is invalid
for scientific inference, model comparison, promotion, BIND claims, or BMA
performance evidence.

## Cause

The executor implemented matched `N training months -> N target months` games
for `N in {1,2,3,4,5,6}` and accumulated target documents in the raw history.
The user-mandated operational contract is stricter:

`one monthly observation block -> one immediately following monthly target`

repeated as a sliding sequence. A realized target may update a carried Bayesian
state only after adjudication, but it becomes the sole observational month for
the next one-month prediction. Multiple raw months must not be pooled as the
training observation block for a target month.

## Evidence consequence

- Do not inspect or report v0.6.2 performance metrics.
- Do not reuse its fitted weights, predictions, scores, or posterior state.
- Preserve the artifacts only as adverse protocol evidence.
- Any successor requires a new preregistration, new implementation hash, fresh
  state, and explicit `1 month -> 1 month` transition receipts.

## Quarantined output

`evidence/runs/aeat-ch72-monthly-matched-games-v0.6.2/`

The directory completed before the stop request was received. No matching
process remained running when checked. Completion does not cure the protocol
violation.
