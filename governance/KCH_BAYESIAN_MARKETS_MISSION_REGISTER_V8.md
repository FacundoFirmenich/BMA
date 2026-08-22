# Registro de misión KCH — Bayesian Markets V8

Estado: `ACTIVE_LUKE_PROTOCOL_FROZEN_BEFORE_HISTORICAL_ACQUISITION`.

## Objetivo rector

Completar la campaña Luke de madera finlandesa bajo secuencia mensual
prequential, congelar una predicción prospectiva para agosto de 2026 y, después
de su cierre, integrar cabalmente las líneas Argentina y Eurostat. A partir de
esa integración se buscarán fuentes adicionales que produzcan saltos
cuantitativos y cualitativos tanto por jurisdicción como en una síntesis coral
tipada, sin crear ganador global ni pooling N→1.

## Posición respecto de V7

V7 demostró que Luke ofrece una celda mensual de producto físico con volumen y
precio. V8 convierte esa posibilidad en un protocolo plurianual ejecutable,
antes de abrir el histórico. La posición mejora metodológicamente, pero no hay
aún resultado predictivo nuevo.

El soporte congelado contiene 79 meses de serie corriente, desde 2020-01 hasta
2026-07. El año 2020 entrena la memoria estacional en sombra; desde 2021 M1 y M2
se activan sin reiniciar estados. Cada target conserva su propio posterior y
sus propios pesos. Julio de 2026 permanece en cuarentena de score porque fue
abierto en V7; agosto de 2026 queda como primer target prospectivo pendiente.

## Invariantes vigentes

1. Cada mes predice sólo el siguiente mes calendario.
2. Posterior, pesos y `Z_post` no se reinician en cambios de año.
3. Volumen y precio son targets distintos y no comparten likelihood ni pesos.
4. Serie corriente retrospectiva no equivale a vintages históricos de primera
   publicación.
5. Luke no se pooliza con Argentina, Eurostat, RMK, AEAT, Puertos o TED.
6. Faltantes, banderas no interpretadas, pérdidas y `NOT_ESTIMABLE` se
   preservan y detienen la autoridad correspondiente.
7. Año y fase calendario son diagnósticos; no hay ganador global.
8. Ningún raw actualiza directamente un prior: outcome, adjudicación y
   `Z_post` median toda actualización autorizada.

## Gates activos

- No adquirir historia Luke hasta que preregistro, addendum, hashes, auditor,
  commit y push público estén verificados.
- Un solo POST de 158 celdas como máximo; ningún GET de metadatos adicional.
- Un fallo del POST detiene la campaña y exige una nueva enmienda antes de
  cualquier segundo acceso.
- Una forma de cubo inesperada, un faltante o una bandera no interpretada no se
  corrige post hoc para rescatar el experimento.

## Obligación posterior vinculante: Argentina, Eurostat y expansión coral

Al cerrar Luke se realizará un inventario de bytes, contratos, outcomes y
autoridades ya existentes de Argentina y Eurostat. IPI/UCII, STS, Prodcom y
cualquier otra línea confirmada conservarán granularidad, calendario, vintage,
unidad y función económica propias. Comercio exterior, producción, precio,
actividad portuaria, licitación y clearing no se presentarán como equivalentes.

La integración coral se construirá como composición de evidencias locales:
cartografía de jurisdicciones, comparaciones homologables, divergencias,
complementariedades y abstenciones. Podrá producir más cobertura, triangulación
y poder diagnóstico; no una supermuestra ficticia ni una autoridad global.

Después del inventario se buscarán fuentes públicas adicionales priorizando
producto físico explícito, producción industrial estricta, cantidad y precio,
frecuencia mensual o superior, revisiones documentadas y acceso sin cuenta.
Gas, electricidad y precios regulados o administrados continúan excluidos;
madera permanece incluida.

## Siguiente acción crítica

Cerrar custodia pública V8. Después ejecutar el único POST Luke, supervisar la
cadena hasta estado terminal, auditarla y explicar resultados locales. Recién
entonces abrir el bloque Argentina/Eurostat y la búsqueda de fuentes nuevas.

