# Candidatos industriales diarios desagregados — v2

Fecha: 2026-08-09  
Estado: `CANDIDATES_IDENTIFIED_ACCESS_NOT_YET_CONTRACTED`

## Orden de preferencia por fidelidad informativa

### 1. Eventos internos de marketplace o Venture Client español

ScrapAd, Trazko, gestores de chatarra, acerías, distribuidores y compradores
industriales son la vía de mayor valor si entregan cada pedido, oferta o
transacción con timestamp nativo, calidad, cantidad, precio, localización,
condición de entrega y estado. No se ha verificado acceso público a ese corpus.

Gate: `IDEAL_RAW_EVENT_SOURCE_BUT_ACCESS_UNAVAILABLE`.

### 2. Fastmarkets — HRC y chatarra europeos

El índice diario de bobina laminada en caliente (HRC) doméstica ex-works Northern
Europe tiene una especificación física explícita: grado S235JR, anchura
1.200–1.300 mm, espesor 3 mm, mínimo 50 toneladas, Alemania/Países
Bajos/Bélgica, publicación diaria. La metodología pondera por tonelaje y puede
usar transacciones, ofertas, bids e indicaciones normalizadas.

Desde julio de 2025 varias series europeas de chatarra pasaron a frecuencia
diaria e índice único, entre ellas HMS 1&2 FOB Rotterdam y referencias de
exportación/importación UK–Turquía, con mínimo 5.000 toneladas.

Ventajas: producto físico bien definido, frecuencia y hora de publicación,
mercado europeo, términos comerciales y volumen mínimo explícitos.

Límite: el índice es una transformación de inputs confidenciales; no entrega por
defecto los eventos subyacentes. En baja liquidez puede incorporar información
no transaccional o carry-over conforme a metodología.

Gate: `HIGH_VALUE_DAILY_PHYSICAL_INDEX_LICENSE_REQUIRED_NOT_RAW`.

### 3. Argus Scrap Markets

Argus ofrece precios de chatarra ferrosa y no ferrosa por grado, región y término
de entrega mediante informe diario y ficheros descargables. Los materiales de
muestra incluyen referencias europeas y del norte de España, además de series
FOB Rotterdam, CFR Turquía y delivered mill.

Ventajas: proximidad directa al mercado físico de chatarra, diversidad de
calidades y geografías, timestamps de evaluación y data files.

Límites: acceso licenciado; la cadencia exacta de cada código español debe
verificarse contractualmente; son evaluaciones/índices, no raws individuales.

Gate: `HIGH_VALUE_DAILY_OR_PERIODIC_PHYSICAL_ASSESSMENT_LICENSE_REQUIRED`.

### 4. London Metal Exchange

El Next Day XML Feed publica diariamente precios oficiales/settlement, volumen
y movimientos físicos de almacén por commodity, grado, estado y localización.

Ventajas: disponibilidad next-day definida, series conjuntas de mercado y stock
físico, contrato técnico estable.

Límites: precios y volúmenes de exchange; licencia; no equivalencia con una
compraventa física individual de producción.

Gate: `DAILY_EXCHANGE_AND_PHYSICAL_STOCK_JURISDICTION`.

## Fuentes españolas descartadas para el gate diario

- FEAF: medias mensuales.
- Puertos del Estado: difusión y agregación mensuales.
- INE/data.gob.es: índices industriales mensuales o datos anuales.
- AEAT: evento fechado por día, pero disponibilidad pública mensual.

No se incluyen gas, electricidad ni precios administrados.

## Decisión

La búsqueda no termina en este inventario. El siguiente trabajo es verificar,
para cada candidato, historial disponible, licencia de uso/modelado, API o
formato, frecuencia efectiva, revisiones, missingness, profundidad transversal
y si el precio proviene de operaciones, ofertas o juicio editorial. Solo después
se congela una nueva jurisdicción BMA.

## Fuentes

- Fastmarkets HRC Northern Europe:
  `https://www.fastmarkets.com/insights/pricing-notice-proposal-to-create-a-daily-hrc-index-for-northern-europe/`
- Fastmarkets scrap daily 2025:
  `https://www.fastmarkets.com/insights/increased-publication-frequency-of-some-uk-europe-turkey-steel-scrap-prices-change-to-indices/`
- Fastmarkets ferrous scrap methodology:
  `https://www.fastmarkets.com/methodology/metals/ferrous-scrap-indices/`
- Argus Scrap Markets:
  `https://www.argusmedia.com/en/solutions/products/argus-scrap-markets`
- LME Next Day XML Feed:
  `https://www.lme.com/-/media/files/data/accessing-market-data/reference-and-transparency-data/lmelive-ptt-xml-feed-developer-guide-1-20.pdf`
