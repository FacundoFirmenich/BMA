# Checkpoint de reclasificación BPM / BUM / HBP V4

La posición clasificatoria mejora respecto de V3 porque la identidad canónica
ya no mezcla las familias nuevas con nombres de procedencia históricos.

## Corrección observada

- Los únicos destinos positivos son BPM, BUM y HBP.
- BMA queda absorbido por BPM y no reaparece como identidad canónica.
- BayME, BayME Pulse y BayME EVE sobreviven sólo como
  `historical_source_lineage`.
- Se sustituyeron identificadores residuales con prefijos `bma-`, `bayme-` y
  `eve-` por identificadores de la familia nueva.
- Se corrigió la contradicción por la que el índice reconocía una unidad BUM
  mientras el README afirmaba que BUM estaba vacío.
- `UNCLASSIFIED_PENDING_CONTENT_REVIEW` no es una cuarta categoría: es un
  estado de abstención hasta poder leer el contenido indivisible.

## Frontera de evidencia

Esta operación cambia una vista derivada y su semántica de identidad. No mueve,
renombra ni reescribe los experimentos originales; tampoco convierte diseños en
ejecuciones. Resultados adversos, abstenciones, intentos fallidos y huecos de
custodia conservan su estado histórico.

## Consecuencia experimental

La cadena AEAT 2022-2024 y su mini-ejecución estacional pertenecen a BPM por
tratar comercio de bienes físicos. CN4 y CN8 siguen siendo niveles de
observación, no categorías de producto ni familias canónicas. Cualquier nueva
mini-ejecución debe registrarse como unidad BPM y conservar por separado sus
categorías internas preregistradas; reclasificar el proyecto no autoriza a
mezclarlas.

## Bloqueo y siguiente acción

La recolección aún no es exhaustiva y hay una conversación mixta con transporte
truncado. El siguiente paso es completar el censo multirraíz y, después,
contrastar cada categoría interna de la mini-ejecución contra su definición
prerregistrada antes de volver a correrla.
