# Registro de misión KCH — Bayesian Markets V3

Estado: `ACTIVE_AFTER_RMK_CAUSAL_CLOSURE_AND_CROSS_FAMILY_CORAL_V1`

## Objetivo rector

Preservar BayME como modelo general y BPM, BUM y HBP como familias canónicas; ejecutar predicción causal estrictamente local; y construir una coralidad tipada que aumente cobertura de productos, territorios y mecanismos sin crear un posterior universal ni un ganador global.

## Posición alcanzada

### RMK Estonia

La campaña retrospectiva elegible queda cerrada. Catorce eventos tienen auditor PASS y suman 646 controles. El posterior final contiene 388 celdas locales y 1.008 observaciones; 30 celdas tienen soporte M1 y ninguna M2. En las 14 comparaciones M1 observadas, precio favorece M1 5 veces y M0 9; volumen queda 7 a 7. Dos eventos retrospectivos son `NOT_ESTIMABLE` y el evento 26-08-2026 permanece futuro. No existe promoción.

### Argentina

Crédito, M3 e IPC conservan su adjudicación local y sus freezes futuros con brecha de custodia. UCII conserva el hallazgo 59,1% y la invalidez del posterior que doble contó evidencia; ese freeze no gobierna futuro. IPI permanece separado y sin payload recuperado. La fuente oficial INDEC permite comenzar una cadena nueva con informes y series oficiales, pero nunca reconstruir retrospectivamente un freeze perdido desde una publicación posterior.

### Eurostat

RC15 conserva 27 países, 351 aristas y 69.498 contrastes históricos; julio de 2026 sigue `NOT_ESTIMABLE_INCOMPLETE_PANEL`. STS industrial por país y NACE se incorpora como outcome prospectivo con captura obligatoria de primera publicación: la API oficial mantiene la última versión y no ofrece archivo de vintages. Prodcom se incorpora sólo como soporte anual de producto, cantidad y valor.

### Observadores

Puertos del Estado puede aportar flujo físico mensual; TED, recuentos de eventos CPV-NUTS. Ninguno tiene autoridad de precio de mercado ni actualiza por sí solo un posterior de outcome. UN Comtrade permanece en cuarentena y Zoll-Auktion en espera.

## Invariantes

1. Cada mes predice sólo el siguiente; cada evento RMK sólo el siguiente evento comparable.
2. Posterior y Z_post específicos acumulan sin reset.
3. N períodos no se condensan en un target.
4. País, producto, destino, unidad, vintage y fuente definen jurisdicciones separadas.
5. Revisión oficial y primera publicación son bytes distintos.
6. `NOT_ESTIMABLE`, abstención, pérdida, cuarentena y brecha de custodia son evidencia.
7. No hay ganador global ni promoción automática.

## Siguiente acción crítica

Ejecutar probes mínimos de custodia —no fitting— para una nueva vintage INDEC IPI/UCII, una celda Eurostat STS país-NACE y una rebanada Prodcom producto-país. Después congelar esquemas, hashes, fechas de publicación, soporte y priors antes de iniciar cadenas prospectivas. No se autoriza descarga masiva, cuenta, contacto a terceros ni VPS.
