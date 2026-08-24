# Registro de misión KCH — Bayesian Markets V4

Estado: `ACTIVE_AFTER_FIRST_HBP_EUROSTAT_STS_PROSPECTIVE_FREEZE`.

## Objetivo rector

Preservar BayME como modelo general y BPM, BUM y HBP como familias canónicas;
ejecutar predicción causal estrictamente local; y ampliar la coralidad tipada sin
posterior universal, pooling de jurisdicciones ni ganador global.

## Nueva posición

### HBP Eurostat STS España

La celda `ES × NACE C × PRD × SCA × I21` tiene su primer freeze prospectivo.
La fuente oficial estaba actualizada al 19 de agosto de 2026 y contenía 138 meses
contiguos hasta junio, todos provisionales. Julio no fue solicitado ni observado.
M0 predice 102,9000 y M1 102,9983; sus intervalos del 90 % se superponen casi por
completo. Los pesos 0,5/0,5 permanecen no adjudicativos. Puertos, TED y la coral
se abstienen por falta de alineación causal.

La API ordinaria sigue siendo latest-only. La tabla de vintages `ei_is_m_vtg`
repara parcialmente la custodia histórica, pero su NACE `B-D` incluye energía,
gas y electricidad y queda fuera de la jurisdicción manufacturera autorizada.

### Estados heredados

RMK conserva su cierre causal mixto sin promoción. Argentina conserva crédito,
M3 e IPC, la invalidez histórica UCII y el IPI previo no recuperado. RC15 conserva
julio `NOT_ESTIMABLE_INCOMPLETE_PANEL`. BUM y los demás HBP preservan sus
adjudicaciones, cuarentenas y brechas documentadas en el contrato V3.

## Invariantes

1. Cada mes predice exclusivamente el mes siguiente.
2. Posterior y `Z_post` son específicos del modelo y acumulan sin reset.
3. `Z_post` no es z residual ni `Z_XPL`.
4. País, actividad, unidad, ajuste, fuente y vintage definen jurisdicción.
5. Primera publicación y revisión son bytes distintos.
6. Abstención, pérdida, empate, cuarentena y `NOT_ESTIMABLE` son evidencia.
7. No hay pooling N→1, ganador global ni promoción automática.

## Siguiente acción crítica

Capturar un informe y una serie oficiales acotados de la nueva vintage INDEC
IPI/UCII y una rebanada Prodcom producto-país, sin fitting. Después congelar el
panel observador para Puertos/TED. El outcome Eurostat julio sólo se abrirá cuando
sea publicado y se almacenará como vintage separada.

