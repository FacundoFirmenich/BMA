# Mercados físicos industriales diarios y desagregados — v3

Fecha de verificación: 2026-08-09  
Estado: `RAW_EVENT_CANDIDATES_FOUND_ACCESS_AND_COVERAGE_NOT_YET_PROVEN`

## Decisión

En España no se verificó una fuente pública que combine simultáneamente evento industrial físico, timestamp diario nativo, producto/lote desagregado, cantidad, precio final, historial completo y acceso masivo reutilizable. Sí existen plataformas con el dato operativo internamente; requieren acuerdo.

En Europa aparecen dos candidatos superiores a los índices evaluados: TBAuctions/ATLAS y EquipmentWatch. Ambos pueden acercarse al dato raw de evento, pero ninguno está listo para ejecutar una campaña hasta demostrar cobertura, licencia, cronología y completitud mediante una muestra contractual.

Gas, electricidad y cualquier precio regulado o administrado quedan fuera. La madera continúa incluida, tanto como producto biológico de interés como a través de maquinaria y activos de transformación; la prioridad adicional es producción industrial estrictamente no biológica.

## España

### 1. Subalia B2B — mejor candidato español de datos internos

Subalia gestiona subastas privadas entre empresas para excedentes, devoluciones, materiales de desecho y productos descatalogados. El vendedor define lotes y reglas y observa pujas en tiempo real; la comisión se calcula sobre el valor final vendido.

Potencial científico: lote físico, inventario, puja, valor final y condición vendido/no vendido. Puede cubrir fabricantes, mayoristas y distribuidores, incluida producción estrictamente industrial.

Límite decisivo: la plataforma es privada y el portal público no ofrece un archivo histórico masivo de resultados. BMA necesitaría un acuerdo de datos que preserve timestamps, revisiones, unidades, moneda, impuestos/comisiones y estados de adjudicación.

Gate: `SPAIN_RAW_B2B_EVENT_IDEAL_PARTNERSHIP_REQUIRED`.

Fuente oficial: https://www.subalia.com/es

### 2. Gobid España — activos y maquinaria industrial reales

Gobid ejecuta subastas de maquinaria, equipamiento industrial, vehículos, unidades productivas y liquidaciones privadas o concursales. Las pujas ocurren en tiempo real y la adjudicación depende del mejor postor y, cuando corresponde, de la reserva.

Potencial científico: secuencia de pujas, precio final de lote, cierre, adjudicación, categoría y localización física.

Límites: los precios de subastas finalizadas no forman un histórico público descargable; Gobid indica que deben solicitarse por correo para lotes concretos. Tampoco se verificó una API masiva ni una cadencia diaria suficientemente densa para todas las categorías.

Gate: `SPAIN_REAL_INDUSTRIAL_AUCTION_OUTCOME_ACCESS_BY_AGREEMENT`.

Fuente oficial: https://www.gobid.es/es/como-funciona

### 3. Bid Industry — marketplace industrial europeo accesible desde España

Bid Industry publica maquinaria usada, cierres de fábricas y equipos de metal, madera, logística, alimentación, laboratorio, farmacia y semiconductores. Declara transacciones directas, subastas y negociación privada.

Potencial: activos industriales estrictos, lotes y cierres reales; la categoría de trabajo de la madera conserva esa jurisdicción sin confundirla con materias primas forestales.

Límite: no se verificó API histórica, resultado final masivo ni completitud diaria. Parte de las subastas se deriva a Troostwijk/TBAuctions, por lo que puede funcionar mejor como canal de descubrimiento que como fuente canónica independiente.

Gate: `EU_INDUSTRIAL_MARKETPLACE_DISCOVERY_NO_VERIFIED_BULK_OUTCOME_FEED`.

Fuente oficial: https://www.bidindustry.com/es/

## Europa

### 1. TBAuctions / ATLAS — candidato principal

TBAuctions opera subastas en más de 20 países europeos; Troostwijk se orienta a B2B. ATLAS ofrece APIs para inventario y datos de órdenes post-subasta. La documentación define las órdenes como lotes vendidos y pagados, con información de comprador y vendedor.

Ventaja: eventos físicos industriales, categorías anidadas, atributos de artículo, localización, vendedor, comprador y orden post-subasta. Es más próximo a raw transaccional que un índice de precios.

Límites observados:

- ATLAS no expone directamente la puja en vivo; esa fase ocurre en plataformas externas.
- Se necesita cuenta de desarrollador obtenida mediante ventas/API Support.
- Las consultas están acotadas por empresa/comprador; la documentación pública no demuestra acceso a todo el mercado ni a un histórico completo.
- Debe verificarse que importe final, moneda, cantidad, impuestos, comisión, cancelaciones y timestamp de cierre/adjudicación sean recuperables con semántica estable.

Gate: `EU_TOP_RAW_POST_AUCTION_CANDIDATE_DEVELOPER_ACCOUNT_AND_SCOPE_PROOF_REQUIRED`.

Fuentes oficiales:

- https://apidocs.tbauctions.com/
- https://apidocs.tbauctions.com/getting-started

### 2. EquipmentWatch Market Data API — mejor archivo transaccional documentado

EquipmentWatch declara acceso API a observaciones raw de reventa y subasta. El ejemplo oficial incluye modelo, fabricante, categoría, tipo de venta, año, condición, fecha, marketplace, precio y localización. Su producto Market Activity declara más de veinte años de transacciones de subasta y precio final.

Ventaja: contrato de datos cercano al requerido por BMA para maquinaria pesada, elevación y agricultura; timestamp y precio final explícitos; profundidad histórica.

Límite: la evidencia pública observada muestra con claridad cobertura norteamericana, no demuestra aún cobertura europea suficiente ni completitud diaria por jurisdicción. Requiere API key y validación contractual de derechos de modelado y redistribución de derivados.

Gate: `RAW_EQUIPMENT_TRANSACTION_API_EUROPE_COVERAGE_UNPROVEN`.

Fuentes oficiales:

- https://equipmentwatch.com/api/market-data/
- https://equipmentwatch.com/market-activity-data/

## Fuentes físicas diarias secundarias, no raw

Fastmarkets, Argus, Platts y LME siguen siendo útiles como comparadores externos o covariables, no como sustitutos de eventos transaccionales:

- Fastmarkets: índices diarios de acero/chatarra que pueden mezclar transacciones, ofertas, bids e indicaciones normalizadas.
- Argus: evaluaciones de precios físicos por grado, región y término de entrega.
- Platts: evaluaciones spot diarias para polímeros y otros materiales.
- LME: precios/volumen de exchange y stock físico de almacén.

Gate conjunto: `LICENSED_DAILY_PHYSICAL_REFERENCE_NOT_RAW_EVENT`.

No deben mezclarse con TBAuctions o EquipmentWatch como si compartieran contrato de evidencia. Pueden predecir o contextualizar, pero no adjudicar una afirmación sobre transacciones individuales.

## Fuentes españolas descartadas para el gate diario

- AEAT: el evento lleva fecha, pero la publicación pública consolidada es mensual.
- FEAF: medias de mercado mensuales.
- Puertos del Estado: agregación/difusión mensual.
- INE y data.gob.es: índices industriales mensuales o anuales.

## Gate de adquisición mínimo

Antes de descargar o contratar nada debe exigirse una muestra pequeña y remota que permita comprobar:

1. una fila por evento/lote y timestamp nativo;
2. resultado final vendido/no vendido/cancelado;
3. precio final, moneda, impuestos y comisiones separables;
4. cantidad, unidad, categoría y atributos físicos;
5. localización y términos de entrega/retirada;
6. revisiones, duplicados y late arrivals;
7. cobertura diaria real y profundidad histórica;
8. licencia para entrenamiento, auditoría y persistencia de derivados;
9. ausencia de precios regulados o administrados;
10. exportación mínima sin persistir localmente archivos crudos innecesarios.

## Consecuencia para BIND

La vía española más defendible es un Venture Client o partnership de datos con Subalia/Gobid. La vía europea técnicamente más fuerte es TBAuctions; EquipmentWatch es la alternativa con contrato raw mejor documentado si confirma Europa. La candidatura no debe afirmar que BMA ya dispone de esos datos: debe presentar el conector y el protocolo de custodia como capacidad lista para un piloto condicionado al acceso.
