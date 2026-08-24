# Checkpoint sustantivo: Luke Finlandia, mercado físico de madera

Fecha: 2026-08-22  
Estado: `PASS_SINGLE_PRODUCT_PRICE_VOLUME_SUPPORT`

## Resultado en plata

Se encontró la primera fuente pública europea de esta ampliación que entrega en
una misma celda mensual un producto físico, un volumen y un precio: troncos de
abeto vendidos en pie en Finlandia. Para julio de 2026, el valor nacional
publicado es 429 miles de m³, es decir 429.000 m³, y 83,14 EUR/m³. La tabla fue
actualizada el 20 de agosto de 2026.

Esto posiciona mejor a BPM que Puertos, TED y el corte Prodcom vacío porque la
unidad observada ya tiene mercado, producto, modalidad de venta, geografía,
calendario, cantidad y precio. No demuestra todavía capacidad predictiva.

## Custodia y corrección previa al dato

La consulta se preregistró antes de abrir esquema o valores. El primer intento
consumió un único GET de metadatos y se detuvo antes del POST porque PXWeb
presenta la jerarquía como `..Spruce logs` y el único precio como
`Price (EUR/m³)`. Se congeló una enmienda ligada al hash del metadato, sin haber
visto valores, que sólo corrigió esa sintaxis y fijó los códigos exactos:

- `INFO=M3T`: volumen en miles de m³;
- `INFO=E_M3`: precio en EUR/m³;
- `M=2026M07`;
- `MPKH=SSS`: Finlandia completa;
- `KAUP=PKAUP`: venta en pie;
- `PTL=TUK_KU`: troncos de abeto.

Después se realizó el único POST permitido, que devolvió dos celdas y HTTP 200.
No hubo segunda consulta de metadatos, sustitución de producto ni descarga
histórica masiva.

## Soporte y límites

El metadato corriente enumera 79 meses consecutivos, desde 2020-01 hasta
2026-07, superando el umbral técnico de 36 meses. La fuente editorial oficial
declara publicación mensual y anual, precios basados en acuerdos de compraventa
y una cobertura aproximada del 90 % de las compras de la industria forestal a
bosques privados no industriales.

La tabla también contiene notas explícitas de revisiones. Por ello, la serie
actual sirve para diseñar y entrenar retrospectivamente bajo una jurisdicción
separada, pero no reconstruye vintages de primera publicación. La observación de
julio se abrió después de publicarse y no puede tratarse como forecast causal.

Hay una discrepancia documental preservada: la página de Luke exhibe la marca de
Estadística Oficial de Finlandia, mientras el campo técnico
`extension.px.official-statistics` del JSON vale `false`. Hasta reconciliarla,
se describe como tabla pública de Luke sin usar ese flag para elevar claims.

## Significado científico y consecuencia

Luke habilita una nueva jurisdicción BPM Finlandia de mercado físico de madera,
mucho más limpia que una agrupación administrativa CN4: aquí conocemos producto,
modalidad, volumen y precio. Es además compatible con el estudio estacional,
porque hay más de seis años mensuales corrientes. Pero la estacionalidad no se
activa post hoc: requiere su propio freeze de soporte, priors, pesos, recovery e
invariantes antes de abrir outcomes de evaluación.

Para BMA/BPM, el candidato debe pasar a una campaña causal separadamente
preregistrada, mes a mes, donde cada periodo prediga sólo el siguiente y
posterior/`Z_post` acumulen sin reset. Para BIND, mejora de forma concreta la
demostrabilidad de una aplicación industrial europea; todavía no valida
precisión, piloto ni readiness comercial.

No se realizó fit, forecast, score, actualización de posterior o `Z_post`,
pooling con RMK/AEAT/Eurostat/Argentina, ganador global ni promoción automática.

## Siguiente acción crítica

Diseñar la campaña Luke por años y por producto exacto, congelando primero el
histórico corriente como entrenamiento retrospectivo no-vintage y reservando
las próximas publicaciones como vintages prospectivas inmutables. En paralelo,
Comext queda como segundo candidato para cantidades físicas mensuales por CN,
pero sólo como comercio exterior y con un gate explícito de revisiones,
confidencialidad y masa neta estimada.

