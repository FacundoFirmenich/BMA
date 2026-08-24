# BPM/RMK — clausura causal retrospectiva al 21-08-2026

## Resultado sustantivo

La campaña queda cerrada hasta la frontera temporal disponible. Se ejecutaron y auditaron 14 eventos con oferta congelable y resultado adjudicable, siempre en orden causal. Dos eventos retrospectivos quedaron fuera: 28-04-2026 por ausencia de oferta recuperada y 30-06-2026 por preexposición como prueba de esquema. El 26-08-2026 permanece cerrado por ser futuro respecto del corte.

El posterior final contiene 388 celdas locales y 1.008 observaciones, exactamente 504 de precio y 504 de volumen. Hay 30 celdas con soporte M1 para uso futuro y ninguna con soporte M2 suficiente. No hubo reset, pooling N→1, aprendizaje dentro de un evento, ganador global ni promoción automática.

## Evidencia M1 observada

M1 pudo puntuarse por primera vez en 14 celdas exactas: una el 22-12-2025 y trece el 23-02-2026.

| Outcome | M1 mejora | M0 mejora | Empate |
|---|---:|---:|---:|
| Precio local | 5 | 9 | 0 |
| Volumen local | 7 | 7 | 0 |

La lectura correcta es heterogeneidad local y por outcome, no una derrota o victoria global de M1.

- `Kasepaberipuit → Pärnu`, 22-12-2025: M1 reduce el error de precio de 1,53697 a 0,08372 EUR/m³, pero empeora el error logarítmico de volumen de 2,14523 a 2,34739.
- `Kuusepaberipuit → Paldiski`, 23-02-2026: M1 reduce el error de precio de 1,56 a 0,04819 EUR/m³; M0 conserva una ventaja pequeña en volumen, 1,50244 frente a 1,59405.
- `Kasepaberipuit → Paldiski`, 23-02-2026: M1 mejora tanto precio como volumen en esa celda concreta.
- `Männipalk → Verijärve`, 23-02-2026: M0 mejora precio, mientras M1 reduce fuertemente el error de volumen de 0,21216 a 0,02215.

Estas inversiones entre precio y volumen confirman que la información útil está en jurisdicciones físicas locales. Condensarlas a un único ranking borraría precisamente el patrón que BMA/BayME busca aprender.

## Tramo final

| Evento | Estado | Resultado local | Posterior después del evento | Auditoría |
|---|---|---|---:|---:|
| 22-12-2025 | adjudicado | 18 scores; 1 M1 observado; precio M1 gana y volumen M0 gana en `Kasepaberipuit → Pärnu` | 302 celdas / 760 obs. | PASS 53/53 |
| 23-02-2026 | adjudicado con cuarentenas | 38 scores; 13 M1; precio 4 M1/9 M0; volumen 7 M1/6 M0; 15 outcomes en cuarentena | 381 / 994 | PASS 59/59 |
| 28-04-2026 | `NOT_ESTIMABLE_NO_FROZEN_OFFER` | resultado cerrado; sin score ni actualización | sin cambio | cierre hasheado |
| 28-05-2026 | expansión sin match previo | 7 outcomes nuevos; errores `null`, no cero; resultado hake no emparejado y cerrado | 388 / 1.008 | PASS 44/44 |
| 30-06-2026 | `NOT_ESTIMABLE_SCHEMA_PROBE_PREEXPOSURE` | excluido de evaluación y posterior | sin cambio | cierre hasheado |
| 26-08-2026 | `FUTURE_EVENT_NOT_OCCURRED_BODY_CLOSED` | no ejecutado | sin cambio | hold hasheado |

Los diez eventos auditados anteriores se conservan en sus cierres originales. En total, los 14 auditores eventuales suman 646 comprobaciones aprobadas. La batería de regresión vigente aprueba 25/25 pruebas.

## Qué mejoró y qué no

La posición científica mejoró en tres sentidos:

1. M1 dejó de ser sólo estimable y pasó a tener observaciones reales, con resultados favorables y adversos preservados por celda y outcome.
2. El soporte futuro aumentó hasta 30 celdas M1 sin reescribir el pasado ni condensar varios meses o destinos en un target.
3. La campaña probó que una fuente industrial difícil puede transformarse en evidencia local reproducible aun con productos, destinos, unidades, hojas y contratos heterogéneos.

No mejoró todavía en estacionalidad M2: ninguna celda alcanza dos eventos de innovación distintos en la misma fase. Esto es falta de soporte, no evidencia de ausencia de estacionalidad.

## Defectos y reparabilidad

Se detectaron y corrigieron antes de contaminar scoring o posterior: filas vacías interpretables como duplicados, precedencia del conflicto de volumen, productos multiclase, separadores finales vacíos, semántica de lotes `LAOKAUP` y resultados no emparejados. Los artefactos inválidos o supersedidos se conservaron con estado explícito; no se borraron ni se promovieron.

Las pérdidas de información no reparables permanecen visibles:

- objeto 6 del 29-10-2025: conflicto 4.686 frente a 5.549 m³;
- 15 outcomes del 23-02-2026: seis por conflicto de volumen y nueve por precios multiclase sin pesos observables;
- resultado 28-04-2026 sin oferta;
- resultado hake 28-05-2026 sin componente de oferta;
- par 30-06-2026 preexpuesto como prueba de esquema.

## Consecuencia para BMA/BayME

RMK ya constituye una jurisdicción industrial física europea útil dentro de BMA: madera, contratos reales, destinos de entrega, precio y volumen, calendario irregular y abstención explícita. No prueba superioridad general de BMA, pero sí prueba que el aparato causal puede producir señal local, conservar evidencia adversa y aumentar soporte sin falsear comparabilidad.

La siguiente etapa es integrar Argentina y Eurostat como jurisdicciones separadas bajo el mismo contrato coral: identidad local, freeze previo, outcome siguiente, actualización acumulativa, abstención y ausencia de ganador global. Después se incorporarán nuevas fuentes públicas industriales sólo si aportan productos físicos, frecuencia y targets observables sin mezclar mercados, unidades ni calendarios.
