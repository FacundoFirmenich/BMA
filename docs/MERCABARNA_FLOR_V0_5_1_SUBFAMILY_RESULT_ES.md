# Mercabarna Flor v0.5.1: flor, planta, verdes y complementos

## Posición del proyecto

BMA queda mejor y más precisamente posicionado que en v0.5.0. El resultado
favorable ordinario ya no se atribuye indistintamente a "flores y plantas": se
separaron 98 productos del entrenamiento en 36 de flor cortada, 22 de planta
viva, 23 de árboles y verdes, 13 complementos y 4 productos no resueltos.

La taxonomía usa solo nombres presentes en entrenamiento 2026-07-01--20. Cuatro
etiquetas ambiguas —Agaphanthus, Heliconia, Hortensias y Strelitzia— conservan
`UNRESOLVED`. Siete productos realmente nuevos en el target también quedan sin
inferir. No se usaron sus outcomes para decidir la clase.

## Participación ordinaria

| Subfamilia | n | positivos | Brier BMA | Brier congelado | mejora | estado |
|---|---:|---:|---:|---:|---:|---|
| Flor cortada | 448 | 152 | 0,200662 | 0,207726 | 3,40 % | favorable descriptivo |
| Planta viva | 192 | 16 | 0,142360 | 0,173216 | 17,81 % | favorable descriptivo |
| Árboles y verdes | 208 | 55 | 0,197083 | 0,205826 | 4,25 % | favorable descriptivo |
| Complementos | 208 | 47 | 0,153516 | 0,157300 | 2,41 % | favorable descriptivo |
| No resuelto | 40 | 11 | 0,151779 | 0,161006 | 5,73 % | no estimable por soporte |

Sí: la señal de participación favorable incluye específicamente planta viva en
el régimen ordinario, con el mayor gain descriptivo de las cuatro subfamilias.
Esto no es una prueba de superioridad poblacional ni prospectiva.

## Cantidad ordinaria condicional a participación

| Subfamilia | n | BMA | congelado | persistencia | fuerte | estado |
|---|---:|---:|---:|---:|---:|---|
| Flor cortada | 153 | 1,010987 | 1,014476 | 1,230591 | 1,291627 | favorable descriptivo |
| Planta viva | 16 | 1,646679 | 1,682013 | 1,897301 | 1,881594 | `NOT_ESTIMABLE` |
| Árboles y verdes | 55 | 0,628501 | 0,627476 | 0,747963 | 0,885990 | mixto; abstención |
| Complementos | 47 | 0,645698 | 0,663346 | 0,770877 | 0,834336 | favorable descriptivo |
| No resuelto | 12 | 1,147098 | 1,111491 | 1,406124 | 1,382913 | `NOT_ESTIMABLE` |

Para planta viva, la dirección es favorable frente a persistencia (13,21 %) y
baseline fuerte (12,48 %), con récord 10--6 frente a ambos. Sin embargo, n=16
queda por debajo del umbral precongelado de 30. Por tanto, no se promueve el
resultado: es una señal prioritaria para ampliar, no evidencia suficiente.

Árboles y verdes mejora a los dos comparadores externos, pero pierde por un
margen mínimo frente al control congelado (0,628501 vs 0,627476); el estado
correcto es mixto y `ABSTAIN`. Complementos y flor cortada sí son favorables en
los cuatro contrastes descriptivos del régimen ordinario.

## Regímenes adversos y límites

Sábado y fin de mes mantienen las abstenciones de v0.5.0. En fin de mes, la
participación de planta viva empeora 31,79 % frente al control congelado y la
cantidad solo aporta 17 observaciones no calibradas. El precio hereda
`DEGENERATE_METRIC_VETO`. La auditoría no refitó el modelo ni creó evidencia
prospectiva; estratificó los scores congelados de v0.5.0.

## Consecuencia para BIND

La demo puede afirmar que BMA separa actividad, participación y cantidad por
subfamilia y sabe abstenerse cuando el soporte o el régimen no alcanzan. Para
plantas vivas, la entrada defendible hoy es participación ordinaria; la
cantidad necesita más días activos y no debe presentarse como validada.

Dos ejecuciones independientes fueron byte a byte idénticas. Manifest:
`ab06e209c22415d8a7b527d1d47eb79c899bd84dc20b598fb3ac1c9a424f2971`.
