# BMA AEAT capítulo 72 — resultado del holdout de noviembre de 2024

Fecha de cierre: 2026-08-09  
Experimento: `bma.aeat.chapter72.nov2024.v0.6.1`  
Estado: `EXECUTED_RETROSPECTIVE_INDUSTRIAL_HOLDOUT`  
Promoción: `NO_PROMOTION_SINGLE_RETROSPECTIVE_MONTH`

## Resultado sustantivo

BMA queda mejor posicionado como arquitectura multijurisdiccional de mercados
físicos: el experimento aporta evidencia real en producción industrial estricta
—hierro y acero, capítulo 72 de la Nomenclatura Combinada—, fuera de alimentos,
flores, plantas y madera. La extensión resulta favorable para masa y valor
unitario estadístico frente a comparadores estáticos o de persistencia, pero no
demuestra superioridad general: un experto simple de recencia iguala o supera
ligeramente a BMA en las dos magnitudes continuas, y una tasa empírica simple
supera a BMA en participación.

El resultado es, por tanto, informativo y mixto. Justifica continuar el
desarrollo industrial y revisar el aprendizaje de pesos; no justifica afirmar
que BMA sea el mejor predictor, promover el modelo ni presentar el valor
unitario aduanero como precio de transacción, de subasta o spot.

## Contrato ejecutado

- Fuente oficial: datos definitivos de comercio exterior de la AEAT a máxima
  desagregación para 2024.
- Dominio: capítulo 72, hierro y acero; se excluyeron gas, electricidad y
  cualquier mercado de precio regulado o administrado.
- Celda: flujo × CN8 × país socio.
- Entrenamiento: enero-octubre de 2024, diez meses completos.
- Holdout congelado: noviembre de 2024. Diciembre quedó preservado como diseño
  histórico y fue sustituido antes de ejecutar para evitar el confusor plausible
  de cierre anual.
- Objetivos: participación; masa en kg condicionada a presencia; valor unitario
  estadístico EUR/kg condicionado a masa y valor positivos.
- Comparación: persistencia, centro de celda, jerárquico, recencia y, para
  participación, tasa empírica Beta.
- Incertidumbre descriptiva: bootstrap determinista por conglomerados CN4,
  2.000 réplicas. No constituye prueba de independencia.

## Escala y orden causal

El entrenamiento procesó 7.247.656 líneas brutas en memoria, de las cuales
330.176 pertenecían al capítulo 72; produjo 42.242 agregados mensuales y un
universo de 9.177 celdas. Noviembre contenía 686.306 líneas brutas, 31.889 del
capítulo 72, 4.280 agregados, 3.962 celdas conocidas y 318 celdas nuevas fuera
del universo de entrenamiento.

Las predicciones se congelaron antes de abrir el archivo objetivo:

- freeze de predicciones: `2ac9ad18175b4b7a6adfd160a136ecb32a8423577ff847fa3c97e2609f32b74e`;
- archivo objetivo: `134438e2334cf1a7323d6520035b92cfb5522233116c7f2cc8c8dc0b59de5106`;
- agregado objetivo: `d42696402a9a749f499c9f4bbb60e8d30609fbb0f09b68f292fc4aadbaf85a63`;
- gate causal: `PASS_FREEZE_PRECEDES_TARGET_OPEN`.

Los ZIP mensuales nunca se persistieron: se descargó y procesó un archivo por
vez en memoria. El bundle de evidencia contiene solo agregados normalizados,
predicciones, métricas y registros causales.

## Resultados

En todas las diferencias siguientes, un valor negativo favorece a BMA.

| Objetivo | n | BMA | Comparador crítico | Diferencia | IC95 por CN4 | Gate |
|---|---:|---:|---:|---:|---:|---|
| Participación, Brier | 9.177 | 0,133950 | tasa empírica 0,132256 | +0,001694 | [0,000589; 0,002823] | mixto/adverso descriptivo |
| Masa kg, error log absoluto medio | 3.961 | 1,042750 | recencia 1,041886 | +0,000864 | [-0,001971; 0,003838] | favorable descriptivo según protocolo |
| Valor unitario EUR/kg, error log absoluto medio | 3.961 | 0,373638 | recencia 0,371867 | +0,001772 | [0,000106; 0,003404] | favorable descriptivo según protocolo |

Participación: BMA supera a persistencia, jerárquico y recencia, pero pierde
frente a la tasa empírica simple. La pérdida frente al comparador crítico no es
un empate descriptivo: todo el intervalo queda por encima de cero.

Masa: BMA supera a persistencia (-0,147297), centro de celda (-0,013303) y
jerárquico (-0,232733). Frente a recencia queda prácticamente empatado y el
intervalo cruza cero.

Valor unitario estadístico: BMA supera a persistencia (-0,029049), centro de
celda (-0,003181) y jerárquico (-0,103774), pero recencia lo supera por un
margen pequeño y consistente en este mes.

## Réplica computacional

Se ejecutaron dos campañas completas en GitHub Actions. La segunda usó una
implementación optimizada matemáticamente equivalente. Reprodujo exactamente
los datos, el universo, el orden causal, el freeze y todas las métricas
centrales. Solo cuatro extremos bootstrap variaron por redondeo de coma flotante,
con diferencia máxima `2.7755575615628914e-17`; ningún signo, intervalo ni gate
cambió. Esto demuestra reproducibilidad computacional del resultado, no añade
un segundo mes independiente de evidencia.

- campaña original: run `31316633001`, artefacto `9039039888`, digest
  `sha256:652d3351a4227aa8a71b699a6cbc79beaecb8c8e27569b32473b88c91c80f2cc`;
- réplica optimizada: run `31316930539`, artefacto `9039111449`, digest
  `sha256:bdc69776a58a4abfc313685e8ddaa600c7212041e1d8a4f913fc372465750b80`.

Los digests del bundle no tienen que coincidir: el código, los registros de
ejecución y el empaquetado difieren. La identidad decisiva está en los hashes de
fuente, agregado y freeze, y en la equivalencia de los resultados dentro del
límite de redondeo documentado.

## Significado para BIND

El experimento fortalece una candidatura BIND basada en un único producto con
jurisdicciones contractuales: demuestra que la misma arquitectura puede pasar
de mercados alimentarios y florales a una cadena industrial no biológica sin
inventar datos ni reutilizar claims. El encaje más defendible sigue siendo
previsión de demanda y apoyo a planificación/aprovisionamiento, con la decisión
operativa fuera de BMA.

La evidencia aún es insuficiente para prometer mejora universal de KPI o
autonomía de compra/precio. Un piloto debe congelar con el Venture Client el
baseline vigente, costes asimétricos, horizonte, reglas de abstención y criterio
de continuidad. El próximo gate científico es incorporar la lección adversa
—fortaleza de recencia y de la tasa empírica— al diseño de pesos usando solo
training, y probarlo en otro mes definitivo todavía intacto.

## Evidencia floral complementaria

La taxonomía fina solicitada quedó congelada separando `FLOR_CORTADA`,
`PLANTA_VIVA`, `ÁRBOLES_Y_VERDES` y `COMPLEMENTOS`. En `PLANTA_VIVA`, la
participación fue favorable descriptiva (n=192; Brier BMA 0,142360 frente a
0,173216 del origen congelado). La cantidad tuvo solo 16 observaciones y se
mantiene correctamente como `NOT_ESTIMABLE_INSUFFICIENT_SUPPORT`. Este resultado
no se mezcla con el holdout industrial.

## Frontera de evidencia y siguiente decisión

- No es validación prospectiva.
- No es evidencia de precio transaccional.
- No prueba superioridad global ni comercial.
- No autoriza promoción del modelo.
- Sí prueba una extensión industrial estricta y una ejecución causalmente
  ordenada, reproducible y útil para rediseñar el siguiente gate.

El bundle normalizado permanece en GitHub Actions. Su copia a la carpeta BMA de
Google Drive queda pendiente de autorización explícita del usuario para ese
payload concreto; no se ha eludido el bloqueo descargándolo localmente.
