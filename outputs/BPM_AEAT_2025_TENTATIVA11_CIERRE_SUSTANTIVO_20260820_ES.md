# BPM–AEAT capítulo 72 — cierre sustantivo 2025, tentativa 11

Fecha: 2026-08-20  
Estado: `EXECUTED_AND_INDEPENDENTLY_AUDITED_RETROSPECTIVE_UNUSED_CONFIRMATORY_VALIDATION`  
Promoción: `PROHIBITED`  
Ganador global: `null`

## Resultado que cambia la posición

Bayesian Physics Markets (BPM) queda mejor posicionado para sostener que la memoria estacional contiene señal predictiva **local y dependiente de fase**, no para sostener una familia estacional superior en general. De los ocho tests variable × mes congelados antes de abrir los outcomes, siete mejoran M0 y uno empeora. Los pesos prequentiales diagnósticos terminan concentrados en M0 para las tres variables; por contrato esos pesos no pueden revocar ni rescatar los tests locales congelados.

| Mes | Variable | Modelo seleccionado | Seleccionado | M0 | Diferencia | Cambio relativo |
|---|---|---:|---:|---:|---:|---:|
| 2025-03 | valor unitario estadístico | M1 | 0.481538620062 | 0.487936648269 | -0.006398028207 | -1.311242% |
| 2025-06 | participación | M1 | 0.106058665990 | 0.106109378507 | -0.000050712516 | -0.047793% |
| 2025-07 | participación | M1 | 0.104540048326 | 0.104792020048 | -0.000251971722 | -0.240449% |
| 2025-08 | participación | M1 | 0.107437450924 | 0.107890294096 | -0.000452843171 | -0.419726% |
| 2025-09 | participación | M1 | 0.100427144684 | 0.100501817242 | -0.000074672559 | -0.074300% |
| 2025-09 | cantidad | M2 | 1.308167461972 | 1.393198174589 | -0.085030712618 | -6.103275% |
| 2025-10 | participación | M2 | 0.103705348504 | 0.103653835464 | +0.000051513041 | +0.049697% |
| 2025-11 | participación | M2 | 0.101325883953 | 0.102127437246 | -0.000801553292 | -0.784856% |

Una diferencia negativa mejora la pérdida. Octubre es el único resultado adverso primario y se conserva. Diciembre actualiza posterior y Z_post, pero permanece `ABSTAIN_YEAR_END_UNCALIBRATED` para las tres variables.

## Significado científico y epistemológico

- La señal más grande aparece en cantidad de septiembre: el residuo mensual jerárquico M2 reduce MALE aproximadamente 6.10% frente a M0. Es evidencia de fase local en esa variable/mes/jurisdicción, no de un producto físico identificado por CN4 ni de una ventaja anual general.
- La participación armónica M1 mejora junio–septiembre en los cuatro meses preregistrados, pero las magnitudes son pequeñas. La repetición direccional refuerza la hipótesis de una fase estival amplia; no identifica por sí sola el mecanismo causal ni autoriza generalización fuera de AEAT capítulo 72.
- Participación M2 cambia de signo entre octubre y noviembre: pérdida mínima en octubre y mejora mayor en noviembre. Esto impide tratar el residuo jerárquico otoñal como uniformemente beneficioso.
- Valor unitario mejora en marzo bajo M1, pero sigue siendo valor estadístico aduanero por kg, nunca precio spot, puja o transacción individual.
- La concentración final de pesos en M0 informa que, acumulada por log-score dentro de esta cadena, la familia estacional no merece autoridad general. No invalida los tests locales precongelados y tampoco permite declarar un ganador global.

## Causalidad, custodia y reparaciones

La cadena 2022→2025 fue reconstruida sin reset de posterior, Z_post, memoria estacional ni pesos. Cada target 2025 siguió `freeze → outcome oficial → adjudicación → posterior/Z_post → freeze siguiente`; no hubo pooling de N meses para un solo target.

Las tentativas adversas se preservan. La tentativa 9 falló porque el miembro descomprimido de septiembre medía 297,819,984 bytes y superaba el límite anterior de 250,000,000. La tentativa 10 falló en la resolución DNS de marzo, en byte cero, después de cerrar enero y febrero. La tentativa 11 reutilizó una sesión HTTPS y aplicó esperas deterministas de 2 y 10 segundos; mantuvo TLS, Content-Range, tamaño constante y límite comprimido de 30 MB. Esta reparación atravesó enero–diciembre sin persistir ZIP raw.

## Auditoría independiente

- 62 archivos del manifiesto verificados por SHA-256.
- 36 eventos en orden causal exacto.
- 12 freezes, 12 meses estructurados, 12 adjudicaciones, 12 priors y 12 Z_post.
- Ocho tests primarios: 7 mejoras, 1 pérdida, 0 empates.
- Diciembre: tres abstenciones primarias.
- `aggregate_winner=null`; promoción prohibida; cero ZIP raw.

Recibo: `governance/BPM_AEAT_2025_ATTEMPT11_AUDIT.json`.

## Frontera de evidencia y consecuencia

La campaña es retrospectiva, usa el primer año AEAT no utilizado para descubrir el selector, no es ciega y no valida producción, BIND, automatización ni transferencia a Argentina, Eurostat u otra fuente. Sí confirma que BPM puede extraer señal local útil incluso de una base mensual aduanera hostil, preservando resultados pequeños, adversos y abstenciones.

El siguiente paso decisivo no es buscar una victoria agregada. Es integrar las campañas Argentina y Eurostat como jurisdicciones HBP separadas, normalizar sus contratos hacia una interfaz coral y medir complementariedad sólo sobre claims homologables. Después se buscarán nuevas fuentes públicas industriales que agreguen resolución o variables genuinamente nuevas.
