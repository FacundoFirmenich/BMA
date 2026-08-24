# BayME - disponibilidad de outcomes pendientes

Fecha: 2026-08-24
Estado: `NO_PENDING_TARGET_OUTCOME_AVAILABLE`

## Resultado sustantivo

Ninguno de los cinco targets congelados de la coral está disponible todavía.
La consecuencia correcta no es una ejecución vacía: es preservar los cinco
`OUTCOME_PENDING`, sin score, sin posterior, sin `Z_post` y sin congelar el
período siguiente.

Esto mantiene a BayME igual de bien posicionado causalmente que en el checkpoint
anterior. No añade rendimiento predictivo, pero evita cinco contaminaciones
posibles: imputar un cero, descargar un vintage inexistente, actualizar dos
veces, reescribir una freeze o fingir que una ausencia equivale a pérdida.

## Evidencia por campaña

### Luke Finlandia - agosto 2026

La API PxWeb enumera 79 meses y termina en `2026M07`. Agosto no aparece. Esto
rige por separado para volumen y precio, aunque ambos comparten la misma
jurisdicción y consulta de disponibilidad.

### INDEC IPI - julio 2026

Se ejecutó sólo `HEAD`. El workbook conserva:

- `Last-Modified: Fri, 07 Aug 2026 18:51:55 GMT`;
- `ETag: "9fca30d19d26dd1:0"`;
- `Content-Length: 1087488`.

Son exactamente las cabeceras de la fuente congelada que termina en junio. No se
descargó ni abrió un workbook nuevo.

### INDEC UCII - julio 2026

Se ejecutó sólo `HEAD`. El workbook conserva:

- `Last-Modified: Fri, 14 Aug 2026 18:52:54 GMT`;
- `ETag: "9289aa1d1e2cdd1:0"`;
- `Content-Length: 57344`.

También coincide con la captura que termina en junio. El fallo v0.1 y la
reparación v0.2 permanecen inmutables.

### Eurostat STS España manufactura - julio 2026

La consulta exacta de una celda devolvió HTTP 200, pero el resultado contiene
`value={}`, dimensión temporal de tamaño cero y último período general
`2026-06`. El dataset declara actualización 2026-08-22 11:00 CEST; aun así,
julio no está presente para esta celda.

## Gates de fuente actualizados

La producción industrial letona `RUI020m` falla por HTTP 400 incluso al pedir
la primera combinación declarada por sus propios metadatos. El problema ya no
puede atribuirse a C16 o a un mes reciente; queda como defecto de POST o
requisito no documentado. El esquema sigue siendo real, pero no hay muestra.

EUMOFA sigue sin muestra: su interfaz de datos respondió 403 y el runtime del
navegador de la app no pudo iniciar por un error local de ACL, incluso tras
autorizar lectura del plugin. Esa segunda falla no demuestra que EUMOFA exija
login; sólo demuestra que este entorno no pudo probar la interfaz.

## Significado y reparabilidad

Las ausencias son reparables por publicación, no por código. Cuando una fuente
cambie, se repite únicamente su comprobación acotada. La primera que contenga el
target habilitará la secuencia local completa: capturar bytes, verificar
identidad, adjudicar, actualizar una sola vez posterior y `Z_post`, y congelar
exactamente el mes siguiente.

Los gates EUMOFA y Letonia son reparables por acceso: export anónimo manual
mínimo para EUMOFA o documentación/consulta POST correcta para `RUI020m`.
Ninguno justifica crear cuenta, contactar a terceros ni introducir datos
plausibles.

## Consecuencia para el objetivo

BPM conserva dos forecasts Luke genuinamente prospectivos. HBP conserva IPI,
UCII y Eurostat como cadenas pre-outcome separadas. La coral sigue siendo un
sistema de coordinación y custodia, no un modelo agregado ni un ranking. Para
BIND, la disciplina de abstención mejora trazabilidad, pero no añade validación
industrial o comercial.

Siguiente acción: esperar un cambio oficial verificable y adjudicar el primer
target realmente publicado; mientras tanto, avanzar sólo en contratos de fuente
que no abran esos outcomes ni alteren sus freezes.
