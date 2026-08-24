# HBP Argentina + Prodcom — checkpoint de custodia pública 2026-08-22

## Posición del proyecto

BayME/BMA queda mejor posicionado en cobertura observacional industrial y en
separación de jurisdicciones. No hay un nuevo resultado causal ni una victoria
de modelo: la adquisición se realizó después de publicarse junio y estuvo
prerregistrada expresamente como custodia y sondeo sin ajuste.

## Resultado observado

### Argentina: IPI manufacturero

El informe oficial publicado el 7 de agosto de 2026 queda preservado byte a
byte. Para junio de 2026 informa índice original 119,9 (base 2004=100), +2,0 %
interanual, −2,2 % acumulado enero-junio, índice desestacionalizado 119,1 y
+0,9 % frente a mayo. Nueve de las dieciséis divisiones subieron en términos
interanuales.

La madera ya no aparece sólo como rótulo amplio. La subclase «Madera y productos
de madera y corcho, excepto muebles» (códigos 20100/210/220/230/290) registra
índice 87,9, +17,3 % interanual, +9,2 % acumulado y contribución de 3,5 puntos a
la variación de su agrupación. La agrupación 20-22 —madera, papel, edición e
impresión— registra índice 102,9 y +8,4 % interanual.

### Argentina: utilización de capacidad instalada

El informe publicado el 14 de agosto queda preservado por separado. Junio marca
59,1 % de utilización frente a 58,9 % un año antes. El indicador se construye
sobre un panel de 600 a 700 empresas y mide capacidad utilizada, no cantidad
producida. Metálicas básicas alcanza 68,7 %, papel y cartón 66,2 %, automotriz
45,5 % y metalmecánica excepto automotores 41,5 %.

### Eurostat Prodcom

La consulta quedó limitada antes de abrirla a España × producto 16101035 × 2024
× cantidad/unidad/flag. Eurostat confirmó la identidad: madera aserrada de
pícea o abeto. El cubo respondió correctamente, pero no contiene ninguna
observación publicable para esa celda. El resultado es
`NOT_ESTIMABLE_NO_CELL`: no hay cantidad, unidad ni flag que puedan utilizarse.
No se sustituyó el producto después de ver el vacío.

## Comparación y significado

Antes de este sondeo, Argentina y Prodcom estaban integrados principalmente por
contrato y documentación. Ahora existen bytes oficiales, cabeceras, fechas,
hashes independientes y magnitudes industriales verificadas. El salto
cuantitativo es una cobertura argentina de nivel general, dieciséis divisiones,
subclases y doce bloques de capacidad. El salto cualitativo es distinguir tres
objetos que no deben confundirse:

1. IPI: outcome mensual de actividad manufacturera.
2. UCII: estado mensual de capacidad productiva.
3. Prodcom: identidad y, cuando existe, cantidad anual por producto físico.

No se suman observaciones ni verosimilitudes entre esos paneles. Tampoco se
evalúa ganador global: cada claim sigue gobernado por su celda, fuente, unidad,
vintage y calendario.

## Límites, reparabilidad e incertidumbre

Los dos informes argentinos son vintages corrientes observadas después de su
publicación y todos los datos 2026 están marcados provisionales. No reparan el
freeze histórico perdido ni validan prospectivamente un modelo. El informe IPI
expone dieciocho filas mensuales a nivel general, menos que el mínimo de treinta
y seis meses fijado para pronosticar. El XLS oficial completo fue preservado,
pero es un libro binario antiguo: el lector OpenXML y la automatización local de
Excel no pueden abrirlo. La brecha es reparable mediante una futura fuente
machine-readable oficial o un lector autorizado; no mediante transcripción
inventada.

UCII queda como observador: sustituir IPI por capacidad introduciría una
equivalencia causal falsa. Prodcom es anual, revisable y el producto seleccionado
está vacío; por tanto tampoco puede gobernar un target mensual.

## Consecuencia para BMA/BayME y BIND

La coral industrial gana resolución y custodia, pero no evidencia de promoción.
Para BMA/BayME, el diseño correcto es mantener outcomes y observadores separados
y alinear fases calendario sólo en futuros freezes causales. Para BIND, mejora
la trazabilidad del producto científico, no la preparación comercial ni una
afirmación de superioridad predictiva.

## Próxima acción decisiva

Congelar Argentina sólo cuando exista una serie estructurada de al menos treinta
y seis meses disponible antes del target. Cualquier nuevo producto Prodcom debe
seleccionarse antes de consultarlo y preservar vacíos o confidencialidad. En
paralelo, la ampliación siguiente debe probar observadores públicos de flujo
físico —puertos— y demanda industrial —TED— sin convertir conteos de eventos en
cantidades y sin incorporarlos a M2 hasta demostrar alineación causal.

