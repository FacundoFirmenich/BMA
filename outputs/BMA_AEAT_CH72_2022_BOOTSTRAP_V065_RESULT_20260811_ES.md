# BMA — cierre del bootstrap AEAT CH72 2022 v0.6.5

Estado: `AUDITED_RETROSPECTIVE_M0_BOOTSTRAP_ONLY`

## Resultado

La cadena mensual 2022 terminó con 11 objetivos (febrero--diciembre), una
predicción para el mes inmediatamente siguiente en cada transición y un
posterior `Z_post` future-only por objetivo. Diciembre queda expresamente
marcado como `YEAR_END_UNCALIBRATED`.

| Variable | BMA | Control | Meses BMA mejores |
|---|---:|---:|---:|
| Participación (Brier micro) | 0.212174 | 0.521243 (control congelado) | 10 victorias, 1 empate |
| Cantidad (MALE micro) | 1.491994 | 1.183252 (persistencia) | 0/11 |
| Valor estadístico unitario (MALE micro) | 0.470117 | 0.360215 (persistencia) | 0/11 |

Los valores continuos son cantidad y valor estadístico unitario de comercio
exterior; este último no equivale a precio de transacción, de subasta ni spot.

## Comparación y significado

El patrón coincide cualitativamente con el run 2024 ya sellado: participación
es marcadamente mejor que su control, mientras que cantidad y valor pierden
frente a persistencia. Esto no admite ganador global ni promoción. Tampoco
constituye evidencia a favor o en contra de la estacionalidad: 2022 es sólo la
primera firma que alimenta la siguiente fase.

## Evidencia y custodia

El auditor genérico verificó `PASS`: 58 artefactos manifestados, 34 eventos de
secuencia, 11 freezes, 11 adjudicaciones, 11 posteriores y 11 `Z_post`; no hay
ZIP raw persistidos. Los archivos fuente históricos se leyeron uno por vez en
memoria. La corrección de transporte para directorios históricos AEAT probó las
dos capitalizaciones oficiales del nombre mensual y registró la URL que abrió
cada fuente; no alteró artefactos ya sellados.

Run: `evidence/runs/aeat-ch72-monthly-sequential-v0.6.5-2022-bootstrap-r2`.

## Límite y siguiente decisión

Es desarrollo retrospectivo, no validación prospectiva ni evidencia diaria.
El siguiente paso es la cadena 2023 sin reinicio: diciembre 2022 predice enero
2023 y cada mes posterior predice sólo el siguiente. El posterior causal de
esa cadena no puede incorporar 2024. En paralelo se ejecutará, como diagnóstico
separado y explícitamente bidireccional, la prueba de recurrencia estacional
2022+2024 contra 2023; no podrá actualizar un freeze o posterior causal de 2023.
