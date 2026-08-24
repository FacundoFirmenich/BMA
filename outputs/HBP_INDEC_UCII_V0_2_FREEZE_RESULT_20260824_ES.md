# HBP Argentina — resultado del freeze UCII v0.2

Fecha de cierre documental: 2026-08-24
Estado: `FROZEN_PRE_OUTCOME`
Target: nivel general de utilización de la capacidad instalada, julio de 2026.

## Resultado observado

La reparación v0.2 permitió inicializar el posterior sin cambiar el target, los modelos, los priors, los pesos ni el calendario congelados en v0.1. La única modificación fue aceptar soporte cerrado `[0,100]` para los doce bloques sectoriales observadores; esos bloques permanecen fuera de la likelihood del nivel general.

La serie general contiene 126 meses entre 2016-01 y 2026-06 y 125 transiciones. El último valor observado es 59,1%.

| Modelo | Mediana julio 2026 | Intervalo predictivo 90% | Peso congelado |
|---|---:|---:|---:|
| M0 — persistencia acotada | 59,100000 | [53,778907; 64,216117] | 1/3 |
| M1 — deriva acotada | 59,069335 | [53,726292; 64,206456] | 1/3 |
| M2 — armónico anual y semestral | 59,254500 | [54,285342; 64,041306] | 1/3 |

M2 presenta una escala predictiva interna menor (`0,122324`) que M0 (`0,130771`) y M1 (`0,131283`). Esto describe el posterior ajustado con datos hasta junio; no autoriza a declarar superioridad predictiva antes de observar julio.

## Fronteras causales y adversas

- El outcome de julio no fue abierto.
- No hubo score, actualización posterior del target ni congelación de agosto.
- No hubo pooling de los doce sectores hacia el target general.
- Los dos ceros sectoriales de abril de 2020 se conservaron como eventos límite.
- El fallo v0.1 permanece inmutable y no se reinterpretó como ejecución exitosa.
- `Z_post` es el estado posterior por modelo; no es `Z-XPL` ni un residuo z estandarizado.
- `global_winner` continúa en `null`; no existe promoción automática.

## Significado para HBP y la integración coral

Argentina aporta ahora dos freezes productivos separados: IPI manufacturero y UCII general. Constituyen dos jurisdicciones/targets complementarios, no observaciones intercambiables. Su utilidad coral será comparar cobertura, familia de estado, disponibilidad y comportamiento futuro mediante un ledger tipado, sin colapsarlos en una media ni permitir que uno transfiera autoridad al otro.

## Evidencia exacta

- Workbook fuente: `B603A98B5A148DE4A3150F0AC1119CDF8F1EE04219B051A5DB6004803D340471`.
- Preregistro v0.2: `53258F0CCE99BE141DC96B4DFB1BA16087DE284411C3BA91620087DA5CB6643F`.
- Forecast freeze: `34EF0AB891CAFFF4B2531AC4BF6C0098047A19612CB44C23BD28DB7454FA8435`.
- Posterior/Z_post: `B2D29BB7E166B8F85B74EAB69C2FA94F3ED22325CD595A013FD59DB25463D563`.
- Manifiesto: `000A0BFC19107F04BE1C56A1D0FECC15C2C88CA9981645A3BB5AF803BD6EC31B`.
- Fallos de hash o tamaño: 0.

Siguiente gate: custodiar este freeze, resincronizar las ocho conversaciones nativas embebidas y construir la integración coral sólo con estados y jurisdicciones explícitos.