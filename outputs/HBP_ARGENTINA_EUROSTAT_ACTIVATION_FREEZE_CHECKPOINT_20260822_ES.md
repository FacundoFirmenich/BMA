# Argentina + Eurostat — checkpoint de activación causal congelada

## Resultado

BayME/BMA queda mejor posicionado que en el checkpoint documental anterior.
Eurostat ya tenía una predicción prospectiva de julio; ahora su apertura,
scoring, actualización de pesos y continuación a agosto tienen consulta,
algoritmo y fallos explícitos congelados. Argentina IPI pasa de “XLS ilegible”
a una serie oficial estructurable de 126 meses, suficiente para congelar julio.

Todavía no hay resultado de julio ni victoria de modelo: este checkpoint ocurre
antes de consultar el target Eurostat, antes de ejecutar la freeze IPI y antes
de descargar el workbook UCII.

## Evidencia

- Eurostat: 5/5 artefactos de la freeze coinciden en hash y tamaño.
- INDEC/Prodcom: 6/6 payloads primarios coinciden en hash y tamaño.
- IPI BIFF8: 126 meses contiguos, 2016-01 a 2026-06; último original 119,8601
  y último desestacionalizado 119,0982, reconciliados con 119,9 y 119,1 del PDF.
- Software: 12 pruebas focales y 115 pruebas totales pasan; lint limpio.
- Salidas de IPI, Eurostat-adjudicación y UCII-schema: ausentes al congelar.

## Significado

El salto cuantitativo inmediato es habilitar 125 transiciones argentinas
oficiales sin transcripción manual. El salto cualitativo es que capacidad,
producción y producción armonizada europea quedan como tres objetos causales
distintos. La coral puede compararlos por cobertura, pérdidas, abstenciones y
edad de entrenamiento, pero nunca sumar sus verosimilitudes.

## Límites y reparabilidad

El historial IPI es una vintage corriente provisional, no una colección de
primeras publicaciones históricas. Eurostat ordinario también expone la última
vintage. Eso se repara hacia adelante congelando cada nueva respuesta, no
reescribiendo el pasado. UCII sólo avanza a fit si el esquema capturado permite
una serie exacta y el target julio sigue ausente.

## Próximo gate

Commit y push de esta freeze. Recién después: IPI freeze, Eurostat julio y UCII
schema, cada uno con una sola ejecución y sin retry silencioso.
