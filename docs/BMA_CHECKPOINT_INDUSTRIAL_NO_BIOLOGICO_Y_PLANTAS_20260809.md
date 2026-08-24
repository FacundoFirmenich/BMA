# BMA — checkpoint industrial no biológico y plantas

Fecha: 2026-08-09.

## Posición frente al checkpoint anterior

BMA queda mejor posicionado en dos dimensiones independientes. Primero, la
señal de Mercabarna Flor ya no está mezclada por familias: plantas vivas tienen
una señal favorable descriptiva en participación, mientras cantidad apunta en
la misma dirección pero sigue `NOT_ESTIMABLE` por soporte insuficiente.
Segundo, la extensión industrial ya no depende sólo de la madera: existe una
fuente española abierta de bienes industriales no biológicos y un candidato
transaccional B2B de metales para BIND.

## Anotación 1 — taxonomía de Flor y plantas

Se congeló desde entrenamiento la separación `FLOR_CORTADA`, `PLANTA_VIVA`,
`ARBOLES_Y_VERDES`, `COMPLEMENTOS` y `UNRESOLVED`. No se usaron targets para
clasificar productos ambiguos.

En régimen ordinario, `PLANTA_VIVA` obtuvo:

- participación: n=192, 16 positivos, Brier BMA 0,142360 frente a 0,173216 del
  baseline congelado; ganancia relativa 17,813 %, estado
  `FAVOURABLE_DESCRIPTIVE_ONLY`;
- cantidad: n=16, error BMA 1,646679 frente a 1,897301 de persistencia y
  1,881594 del baseline fuerte; estado `NOT_ESTIMABLE_INSUFFICIENT_SUPPORT`
  porque el gate predeclarado exige n>=30.

No se promueve precio, sábado ni fin de mes. No existe ganador global ni
validación prospectiva.

## Industria estricta sin excluir madera

La madera permanece incluida. Rheinland-Pfalz pasa el gate técnico de lote,
precio adjudicado, volumen y no-oferta, pero su reutilización pública está
bloqueada y sólo 2026 fue verificado a nivel de lote. Xunta aporta volumen,
especie y tasación, no precio ganador.

La nueva vía estrictamente no biológica es AEAT Comercio Exterior. En una sonda
real de enero de 2025 se inspeccionaron 690.929 registros de los capítulos
64--74. Hubo 32.726 registros de hierro/acero, 165.203 de manufacturas de
hierro/acero y 18.682 de cobre, todos con masa y valor positivos.

Para `NC 72083900`, bobina de acero laminada en caliente de espesor inferior a
3 mm, el detalle de enero de 2025 contiene 863 filas y reconcilia con el resumen
oficial:

- importación: 92.843.933 kg, 56.378.482,41 EUR y 0,607239 EUR/kg;
- exportación: 22.633.863 kg, 13.200.110,09 EUR y 0,583202 EUR/kg.

La continuidad se sondó también en enero de 2019. La AEAT autoriza
reutilización comercial y no comercial con condiciones de cita y preservación.
El target es `STATISTICAL_UNIT_VALUE`, nunca precio adjudicado o spot. La fuente
pasa; el modelo no fue ejecutado y 2026 no se considera completo.

ScrapAd es el candidato español de mayor valor para BIND: metales físicos,
calidad, lotes, cantidades, negociación, pago, documentación y logística. La
SETT confirma uso de operaciones reales. Sin embargo, precio final y outcomes
históricos no son públicos; se requiere convenio de datos. Gas y electricidad
quedan expresamente fuera.

## Significado para BIND

La candidatura puede defender dos carriles sin overclaim:

1. demostrador abierto sobre cantidades y valores unitarios de acero AEAT,
   después de preregistración y conector;
2. piloto de alto valor con ScrapAd, condicionado a acceso gobernado a datos
   transaccionales.

Esto fortalece la portabilidad y el encaje en demanda, procurement y supply
chain. No demuestra todavía precisión en metales, ahorro, pricing autónomo ni
automatización de compras.

## Validación y artefactos

- 31 pruebas: PASS;
- Ruff: PASS;
- registros de evidencia: PASS;
- recibo AEAT con hashes y reconciliación:
  `evidence/receipts/aeat-steel-source-audit-20260809.json`;
- auditoría vigente: `docs/INDUSTRIAL_DATA_SOURCE_AUDIT_ES_V2.md`;
- datos brutos: no publicados en el repositorio.

## Próximo gate decisivo

Congelar antes de ejecutar: NC8, importación/exportación, socios o nodos,
frecuencia, confidencialidad, outliers, política de revisiones, ventana de
entrenamiento, target futuro y comparadores. Sólo después se implementará el
conector y se abrirá el replay AEAT. En paralelo, preparar un contrato de datos
y piloto para ScrapAd sin presentar acceso ni performance inexistentes.
