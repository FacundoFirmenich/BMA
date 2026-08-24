# Registro de misión KCH — Bayesian Markets V11

Estado: `ARGENTINA_EUROSTAT_FIRST_EXECUTION_COMPLETE_UCII_V0_1_GATE_FAILED`.

V11 preserva cuatro resultados diferentes sin colapsarlos:

1. INDEC IPI: freeze prospectiva de julio emitida desde 126 meses oficiales.
2. Eurostat STS España: julio continúa `OUTCOME_PENDING`; no hubo aprendizaje.
3. INDEC UCII: workbook y esquema custodiados, con julio ausente.
4. UCII logit V0.1: `GATE_FAIL` antes de fit por dos ceros sectoriales.

La reparación UCII exige V0.2. Puede mantener target general, logit, modelos,
priors, pesos y calendario porque los sectores estaban excluidos de la
likelihood; sólo puede restringir el soporte estricto al nivel general y
preservar los ceros sectoriales como estados observadores de frontera.

Después de esa reparación y freeze, la misión retorna a la integración coral y
a la criba de fuentes oficiales adicionales. No hay ganador global, pooling
N→1, transferencia de posterior ni promoción automática.
