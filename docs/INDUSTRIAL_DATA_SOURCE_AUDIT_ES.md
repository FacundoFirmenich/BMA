> SUPERSEDED on 2026-08-09 by
> `INDUSTRIAL_DATA_SOURCE_AUDIT_ES_V2.md`. This historical checkpoint is
> retained and must not be read as the current source decision.

# Auditoría de fuentes industriales: España y Europa

Fecha de cierre: 2026-08-09.

## Posición del proyecto

BMA queda mejor posicionado en amplitud de mercado: ya existe un candidato
industrial europeo con precio adjudicado, volumen físico, lote, calidad y
resultado de no-oferta. No queda todavía habilitado un experimento histórico
ni la publicación del corpus, porque la barrera real es doble: derechos de
reutilización y profundidad temporal a nivel de lote.

## Gate aplicado

La fuente debía contener un mercado físico industrial o de materiales,
observaciones repetidas, precio final transado o adjudicado, cantidad física,
fecha, nodo o lote, semántica de adjudicación/no-oferta, acceso procesable y
posibilidad de congelar una predicción antes del outcome. Para un artefacto
público se exigió además licencia compatible.

## España

### Madera pública de Galicia

El servicio oficial de la Xunta es una fuente seria: en la capa reciente se
observaron 1.098 registros, 1.088 importes de tasación, 1.082 volúmenes y 1.090
especies. El conjunto cubre fases administrativas y años 2019--2026 entre sus
capas. Sin embargo, `IMPORTE_TAXACION` es tasación, no precio ganador. La fuente
sirve para oferta, volumen, especie y progresión del lote, pero no para evaluar
predicción de precio de cierre.

### Navarra, contratación pública y energía

- Navarra publica 200 expedientes de trabajos forestales, pero la distribución
  inspeccionada carece de precio y volumen.
- La Plataforma de Contratación del Sector Público contiene adjudicaciones,
  pero no una unidad física homogénea y repetida por producto/calidad.
- MIBGAS y OMIE sí tienen precio y volumen, aunque pertenecen a mercados
  energéticos regulados; son controles útiles, no el mercado industrial de
  inventario material buscado.

Resultado España: ningún candidato no energético pasa el gate completo.

## Europa

### Landesforsten Rheinland-Pfalz

El XLS oficial de la Wertholzsubmission Pfalz del 27-01-2026 fue descargado,
hasheado e inspeccionado sin modificarlo:

- SHA-256: `1cee4d73c1de00b3779697a52610569e3ec97f8061c85c8e2058a773d38a0b87`;
- 1.191 lotes únicos y 1.191 volúmenes;
- 1.186 precios máximos adjudicados y 5 lotes sin oferta;
- 1.845,32 fm ofertados, 1.842,95 fm adjudicados y 2,37 fm sin oferta;
- precio adjudicado ponderado: 977,897116 €/fm;
- valor adjudicado implícito: 1.802.215,49 €;
- rango de precio: 132--5.199 €/fm.

La reconciliación externa pasa: el informe oficial declara aproximadamente
2 fm sin oferta, máximo de 5.199 €/fm y 985 €/fm para el subconjunto de robles.
Los informes oficiales confirman recurrencia en 2024, 2025 y 2026, pero en esta
auditoría solo 2026 quedó verificado a nivel de lote.

Estado: `TECHNICAL_PASS_PUBLIC_REUSE_BLOCKED`. El aviso legal indica "todos
los derechos reservados" y prohíbe reproducción o uso sin consentimiento
expreso. El archivo no se incluye en GitHub ni se publican sus filas derivadas.

### Otros candidatos europeos

- LME: excelente estructura para metales —precio, volumen y stocks—, pero el
  histórico y los usos derivados/distribuidos están sujetos a compra o licencia.
- ONF Francia: no apareció una serie pública granular de transacciones por lote.
- RMK Estonia: publica oferta de volumen, pero la mayoría de ventas usa contratos
  de largo plazo y precios negociados sin serie pública de cierre.

## Consecuencia para BMA y BIND

La afirmación correcta ya no es "no hay datos industriales": hay un candidato
técnicamente válido en madera industrial de alto valor. Tampoco puede afirmarse
que BMA esté validada fuera de Mercabarna. Antes de modelar Rheinland-Pfalz se
requieren permiso expreso de reutilización y al menos dos campañas adicionales
a nivel de lote, preservando catálogos previos y outcomes separados.

Para BIND, esta evidencia fortalece la portabilidad de la arquitectura y ofrece
un piloto industrial defendible, pero no autoriza mostrar un benchmark de
performance, un dataset público ni una automatización de pujas.

Fuentes oficiales: [Xunta](https://datos.gob.es/es/catalogo/a12002994-gestion-de-cortas-publicas),
[Navarra](https://datos.gob.es/es/catalogo/a15002917-aprovechamiento-de-madera-trabajos-iniciados-y-finalizados1),
[RLP hub](https://www.wald.rlp.de/nutzen/holz/wertholzsubmission),
[RLP resultado 2026](https://www.wald.rlp.de/start-landesforsten-rheinland-pfalz/service/nachrichten-uebersicht/einzelnachricht/verkaufsbericht-wertholzsubmission-pfalz-27012026-digitale-gebotsabgabe),
[RLP aviso legal](https://www.wald.rlp.de/start-landesforsten-rheinland-pfalz/service/impressum),
[LME histórico](https://www.lme.com/Market-data/Accessing-market-data/Historical-data)
y [LME licencias](https://www.lme.com/Market-data/Market-data-licensing).
