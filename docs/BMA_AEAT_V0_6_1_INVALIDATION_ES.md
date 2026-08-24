# Invalidación científica vinculante — BMA AEAT v0.6.1

Fecha: 2026-08-09

Estado único: `INVALID_EXPERIMENT_NO_SCIENTIFIC_EVIDENCE`.

La v0.6.1 comparó diez unidades temporales mensuales de entrenamiento con una
sola unidad temporal mensual objetivo. Además, el conector leyó la fecha diaria
de admisión contenida en el registro AEAT y después la descartó al agregar por
mes. Esto viola el contrato temporal de BMA.

## Invariante violado

`unidad de entrenamiento = unidad de predicción = unidad de adjudicación = unidad de Z_post`

La medida del bloque también debe conservarse: N unidades de entrenamiento se
contrastan con N unidades objetivo comparables. Cada outcome se acumula en su
misma unidad atómica y solo reinforma estados futuros. Las celdas transversales
no aumentan el número de unidades temporales.

## Consecuencia

Ninguna métrica, peso, posterior, intervalo, comparación, gate ni conclusión de
v0.6.1 es evidencia científica de BMA. No se reutiliza para modelado, selección
de expertos, selección de ventanas, BIND, promoción ni claims industriales.

Los artefactos se conservan exclusivamente como registro histórico de un
experimento inválido y de la causa de su invalidación. Preservarlos no les
confiere utilidad científica.

Solo permanecen como hechos externos que deberán revalidarse bajo un contrato
nuevo:

- el diseño público AEAT tiene registros de 226 bytes;
- sus columnas 20–25 contienen fecha de admisión `AA/MM/DD`;
- los archivos se publican como lotes mensuales, por lo que fecha económica y
  disponibilidad real son relojes diferentes.

El PR #1 fue cerrado sin merge. La ejecución v0.6.1 queda prohibida como base de
integración.

## Reemplazo obligatorio

La unidad primaria será `celda × día`. Un bloque de N días de entrenamiento se
contrastará con N días objetivo. Las adjudicaciones serán diarias y aditivas;
la semana y el mes serán estratos derivados que preservan todas las unidades
diarias. Se analizarán conjuntamente dinámica intramensual e intermensual.

No habrá nueva ejecución hasta congelar: validez de fechas, estado cero/no
disponible, bloques N:N, ventanas, baselines, disponibilidad de la fuente y un
bloque objetivo intacto.
