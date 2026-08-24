# Invariante de resolución temporal e información — BMA

Estado: `CANONICAL_DESIGN_CONSTRAINT`  
Fecha: 2026-08-09

## Regla primaria

BMA opera en la menor unidad temporal computable que preserve observaciones no
promediadas. La unidad no se elige por comodidad del archivo ni por reducir
volumen computacional.

Orden de preferencia:

1. evento individual con timestamp nativo;
2. minuto, si es la resolución real más fina;
3. hora, si no existe resolución inferior verificable;
4. día, si la fuente solo conserva fecha;
5. escalas superiores únicamente como vistas derivadas o cuando la fuente no
   permite legítimamente más resolución.

No se inventan subperiodos. Si una fuente contiene día pero no hora, el día es
su máxima resolución temporal identificable.

## Conservación de raws y unidad del modelo

La coordenada temporal y la observación no son lo mismo. En AEAT, la coordenada
más fina es el día, pero dentro de cada día existen múltiples líneas de
declaración. BMA debe conservar cada línea normalizada como evento marcado y
modelar la distribución diaria de conteo, participación, masa, valor y
heterogeneidad. Un promedio diario no sustituye a esos eventos.

Semana, mes, trimestre y año se construyen desde eventos y adjudicaciones
atómicas preservadas. Nunca se usan para borrar la escala inferior.

## Pérdida de información

Una agregación determinista muchos-a-uno no puede aumentar la información sobre
un estado latente. En general elimina:

- orden y tiempos de llegada;
- dispersión y multimodalidad;
- colas, extremos y asimetría;
- estructura de ceros y conteos;
- covarianzas entre marcas;
- cambios de régimen dentro del periodo;
- identificabilidad de mecanismos distintos con la misma media.

La pérdida se vuelve irreversible cuando los raws dejan de estar disponibles o
cuando el mapeo agregado no es invertible. Un agregado no queda invalidado ex
ante para todo propósito: puede ser suficiente para un parámetro y una familia
probabilística concretos. Esa suficiencia debe demostrarse; nunca presumirse.

Por defecto, escalas más gruesas son capas de contexto y adjudicación
multirresolución, no reemplazos del proceso atómico.

## Invariante de reinformación

`unidad de entrenamiento = unidad de predicción = unidad de adjudicación = unidad de Z_post`

Un bloque de N unidades atómicas de entrenamiento se contrasta con N unidades
atómicas objetivo. Cada outcome se añade una sola vez, en la misma
representación, y solo puede reinformar predicciones futuras. La acumulación no
autoriza promediar unidades incompatibles ni usar la sección transversal como
profundidad temporal.

## Consecuencia para AEAT

- Resolución económica máxima verificable: día.
- Observación preservable: línea individual de declaración.
- Archivo de transporte: lote mensual.
- Capacidad: replay diario retrospectivo con eventos preservados.
- Incapacidad actual: operación day-ahead real, porque la disponibilidad pública
  observada es mensual.

La vista `celda × día` puede utilizarse para resúmenes y scores derivados, pero
el corpus canónico conserva los eventos individuales y su linaje.
