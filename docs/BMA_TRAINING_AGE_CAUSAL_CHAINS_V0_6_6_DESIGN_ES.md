# BMA — investigación general de edad de entrenamiento mediante cadenas causales

## Objetivo

Medir qué cambia cuando el mismo algoritmo llega al mismo objetivo mensual con posteriores de distinta antigüedad. La intervención es algorítmica: cada brazo recibe una cantidad diferente de historia mensual admisible, pero mantiene el mismo objetivo, fase calendario, variable, métrica y soporte congelado.

No se investiga si “más datos ganan en general”. Se investiga localmente si una cadena de 24 o 36 meses mejora, empeora o empata a una de 12 meses al predecir exactamente el mismo mes siguiente.

## Cómo se evita condensar meses

Para un objetivo como junio de 2025:

- brazo de 12 meses: nace en junio de 2024;
- brazo de 24 meses: nace en junio de 2023;
- brazo de 36 meses: nace en junio de 2022.

Cada brazo predice julio después de junio, agosto después de julio y así sucesivamente. Cada paso escribe congelación, abre sólo su mes objetivo, adjudica y genera posterior y `Z_post`. Ningún brazo convierte 12, 24 o 36 meses en una sola observación ni salta directamente al objetivo final.

Los tres brazos terminan prediciendo junio de 2025 desde mayo de 2025. Sus edades difieren, pero la fase inicial y el objetivo están alineados por usar edades múltiplos de doce meses.

## Comparación

La unidad primaria es una celda idéntica del mismo objetivo mensual. Se calculan diferencias pareadas de pérdida entre edades 12–24, 12–36 y 24–36, separadamente para participación, cantidad y valor unitario estadístico.

El soporte común se construye exclusivamente con información disponible hasta el mes anterior al objetivo. La presencia real del objetivo no puede decidir qué celdas entran en participación. Cantidad y valor unitario conservan su condicionamiento y pueden devolver `NOT_ESTIMABLE`.

Las salidas permitidas son `OLDER_BETTER_LOCAL`, `YOUNGER_BETTER_LOCAL`, `LOCAL_TIE` y `NOT_ESTIMABLE`. No existe adjudicación conjunta entre meses, variables o fases.

## Separación respecto de la estacionalidad

El experimento primario usa únicamente el modelo mensual ordinario. Introducir el selector estacional confundiría edad de entrenamiento con cambio de familia predictiva. La validación del selector v0.6.6 será otro experimento sobre el mismo año intacto, con paquetes y reclamos separados.

## Datos y autoridad

Los años 2022–2024 ya participaron en el descubrimiento y no pueden funcionar como confirmación. El primer panel elegible requiere un año desde 2025 que permanezca sin abrir hasta congelar código, hashes, soporte y cadenas, o una jurisdicción distinta igualmente intacta. Si no existe una fuente admisible, el resultado es `NOT_ESTIMABLE`; no se sustituyen datos ni se simula el experimento.

## Incertidumbre

Se conservarán todas las diferencias pareadas por celda. Como diagnóstico de dependencia se usará bootstrap agrupado en dos dimensiones —flujo-CN4 y socio— con 2000 réplicas y semilla 66036. CN4 actúa aquí como agrupación administrativa para dependencia, no como afirmación de producto físico único. Los intervalos del 90 % describen incertidumbre; no habilitan promoción automática por un valor p.

## Diciembre

Diciembre mantiene congelación, resultado y actualización del posterior, pero no participa en la adjudicación primaria mientras siga `YEAR_END_UNCALIBRATED`.

## Estado

El protocolo y el motor de invariantes están congelados. Ningún objetivo desde 2025 fue abierto durante su creación. La ejecución queda bloqueada únicamente por la adquisición y congelación de una fuente mensual intacta y admisible.
