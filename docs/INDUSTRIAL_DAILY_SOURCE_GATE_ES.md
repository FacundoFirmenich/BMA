# Gate de fuente industrial diaria — España y Europa

Fecha de auditoría: 2026-08-09  
Estado: `NO_PUBLIC_DAILY_RAW_TRANSACTION_SOURCE_VERIFIED`

## Criterio

La fuente buscada debe contener producción o intercambio industrial no
biológico, precio y cantidad no regulados, resolución temporal mínima nativa y
disponibilidad compatible con el horizonte de predicción. Una media diaria o
mensual no equivale a eventos raw. Precio de referencia, cotización bursátil,
listing y transacción se mantienen como jurisdicciones distintas.

## España

### AEAT máxima desagregación

- Cada línea conserva fecha diaria de admisión y marcas industriales detalladas.
- El transporte público observado es un archivo mensual.
- Apto para replay diario retrospectivo por `event_time`.
- No apto para claim operacional day-ahead por `availability_time`.
- La línea no debe denominarse necesariamente transacción comercial ni su valor
  unitario precio transaccional.

### FEAF materias primas

La Federación Española de Asociaciones de Fundidores publica precios medios de
compra de chatarra de acero, lingotes y ferroaleaciones, pero la frecuencia
declarada es mensual. Es industrial y de mercado, pero falla el gate de
resolución y conserva promedios, no eventos.

### Marketplaces españoles

ScrapAd y Trazko son candidatos razonables a una colaboración de datos porque
operan sobre chatarra, retales y excedentes metálicos. No se verificó una
descarga pública con operaciones cerradas, timestamps, cantidad, calidad y
precio. Listings visibles o precios orientativos no deben usarse como outcomes
transaccionales. La vía correcta es un acuerdo de piloto o acceso contractual a
eventos internos, con derechos y semántica auditados.

Resultado España: no se verificó en esta búsqueda acotada una fuente pública,
diaria, raw y transaccional que cumpla simultáneamente todos los gates.

## Europa

### London Metal Exchange (LME)

El feed Next Day de LME declara disponibilidad diaria desde las 00:10 GMT e
incluye precios oficiales/settlement, volumen negociado y movimientos de stock
de almacenes aprobados por commodity, calidad, estado y localización. La
documentación también contempla acero billet.

Limitaciones:

- acceso y redistribución sujetos a licencia;
- el acuerdo publicado tarifa el feed Next Day;
- precio oficial/settlement y futuros no equivalen a precio de una compraventa
  física industrial individual;
- el stock de almacén sí es una magnitud física diaria, pero constituye otra
  jurisdicción de modelado.

LME pasa frecuencia y disponibilidad, y es candidato a control industrial
diario multivariable. No sustituye sin más un mercado físico de producción.

### S&P Global Platts Steel Markets Daily

Ofrece evaluaciones diarias y semanales para acero, chatarra, mineral de hierro
y carbón metalúrgico, con distribución por API/feed. Son evaluaciones de precio
licenciadas y comentarios de mercado; no se verificó un corpus raw de
transacciones individuales. Puede ser benchmark contextual, no outcome
transaccional por defecto.

Resultado Europa: existen fuentes industriales diarias operables bajo licencia,
pero no se verificó una fuente pública abierta que entregue eventos físicos raw
equivalentes al contrato ideal.

## Decisión para BMA/BIND

1. AEAT se limita a investigación retrospectiva diaria y multirresolución.
2. LME puede constituir una jurisdicción diaria separada de precios, volumen y
   stocks, nunca presentada como producción física española.
3. Para un piloto BIND verdaderamente operacional se prioriza un Venture Client
   o marketplace que entregue eventos de pedido/oferta/transacción con timestamp,
   producto/calidad, cantidad, precio, estado y disponibilidad real.
4. Ninguna media publicada se convierte en raw mediante interpolación o
   desagregación sintética.

## Fuentes primarias

- AEAT, diseño de registro de 226 bytes:
  `https://sede.agenciatributaria.gob.es/static_files/AEAT/Aduanas/Contenidos_Privados/Estadisticas_Comercio_Exterior/comercio_exterior/datos_mensuales_maxima_desagregacion/diseno226.pdf`
- FEAF, materias primas: `https://feaf.es/materias-primas/`
- LME, Next Day XML Feed v1.20:
  `https://www.lme.com/-/media/files/data/accessing-market-data/reference-and-transparency-data/lmelive-ptt-xml-feed-developer-guide-1-20.pdf`
- LME, Market Data Services Agreement:
  `https://datalicensing.lme.com/Portals/0/LME%20Market%20Data%20Services%20Agreement.pdf`
- S&P Global, Platts Steel Markets Daily:
  `https://www.spglobal.com/energy/es/products-solutions/steel-metals/platts-steel-markets-daily`
