# HBP Eurostat STS España: primer freeze causal manufacturero

Estado: `FROZEN_PRE_OUTCOME`.

## Resultado observado

HBP queda mejor posicionado: la capa Eurostat STS dejó de ser únicamente una
integración documental y ahora contiene una primera predicción prospectiva
inmutable para julio de 2026. La respuesta oficial capturada después de la
preregistración contiene 138 meses contiguos, desde enero de 2015 hasta junio de
2026, y 137 transiciones. Las 138 observaciones conservan el indicador `p`
(provisional). No se solicitó ni abrió el valor de julio.

La predicción de persistencia M0 es **102,9000** puntos, con intervalo predictivo
central del 90 % **[96,4227; 109,8124]**. La deriva bayesiana local M1 predice
**102,9983**, con intervalo **[96,4940; 109,9410]**. La diferencia puntual es
sólo 0,0983 puntos: antes de observar julio no hay evidencia para preferir una
familia. Los pesos permanecen congelados en 0,5/0,5 y no tienen autoridad de
promoción.

`M2_port`, `M2_ted` y `M3_coral` se abstienen porque todavía no existe un panel
observador causalmente alineado y disponible antes del corte. Esta abstención es
el resultado correcto; inventar imputaciones o usar observadores publicados
después habría contaminado el forecast.

## Comparación con el checkpoint anterior

Antes sólo había un probe de esquema de 18 meses, expresamente excluido de fit y
score. Ahora hay una cadena nueva, con priors, pesos, soporte, consulta, hashes,
posterior y recovery congelados. El probe anterior permanece excluido; la
respuesta de campaña es una captura nueva posterior a la preregistración.

La búsqueda oficial también refinó la conclusión sobre revisiones. La API STS
ordinaria conserva únicamente la última versión. Eurostat sí publica la tabla
especial `ei_is_m_vtg`, que permite recuperar vintages españolas, pero sólo para
NACE `B-D`. Esa agregación incluye minería, electricidad y gas, por lo que no
puede gobernar este target manufacturero bajo las exclusiones vigentes. Se
preserva como evidencia de revisión, no como outcome alternativo.

## Significado científico y epistemológico

La predicción es causal respecto del outcome de julio: fue emitida cuando la
fuente sólo llegaba a junio. No es, sin embargo, un holdout de diseño totalmente
ciego: el probe de esquema del día anterior había expuesto valores de enero de
2025 a junio de 2026. Esa exposición está declarada y no invalida el carácter
prospectivo del target, pero prohíbe presentar este primer evento como validación
independiente de selección de arquitectura.

M0 y M1 usan la misma jurisdicción `ES × NACE C × PRD × SCA × I21`. M0 modela
log-cambios con media fija cero; M1 aprende una deriva mensual mediante un
posterior Normal–Gamma inversa. Ambos acumulan sin reset. `Z_post` es el estado
posterior futuro de cada modelo, no un z residual ni `Z_XPL`. No existe pooling
con RC15, Argentina, puertos, TED, otros países o meses condensados.

## Reparabilidad e incertidumbre

La provisionalidad es reparable conservando cada respuesta futura como una
vintage distinta. El historial `ei_is_m_vtg` puede cuantificar revisiones de
industria total, pero no separar retroactivamente manufactura de energía. Para
NACE C la única solución válida es captura prospectiva continua.

La incertidumbre predictiva sigue alta: los intervalos abarcan aproximadamente
13,4 puntos y los dos modelos son casi indistinguibles. Un único outcome no
autorizará conclusión general. La utilidad real aparecerá en la cadena
precuencial de múltiples meses, conservando cada pérdida, empate, abstención y
revisión.

## Evidencia y siguiente acción

- Preregistración: `preregistrations/HBP_EUROSTAT_STS_ES_C_2026_07_FREEZE_V0.1.json`.
- Raw oficial: `evidence/runs/hbp-eurostat-sts-es-c-v0.1-2026-07-freeze/eurostat_sts_es_c_through_2026_06.json`.
- Posterior: `evidence/runs/hbp-eurostat-sts-es-c-v0.1-2026-07-freeze/posterior_z_post.json`.
- Freeze: `evidence/runs/hbp-eurostat-sts-es-c-v0.1-2026-07-freeze/forecast_freeze.json`.

El siguiente paso crítico inmediato no es abrir julio antes de su publicación ni
ajustar contra él. Es capturar una nueva vintage oficial INDEC IPI/UCII y una
rebanada Prodcom producto-país, ambas sin fitting; después se podrá construir el
panel observador causal para los brazos corales y adjudicar julio cuando exista.

