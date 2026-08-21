# RMK Estonia: cierre del inventario y cola causal V3

Fecha: 2026-08-21

## Resultado final del checkpoint

El inventario previo a adquisición queda cerrado con 63 URLs únicas, todas con
HEAD 200, metadatos congelados y cero cuerpos históricos abiertos. La cola V3
contiene exactamente una fila por URL y ordena oferta antes de resultado.

Hay 15 fechas con oferta y resultado descubiertos: doce en 2025 y tres en 2026.
La pareja 30-06-2026 permanece excluida de evaluación ciega porque fue el probe
de esquema. Quedan 13 resultados fechados sin oferta para auditoría de
elegibilidad, nueve resultados trimestrales sin fecha exacta en cuarentena, seis
referencias de normalización y dos recursos fuera del replay.

## Comparación con los intentos anteriores

- V1 era inválida: 83 filas para 63 URLs y riesgo de doble apertura.
- V2 era inválida: deduplicó, pero truncó fechas a `2` por indexación escalar.
- V3 pasa: 63/63 unicidad, 0 conflictos de fecha o HEAD, 0 cuerpos abiertos,
  0 fechas mal formadas y 15 pares reales.

Los dos fallos están preservados con marcadores `INVALID_DO_NOT_EXECUTE`; no se
reescriben como éxitos.

## Significado científico

RMK sigue siendo el candidato BPM público más fuerte encontrado: el esquema
precio-cantidad-producto-destino existe y la web conserva continuidad suficiente
para una cadena prospectiva parcial. No obstante, no hay una campaña histórica
completa 2023-2026: 2023/2024 conservan principalmente resultados, no ofertas.

Por eso la próxima apertura será sólo un test de elegibilidad de outcomes 2023
y 2024, en orden, sin fitting. Un resultado entra como historia previa únicamente
si contiene producto, estándar, volumen, precio y localización comparables. Las
series trimestrales sin fecha no entran. La estacionalidad se activa sólo por
celda con dos fases anteriores; de lo contrario es
`NOT_ESTIMABLE_SEASONAL_SUPPORT`.

## Siguiente acción crítica

Abrir el primer resultado fechado de 2023 según cola V3, congelar su SHA-256 y
adjudicar esquema/soporte. Después continuar 2024 uno por uno. Antes del replay
2025 deberán quedar congelados priors, pesos, recovery, tarifas/distancias y
todos los invariantes de posterior, Z_post y Z-XPL.
