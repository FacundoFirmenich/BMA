# Resincronización nativa Bayesian Markets — checkpoint 2026-08-24

Estado: `PARTIAL_CURRENT_SYNC_WITH_ONE_NATIVE_GAP`.

## Alcance corregido

El registro V5 contiene 16 IDs ChatGPT únicos, aunque una nota interna afirma 15. A esos 16 se agregan las dos tareas Codex primarias del relevo. El usuario añadió después dos conversaciones constitucionales enlazadas. Alcance actual: 20 fuentes nativas.

Las cifras previas 8, 15, 17 y 18 quedan supersedidas por conteo material, no por narrativa.

El registro V5 contiene además dos IDs con 83eb donde las referencias nativas resolubles usan 83ed: Eurostat y PULSO. Se preservan como correcciones egistry_id → native_id; no representan fuentes nuevas.

## Deltas posteriores al corte V5

Corte: commit `14c34a543d987644250ec8cded5922985a772643`, 2026-08-22 00:33:32 +02:00.

### Galicia

El hilo de freeze añadió evidencia de un freeze ex ante del 19 de agosto:

- corte informativo 18 de agosto 12:14:06 CEST;
- 36 distribuciones locales;
- 27 dentro de soporte;
- 9 `OUT_OF_SUPPORT_PREDICTION`;
- outcome del 18 y 19 no usado;
- paquete v0.5.28 verificado 6.148/6.148.

La limitación material es posterior: el artefacto histórico llamado `Z_POST` es realmente un ledger residual. El freeze del 19 no queda invalidado, pero se bloquean freezes posteriores hasta persistir un `Z_post` ad hoc corregido sin doble conteo.

### Andalucía

Se incorporaron outcomes estables para 19, 20 y 21 de agosto, siempre con 16/16 lonjas byte-estables y vacíos tratados como `PENDING_EMPTY_NOT_ZERO`.

- 19 de agosto: Barbate, Algeciras y Huelva; seis celdas relevantes. OCC pendiente.
- 20 de agosto: Barbate, Algeciras, Huelva y Cádiz; siete celdas. OCC y MUT pendientes.
- 21 de agosto: Barbate, Huelva, Punta Umbría y Cádiz; ocho celdas. OCC y MUT pendientes.

Biblioteca no materializó las distribuciones congeladas requeridas y devolvió HTTP 502 / `transfer_failed`. Por tanto no existen todavía pérdidas, PIT, proper scores, posterior cerrado, `Z_post`, `Z-XPL`, `Pi_(r+1)`, reentrenamiento ni pesos nuevos. Los outcomes observados no autorizan una adjudicación sin sus predicciones ex ante exactas.

El hilo antiguo de cosecha sólo añadió errores genéricos de tarea; no contiene una nueva conclusión científica.

### Ontología

Un mensaje tardío de Auditoría Library volvió a expandir erróneamente BUM/BPM/HBP. Se clasifica como `DERIVATIVE_ONTOLOGY_ERROR`.

Vigente:

- BUM = Bayesian Un Markets.
- BPM = Bayesian Physical Markets.
- HBP = Hierarchical Bayes Predictor.
- La relación jerárquica interna exacta sigue `PENDING_PRIMARY_RECONCILIATION`.

### Fuente actualmente no resoluble

El ID `6a7631c8-5e7c-83eb-8c06-13b090137f67` no es resoluble actualmente por el host nativo. Se conserva su estado V5 `READ_TO_EOF`, pero no se declara EOF actual. Estado: `CURRENT_NATIVE_READ_UNAVAILABLE_V5_BASELINE_PRESERVED`.

## Nueva rama constitucional

La conversación `6a80b257-f2c4-83eb-ae2d-3d904680e328` alcanzó EOF en una página y dos turnos. Un agente excede el límite nativo de 20.000 caracteres, de modo que su transporte literal está truncado.

Su enlace troncal `6a53d2d1-1388-83ed-a891-07a16b7b9e2a` fue recorrido hasta EOF: tres páginas y 23 turnos, con dos agentes truncados por transporte. La cronología observable trata principalmente AAD–TCS, TALM/TALON, RDS y autoridad computacional; no demuestra por sí misma que sea el origen primario de BayME–EVE.

Por ello la Constitución General de Mundos Económicos Computables queda como `DERIVED_CONSTITUTIONAL_RESEARCH_CANDIDATE`, no como canon histórico ya acreditado.

Sus elementos candidatos compatibles con Bayesian Markets son:

- tipos epistemológicos que separan identidad, observación, estimación, causalidad, teoría y escenario;
- separación constitucional entre realidad y publicación;
- freeze inmutable y aprendizaje sólo hacia el futuro;
- autoridad teórica situada, nunca ganador universal;
- distinción entre mezcla, fusión y composición;
- prohibición de convertir una incompatibilidad contable en mera baja probabilidad.

Estos elementos no obtienen todavía autoridad para reescribir campañas BPM/HBP, transferir posteriores ni fusionar jurisdicciones.

## Consecuencia

La integración coral deberá contener dos capas separadas:

1. ledger empírico local de freezes, outcomes, posteriores, `Z_post`, abstenciones y gaps de custodia;
2. constitución de tipos y transformaciones permitidas, inicialmente candidata y sin autoridad retrospectiva.

Siguiente acción crítica: incorporar este canon actualizado al contrato coral, mantener abierto el único gap nativo y construir la matriz local Luke–Argentina–Eurostat sin pooling ni ganador agregado.
