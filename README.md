# Bayesian Markets App (BMA)

BMA is the canonical product name for the physical-market application of the
broader BayME research architecture. BayME remains the name of the general
model and its historical lineage. Frozen historical artifacts keep their
original names; they are not rewritten or silently relabelled as BMA evidence.

BMA learns locally bounded predictive distributions for physical market
activity, participation, quantity and price when those targets are observable
and identifiable. It preserves the sequence:

```text
raw custody -> structured observation -> completeness semantics
-> pre-outcome freeze -> adjudication -> economic posterior
-> future-only prior -> next freeze
```

Evaluation and local jurisdiction cartography are separate from the economic
posterior. No router, aggregate score or `Z_post` ledger may replace the market
model or grant operational authority.

## Current release posture

`0.1.0a2` is an integration alpha, not an industrially validated product. It
contains:

- typed physical-market contracts and explicit missingness semantics;
- immutable JSON custody and manifest verification;
- a multi-jurisdiction evidence registry covering Galicia, Andalucia and both
  Mercabarna lines recovered from the source project;
- a corrected Mercabarna Flor retrospective replay (`v0.4.1`) retained as an
  intermediate diagnostic;
- the expanded `v0.5.0` hurdle replay, trained on 1--20 July and evaluated on
  the pre-frozen 21--31 July window, with activity, participation and quantity
  scored separately by regime and price kept under a degeneracy veto;
- the target-blind `v0.5.1` taxonomy and subfamily audit separating cut
  flowers, live plants, trees/greens, complements and unresolved products;
- a Spain-first/Europe-second industrial source audit: AEAT foreign-trade
  records pass the open, non-biological physical-goods source gate for a
  carefully scoped unit-value pilot; ScrapAd is the stronger transaction-price
  pilot candidate but requires a data agreement; Rheinland-Pfalz timber remains
  technically useful while public reuse is blocked by source terms;
- tests that validate software behavior but do not count as market evidence.

It does **not** establish global superiority, prospective performance in a new
market, commercial validation, or authority to automate procurement.

## BIND 2026

BMA is the Group 10 product: primarily ID43 (demand forecasting) and ID13
(supply-chain planning, procurement and supplier management). ID44 (commercial
intelligence and market monitoring) is complementary, not the governing claim.
The repository is one part of a three-product BIND programme alongside
`{Kwancode}` and KwanDocs; their capabilities and evidence are not inherited by
BMA.

See [docs/BIND_2026_POSITION_ES.md](docs/BIND_2026_POSITION_ES.md) and
[docs/EVIDENCE_BOUNDARY.md](docs/EVIDENCE_BOUNDARY.md).

The canonical continuation contract for the monthly seasonal programme and
the European daily-data line is
[docs/BMA_TERRA_SUCCESSION_20260810_ES.md](docs/BMA_TERRA_SUCCESSION_20260810_ES.md).

## Install and verify

```powershell
python -m pip install -e ".[dev]"
python -m pytest -q
bma evidence validate evidence/registry.json
bma evidence validate evidence/registry_addendum_20260809.json
bma evidence validate evidence/registry_addendum_v051_industrial_20260809.json
```

The Flor replay consumes already structured historical JSON objects. Raw source
files and restricted datasets are deliberately excluded from this public
repository:

```powershell
bma flor-replay `
  --source-v01 <structured-v01-run> `
  --source-v02 <structured-v02-run> `
  --output local-runs/mercabarna-flor-v0.4.1
```

The subfamily audit reuses the immutable v0.5.0 scores without refitting:

```powershell
python -m bma.experiments.mercabarna_flor_v0_5_1 `
  --training <training-objects-2026-07-01-to-20> `
  --source-run <immutable-v0.5.0-run> `
  --output <new-v0.5.1-output>
```

## Repository policy

- Public code and derived receipts do not imply that source datasets may be
  redistributed.
- Empty or unavailable publication is never converted into economic zero.
- Historical negative results, vetoes and `NOT_ESTIMABLE` states remain
  evidence; later versions do not rewrite them.
- There is no global winner. Claims are indexed by market, node, horizon,
  regime, target and decision edge.
