# Auditoría de fuentes industriales v2: España y Europa

Fecha de cierre: 2026-08-09.

## Resultado sustantivo

BMA queda mejor posicionado. La madera se conserva como jurisdicción industrial
de materiales, aunque sea biológica. Además, España sí ofrece una vía
estrictamente no biológica, no energética y sin precio regulado: las
estadísticas de comercio físico de bienes de la Agencia Estatal de
Administración Tributaria (AEAT).

La AEAT habilita cantidades y valores unitarios comerciales para acero, cobre,
aluminio, maquinaria, químicos y otros bienes. ScrapAd es todavía más próximo
al mercado B2B de metales que interesa a BIND, porque contiene lotes,
composición, cantidad, negociación, logística y transacciones; su precio final
y outcome histórico requieren convenio de datos. Ningún hallazgo es todavía
evidencia de performance de BMA.

## Gate y semántica

La fuente debe aportar bienes físicos industriales, observaciones repetidas,
cantidad, fecha, producto o lote, outcome procesable, posibilidad de freeze
pre-outcome y derechos de reutilización. Para el objetivo no biológico se
excluyen alimentos, biomasa y energía con precios regulados o administrados.

No se mezclan tres targets:

1. `TRANSACTION_PRICE`: precio final de compraventa o adjudicación;
2. `STATISTICAL_UNIT_VALUE`: valor declarado dividido por masa o unidades;
3. `REFERENCE_PRICE`: cotización externa de referencia.

AEAT proporciona el segundo; ScrapAd podría proporcionar el primero bajo
acuerdo. LME proporciona principalmente el tercero y no sustituye outcomes
físicos B2B.

## España: AEAT

La AEAT publica ficheros mensuales de máxima desagregación y resúmenes por
Nomenclatura Combinada (NC), país y flujo. El diseño detallado incluye fecha de
admisión, posición estadística, país, provincia, masa, unidades, valor
estadístico, valor factura, transporte, naturaleza de la transacción y
condiciones de entrega.

Se descargaron y verificaron tres archivos, no incorporados al repositorio:

- `cg25en74.zip`, enero de 2025, capítulos 64--74, SHA-256
  `d1e131cdc941e0d84b0bb5aef26793481ef946028c36ad04257e9babc545b60a`;
- `be25en79.zip`, resumen enero de 2025, SHA-256
  `aa9a0247ec5848f988d7475714997740d67bc18b3988725ca1e0a79e6e23e42d`;
- `be19en79.zip`, resumen definitivo enero de 2019, SHA-256
  `6c585af81afbf2409be68e38b92a60ba61ed9249f0a5253bc3683b75a59ae70`.

El fichero detallado contiene 690.929 registros: 32.726 de hierro/acero
(capítulo 72), 165.203 de manufacturas de hierro/acero (73) y 18.682 de cobre
(74), todos con masa y valor positivos.

La sonda `NC 72083900` representa bobinas de acero sin alear, laminadas en
caliente, ancho mínimo 600 mm y espesor inferior a 3 mm. En enero de 2025,
incluyendo extensiones TARIC:

- 863 filas: 472 importaciones y 391 exportaciones;
- importación: 92.843.933 kg y 56.378.482,41 EUR; 0,607239 EUR/kg;
- exportación: 22.633.863 kg y 13.200.110,09 EUR; 0,583202 EUR/kg;
- detalle y resumen reconcilian exactamente el valor en céntimos y la masa al
  redondeo de kg.

En enero de 2019, el mismo NC8 presenta 49.040.823 kg importados a 0,558750
EUR/kg y 20.355.796 kg exportados a 0,514382 EUR/kg. Esto verifica continuidad
en dos extremos, no todos los meses intermedios.

Estado: `TECHNICAL_SOURCE_PASS_OPEN_REUSE_MODEL_NOT_EXECUTED`. La AEAT permite
reutilización comercial y no comercial con cita, metadatos preservados, sin
desnaturalización ni respaldo institucional implícito.

Límites: el valor unitario no es puja, spot ni precio de empresa; no hay
identidades empresariales; 2019--2024 figuran como definitivos, la finalidad de
2025 no se adjudicó aquí y 2026 está incompleto y sujeto a revisión. Antes de
modelar se deben congelar NC8, flujo, socio/nodo, frecuencia, confidencialidad,
outliers, política de revisiones, entrenamiento y target futuro.

## España: ScrapAd

ScrapAd es una plataforma española de metales físicos. Los anuncios públicos
aportan material, composición y cantidad; una sonda observada ofrece 40 t de
cobre con pureza mínima del 99 %. La plataforma describe negociación, pago,
documentación y logística. La SETT confirma que su recomendador usa datos reales
de operaciones y que las transacciones se verifican.

Estado: `STRICT_PHYSICAL_MARKET_DATA_AGREEMENT_REQUIRED`. Es el mejor candidato
español para un piloto BIND con precio transaccional. La web pública no expone
precio final, cierre/no-cierre ni profundidad histórica; sin convenio no existe
corpus ejecutable.

## Madera, chatarra pública y energía

- Xunta: la madera queda incluida. Sus capas cubren 2019--2026, con volumen,
  especie y tasación; `IMPORTE_TAXACION` no es precio ganador. Estado:
  `TECHNICAL_NEAR_PASS_NO_TRANSACTION_PRICE`.
- BOE/PLACSP: existen subastas reales de chatarra con peso, salida y a veces
  adjudicación, pero están dispersas y son heterogéneas. Estado:
  `REAL_AWARD_CASE_SERIES_FAILS_NORMALIZED_DENSITY_GATE`.
- MIBGAS y OMIE: `EXCLUDED_REGULATED_OR_ADMINISTERED_PRICE_SCOPE`. Gas y
  electricidad no se usarán como sustituto industrial.

## Europa

España ya ofrece una ruta útil, así que Europa deja de ser necesaria para pasar
el gate de disponibilidad. Se conservan los hallazgos:

- Rheinland-Pfalz: madera valiosa; 1.191 lotes, 1.186 adjudicados y cinco sin
  oferta. Pasa técnicamente, pero la reutilización exige permiso y sólo 2026 se
  verificó a nivel de lote.
- Metalshub: mercado físico europeo de metales con datos privados; requiere
  acuerdo.
- LME: referencia industrial licenciada; no aporta por sí sola outcomes B2B
  físicos.

## Consecuencia para BMA y BIND

BMA ya no depende de que la madera represente toda la extensión industrial. Hay
una ruta pública española para un conector y replay de cantidad y valor unitario
de acero, y una ruta comercial más fuerte para BIND mediante acceso gobernado a
ScrapAd. La portabilidad mejora a nivel de fuente, no de validez predictiva.

El siguiente gate es preregistrar una jurisdicción AEAT futura y estricta,
implementar el conector reproducible y auditar completitud/revisiones. En BIND
se puede proponer a ScrapAd un piloto, sin afirmar acceso actual ni validación
en metales.

Fuentes: [AEAT](https://sede.agenciatributaria.gob.es/Sede/estadisticas/estadisticas-comercio-exterior.html),
[formato detallado](https://sede.agenciatributaria.gob.es/static_files/AEAT/Aduanas/Contenidos_Privados/Estadisticas_Comercio_Exterior/comercio_exterior/datos_mensuales_maxima_desagregacion/diseno226.pdf),
[reutilización AEAT](https://sede.agenciatributaria.gob.es/Sede/gobierno-abierto/reutilizacion-informacion/condiciones-reutilizacion.html),
[SETT sobre ScrapAd](https://sett.gob.es/la-sett-invierte-11-millones-de-euros-en-una-plataforma-tecnologica-digital-que-contribuye-a-la-economia-circular-gracias-al-reciclaje-de-metales/),
[ScrapAd](https://scrapad.com/en/buy/),
[Xunta](https://datos.gob.es/es/catalogo/a12002994-gestion-de-cortas-publicas),
[RLP](https://www.wald.rlp.de/nutzen/holz/wertholzsubmission) y
[LME](https://www.lme.com/Market-data/Accessing-market-data/Historical-data).
