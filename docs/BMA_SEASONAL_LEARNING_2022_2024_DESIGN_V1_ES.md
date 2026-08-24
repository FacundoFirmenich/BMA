# BMA — diseño de aprendizaje estacional 2022–2024 v1

Estado: `DESIGN_ONLY_NOT_PREREGISTERED_FOR_EXECUTION`

## Objetivo

Determinar si una memoria anual explícita mejora el pronóstico mensual secuencial de participación, cantidad y valor unitario estadístico por encima del aprendizaje ordinario, sin asumir estabilidad de los niveles absolutos comercializados.

La unidad no cambia: un mes predice únicamente el mes inmediatamente siguiente. La cadena comienza en enero de 2022 y continúa sin reinicios hasta diciembre de 2024. Habrá 35 objetivos: febrero de 2022 a diciembre de 2024. Enero de 2023 y enero de 2024 serán predichos respectivamente por diciembre de 2022 y diciembre de 2023.

## Variable estacional

La estacionalidad se aprende sobre innovación respecto del estado dinámico ordinario:

\[
z_{c,t}=\mu^{(0)}_{c,t\mid t-1}+s_{h(c),m(t)}+\epsilon_{c,t}.
\]

- `z` es `log1p(weight_kg)` para cantidad y `log(unit_value)` para valor.
- `mu^(0)` es la predicción del modelo secuencial no estacional.
- `s` es la desviación anual recurrente del mes calendario, no un nivel comercial absoluto.
- Para participación, `s` actúa en escala logit sobre la probabilidad ordinaria.

## Familia BMA

### M0 — secuencial ordinario

Modelo v0.6.4 eficiente, con nivel, rezago, brecha temporal, composición transversal y codificación armónica básica. Es el control adaptativo; no se elimina.

### M1 — estacional armónico

Añade dos armónicos anuales:

\[
s_m=a_1\sin(2\pi m/12)+b_1\cos(2\pi m/12)+a_2\sin(4\pi m/12)+b_2\cos(4\pi m/12).
\]

El primer armónico aprende fase anual amplia; el segundo permite dos máximos/mínimos sin doce parámetros libres.

### M2 — armónico más residuo mensual jerárquico

Añade un efecto cíclico mensual de suma cero para perturbaciones no suaves —por ejemplo agosto o diciembre— con contracción parcial:

`global -> flujo -> CN4 -> socio -> celda sólo con soporte suficiente`.

Una celda escasa hereda señal de niveles superiores. No se estimarán doce efectos libres por celda sin soporte.

## Combinación y actualización

Participación, cantidad y valor mantendrán pesos BMA separados. Los pesos de `M0`, `M1` y `M2` se actualizarán mediante log-score prequential sólo después de adjudicar el objetivo. Un modelo estacional debe ganar autoridad predictiva; no la recibe por diseño.

Secuencia para cada objetivo:

1. cargar únicamente el posterior sellado del mes anterior;
2. construir `freeze` conjunto de M0/M1/M2 y sus pesos;
3. abrir el mes objetivo;
4. adjudicar modelos y mezcla;
5. actualizar estados estacionales con la innovación observada;
6. emitir `Z_post` future-only;
7. transferir el posterior al mes siguiente.

Para febrero de 2023, la memoria de febrero sólo puede contener febrero de 2022 y el pooling jerárquico permitido. Nunca puede usar marzo–diciembre de 2023 ni 2024.

## Papel de cada año

- 2022: primera exposición; estima la firma y debe permanecer fuertemente contraída.
- 2023: primera prueba causal de recurrencia del mismo mes calendario.
- 2024: segunda repetición retrospectiva y comparación contra la campaña basal v0.6.4.

La campaña no será un holdout prospectivo: su arquitectura se decidió después de observar resultados de 2024. Toda conclusión conservará jurisdicción de desarrollo retrospectivo.

## Métricas primarias

- Participación: Brier y log-loss; skill de la mezcla frente a M0 y control congelado.
- Cantidad/valor: MALE y log-score predictivo; skill frente a M0 y persistencia.
- Calibración: cobertura y anchura de intervalos por mes calendario.
- Estabilidad: fase, amplitud y signo del componente estacional entre 2022→2023 y 2023→2024.
- Localidad: resultados por flujo, CN4 y socio, con soporte efectivo explícito.

No se usarán toneladas o euros absolutos interanuales como evidencia primaria. Se compararán pérdidas, innovaciones normalizadas, log-ratios y skill dentro de la misma fase mensual.

## Gates

- `SEASONAL_INFORMATIVE`: mejora prequential material frente a M0 con soporte suficiente.
- `SEASONAL_STABLE`: fase/amplitud compatibles en dos recurrencias anuales.
- `LOCAL_ONLY`: señal válida sólo en una jerarquía declarada.
- `ABSTAIN_LOW_SUPPORT`: soporte insuficiente.
- `ABSTAIN_UNSTABLE_PHASE`: signo o fase no replican.
- `YEAR_END_UNCALIBRATED`: diciembre continúa separado hasta disponer de repetición suficiente.
- `NO_PROMOTION`: ninguna mejora retrospectiva autoriza producción o afirmación prospectiva.

Los umbrales numéricos deben congelarse antes de abrir 2022. Este documento no los inventa después de ver resultados.

## Cómputo y custodia

- Precálculo transversal O(n) por mes y variable, con equivalencia decisional respecto de v0.6.4.
- Caché únicamente de derivados estructurados; archivos AEAT crudos permanecen en memoria y no se persisten.
- Checkpoint inmutable después de cada `Z_post`, con reanudación hash-verificada.
- Manifiesto final, recibo y auditor independiente de cronología/hash.

## Decisión de continuidad

Después de 2024 se decidirá si añadir 2021 o detener la jurisdicción mensual. Añadir otro año sólo se justifica si cambia una decisión crítica: identificación de recurrencia, estabilidad por jerarquía, calibración de diciembre o discriminación entre subentrenamiento y estacionalidad.

El candidato europeo diario permanece prioritario porque una unidad de tiempo menor conserva más información y reduce la confusión por promedios mensuales. La campaña 2022–2024 sirve para explotar científicamente esta fuente mensual, no para sustituir la búsqueda diaria.
