# BMA AEAT Chapter 72 v0.6.4 — resultado mensual secuencial 2024

## Posición científica

La campaña deja a Bayesian Markets App (BMA) mejor posicionada para predecir participación y para investigar aprendizaje acumulativo y estacionalidad, pero no para sostener superioridad general. La rama de participación supera al control congelado en 10 de 11 objetivos mensuales y empata el primero. Las ramas de cantidad y valor unitario estadístico reducen mucho su desventaja inicial, pero no superan a persistencia en ningún mes cuando se agregan las celdas del objetivo.

La clasificación permanece `RETROSPECTIVE_DEVELOPMENT_REPLAY`, sin promoción, sin ganador global y sin evidencia diaria o prospectiva.

## Contrato ejecutado

- Cadena única: enero predice febrero; cada resultado mensual produce adjudicación, `Z_post` y posterior para el mes siguiente.
- Unidad de entrenamiento, predicción y adjudicación: exactamente un mes calendario.
- Transiciones: 11, desde `2024-01->2024-02` hasta `2024-11->2024-12`.
- Celda: flujo × CN8 × país socio.
- Cantidad: MALE sobre `log1p(weight_kg)`.
- Valor: MALE sobre `log(statistical_unit_value_eur_per_kg)`. Es valor unitario estadístico aduanero, no precio spot ni precio individual de transacción.
- Participación: Brier frente al control estructural congelado en enero; las identidades nuevas se admiten sin añadir resultados posteriores al control.
- Diciembre: jurisdicción separada `YEAR_END_UNCALIBRATED`.

## Resultados por mes

En participación, “ventaja” es la reducción relativa del Brier frente al control. En cantidad y valor, una brecha positiva significa que BMA todavía pierde frente a persistencia.

| Objetivo | Brier BMA | Brier control | Ventaja participación | MALE cantidad BMA | Persistencia | Brecha cantidad | MALE valor BMA | Persistencia | Brecha valor | Primeras apariciones |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2024-02 | 0.282589 | 0.282589 | 0.0% | 2.104549 | 1.065254 | +97.6% | 0.690885 | 0.306383 | +125.5% | 1,203 |
| 2024-03 | 0.282529 | 0.383412 | 26.3% | 1.742263 | 1.099875 | +58.4% | 0.600574 | 0.338978 | +77.2% | 821 |
| 2024-04 | 0.247217 | 0.413809 | 40.3% | 1.607250 | 1.132078 | +42.0% | 0.576635 | 0.347903 | +65.7% | 630 |
| 2024-05 | 0.229482 | 0.449280 | 48.9% | 1.653079 | 1.150070 | +43.7% | 0.533564 | 0.351462 | +51.8% | 577 |
| 2024-06 | 0.220502 | 0.491583 | 55.1% | 1.484586 | 1.153590 | +28.7% | 0.513605 | 0.380760 | +34.9% | 409 |
| 2024-07 | 0.206093 | 0.493604 | 58.2% | 1.421442 | 1.226750 | +15.9% | 0.495836 | 0.379363 | +30.7% | 354 |
| 2024-08 | 0.224627 | 0.597322 | 62.4% | 1.622320 | 1.393355 | +16.4% | 0.502860 | 0.394838 | +27.4% | 310 |
| 2024-09 | 0.183355 | 0.538376 | 65.9% | 1.315690 | 1.306463 | +0.7% | 0.482212 | 0.390713 | +23.4% | 305 |
| 2024-10 | 0.174679 | 0.526362 | 66.8% | 1.257727 | 1.166312 | +7.8% | 0.474858 | 0.397085 | +19.6% | 336 |
| 2024-11 | 0.173728 | 0.568215 | 69.4% | 1.286917 | 1.164276 | +10.5% | 0.484844 | 0.402687 | +20.4% | 318 |
| 2024-12 | 0.175679 | 0.609001 | 71.2% | 1.265074 | 1.212220 | +4.4% | 0.473227 | 0.396355 | +19.4% | 247 |

## Lectura anual

Los microagregados son descriptivos; no convierten celdas ni meses dependientes en réplicas independientes.

- Participación: Brier BMA `0.210459` frente a `0.505664`; reducción descriptiva de aproximadamente 58.4%. Diez victorias mensuales y un empate inicial.
- Cantidad: MALE BMA `1.504852` frente a persistencia `1.189449`; BMA es aproximadamente 26.5% peor en el microagregado. Cero victorias mensuales agregadas.
- Valor unitario: `0.525392` frente a `0.373300`; BMA es aproximadamente 40.7% peor. Cero victorias mensuales agregadas.
- Primeras apariciones acumuladas: 5,510. Nunca se puntuaron antes de disponer de soporte histórico.

La caída de la brecha de cantidad desde +97.6% en febrero hasta +0.7% en septiembre, seguida de rebotes en octubre y noviembre, es compatible con subentrenamiento inicial más dinámica intramensual/intermensual. No lo demuestra: composición cambiante y estacionalidad anual están confundidas dentro de un solo recorrido. Valor presenta una aproximación más gradual, pero tampoco cruza a persistencia.

Diciembre muestra cobertura del 90% de 97.44% en cantidad y 96.93% en valor, mayor que en meses ordinarios. Esto sugiere intervalos conservadores bajo cierre anual y justifica mantenerlo fuera de cualquier conclusión ordinaria.

## Interrupción y recuperación

La ejecución original terminó externamente después de sellar octubre, sin `stderr`, excepción registrada ni artefacto parcial de noviembre. La recuperación:

1. verificó el hash del posterior de octubre contra su `Z_post`;
2. reconstruyó historia e identidades únicamente desde los diez meses derivados existentes;
3. no reabrió enero–octubre ni reescribió artefactos;
4. congeló noviembre antes de abrirlo;
5. sustituyó escaneos repetidos por medianas transversales precalculadas algebraicamente equivalentes.

La equivalencia fue comprobada con igualdad exacta de arrays en una muestra del estado real de noviembre —21 celdas × 2 variables— y con pruebas unitarias sintéticas. Este control no es una comparación exhaustiva celda por celda, pero la transformación implementada conserva la misma selección del último antecedente y las mismas medianas.

## Integridad

- Conteos: 12 meses estructurados; 11 congelaciones; 11 adjudicaciones; 11 posteriores; 11 `Z_post`.
- Secuencia: 34 eventos; todos siguen `freeze -> apertura -> adjudicación/Z_post`.
- Manifiesto: 59 archivos verificados, cero fallos.
- Datos crudos: ningún ZIP persistido.
- Tamaño derivado completo: 28,393,738 bytes.
- Software: 53 pruebas aprobadas; Ruff aprobado.

## Consecuencia y siguiente campaña

La siguiente campaña no debe limitarse a concatenar meses. Debe ejecutar 2022–2024 en orden causal y añadir aprendizaje estacional explícito sobre innovaciones relativas:

- `M0`: estado secuencial actual;
- `M1`: `M0` más componente anual armónica;
- `M2`: `M1` más residuo mensual jerárquico de suma cero;
- pesos BMA prequentiales separados para participación, cantidad y valor;
- jerarquía global → flujo → CN4 → socio, con abstención donde falte soporte;
- comparación del margen de pérdida entre el mismo mes calendario de años sucesivos, no de niveles absolutos comercializados.

2022 estima la primera firma; 2023 aporta la primera prueba de recurrencia; 2024 ofrece una segunda repetición retrospectiva. Como el diseño se decidió después de observar parcialmente 2024, la campaña seguirá siendo desarrollo retrospectivo, no holdout prospectivo.

Antes de ejecutarla debe congelarse una implementación eficiente y demostrar equivalencia con v0.6.4. En paralelo, la búsqueda de mercados industriales europeos diarios debe priorizar fuentes de eventos físicos desagregados —TBAuctions y EquipmentWatch— por encima de índices o precios evaluados.
