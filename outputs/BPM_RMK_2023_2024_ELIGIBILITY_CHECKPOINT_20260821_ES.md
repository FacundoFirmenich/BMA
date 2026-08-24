# BPM-RMK: cierre de elegibilidad histórica 2023-2024

## Resultado sustantivo

RMK queda validada como una fuente BPM de mercado físico de madera a nivel de producto. Los once resultados públicos abiertos en el orden congelado contienen producto o `sortiment`, volumen físico en m³, precio en €/m³ o vectores de precio por clase, destino y, en las contrataciones continuas, fase de entrega. No se trata de una clasificación administrativa ni de un proxy macroeconómico.

La evidencia más nítidamente estacional es la venta de astilla de madera con entrega junio-agosto de 2024: 10.000 m³ adjudicados entre cinco destinos/compradores, con conversión oficial explícita `1 m³ = 2,78 pm³`. Esto confirma que existen celdas de producto y fase calendario físicamente interpretables. No demuestra todavía mejora predictiva del modelo estacional.

## Comparación con el checkpoint anterior

Antes de abrir los cuerpos históricos sólo se conocían URLs, tipos y fechas aparentes. Ahora está establecida la granularidad física real, la recurrencia de productos y la diferencia entre tres relojes: fecha de oferta/subasta, fecha del protocolo y período de entrega. El nombre del archivo no puede usarse como sustituto de esos relojes.

## Frontera causal

Todo 2023-2024 permanece `HISTORICAL_ELIGIBILITY_ONLY`: no ajustó modelos, no produjo predicciones, no actualizó posteriores ni `Z_post`, y no seleccionó ganadores. La cadena ciega continúa empezando en 2025, cuando existen pares públicos oferta-resultado. La estacionalidad sólo podrá activarse en una celda después de dos observaciones previas comparables de la misma fase; en otro caso será `NOT_ESTIMABLE_SEASONAL_SUPPORT`.

## Hallazgo adverso preservado

El resultado del 30 de octubre de 2024 contiene nueve fórmulas de producto (`B38:B46`) que dependen de un libro externo ausente (`[4]müügiobjektid`). Esas filas conservan volumen y precio, pero el producto no se reconstruye ni se adivina: quedan `PARTIAL_NOT_ESTIMABLE_EXTERNAL_LINK_PRODUCT_B38_B46`.

## Consecuencia para BPM y HBP coral

RMK aporta a BPM una jurisdicción de mercado primario físico con producto, precio y cantidad; complementa a AEAT sin mezclarse con ella. En el grafo HBP coral, Eurostat y Puertos pueden aportar contexto industrial de calendario, pero no pueden compartir posterior ni sustituir el resultado de una celda RMK. La ganancia coral es cobertura de mecanismos, no pooling estadístico.

## Próxima acción decisiva

Congelar el contrato exacto de extracción para las ofertas 2025, abrir la primera oferta sin su resultado, emitir predicciones locales de participación/precio/cantidad cuando sean estimables, y sólo entonces abrir el resultado correspondiente y actualizar cada posterior y `Z_post` sin reinicios.
