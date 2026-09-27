# BayME–M_C Gate V — prospective field spine and round-zero calibration

**State:** `INSTRUMENTATION_CANDIDATE / +0`  
**Execution authority:** none  
**Direct M_C status:** `PRIVACY_GATE_FAILED`  
**Verdict:** `PASS_WITH_NO_POLICY_EXPOSURE`

## Material result

Gate V implements the prospective evidence spine required to identify a future
M_C intervention without fabricating observations. It adds a purpose-bound
pseudonymisation primitive, an offline SQLite hash-chain, idempotent event
capture, blocked balanced stepped-wedge assignment, explicit assignment →
exposure → outcome lineage, independent adjudication, and a fail-closed direct
M_C estimability gate.

Round `BAYME-MC-CAL-000` calibrated the price/quantity sensor against a real
official geolocated price-and-volume source. It transformed
**36,667 raw rows** into **11,418
validated aggregate events**, spanning **1,126 local
contexts**, **5 products**, and the period
**2016-06-01–2026-09-27**.

The calibration contains no household, assignment or M_C exposure data.
Accordingly, the direct M_C gate refused estimation rather than treating public
price observations as policy evidence.

## Opening rule for a real prospective round

A direct estimand can become `ESTIMABLE_SHADOW/+0` only after all of the
following coexist:

- at least 200 complete delivered exposures;
- at least 80 treated and 80 comparator exposures;
- known assignment probability for every unit;
- one exact freeze and policy version per exposure;
- 90 supported follow-up days;
- valid privacy-impact and data-collection authority receipts;
- independent outcome adjudication;
- no randomized reduction of the universal rights floor;
- an observed outcome in every promoted exposure context.

Even then, estimability grants neither causal authority nor policy authority.

## Integrity

- Tests: `..............................                                           [100%]`
- Freeze: `freeze-72705149-8399-4c33-8e72-08620b79674d`
- Manifest SHA-256: `da80d4c9564d76827bc0a117828216b9f88b5ad57cf0f73c909676847273ebc6`
- Frozen files: 66
- Field-buffer head: `376f4cfe576032a496053541baa72b1fd17d0c37f9370a22f6f044e9185f9df6`

## What remains open

No M_C policy assignment, exposure, household outcome, supply-credit exposure,
material-wellbeing measure or independent field adjudication exists yet. The
next gate is therefore an authorized, privacy-reviewed, local shadow pilot—not
a further retrospective macro extrapolation.
