# Checkpoint sustantivo: congelación plurianual Luke antes de la historia

Fecha: 2026-08-22  
Estado: `FROZEN_SOFTWARE_AND_PROTOCOL_AWAITING_PUBLIC_CUSTODY`

## Resultado en plata

La campaña finlandesa de madera ya tiene un protocolo ejecutable completo y
verificado, pero todavía no ha abierto los 158 valores históricos. El diseño
separará volumen físico y precio nominal, y hará 78 predicciones consecutivas:
cada mes sólo podrá predecir el siguiente. El posterior, los pesos y `Z_post`
continuarán de un año al otro sin reinicios.

El año 2020 será el bootstrap: M1 y M2 aprenderán sus estados estacionales en
sombra, pero emitirán la misma predicción que M0. Desde enero de 2021 podrán
emitir sus propias predicciones. Esto evita atribuir estacionalidad antes de
haber observado un primer año calendario y, al mismo tiempo, no descarta la
información de entrenamiento necesaria para los años siguientes.

## Qué quedó congelado

La jurisdicción es exactamente Finlandia completa, ventas en pie, troncos de
abeto, frecuencia mensual. Hay dos targets independientes:

- volumen de compras, convertido de miles de m³ a m³ y modelado con `log1p`;
- precio nominal en EUR/m³, modelado en logaritmos.

M0 usa intercepto e innovación previa; M1 añade dos armónicos anuales; M2 añade
a M1 once contrastes mensuales de suma cero con shrinkage. Priors, precisiones,
pesos iniciales, actualización por log-score, piso numérico, transforms,
soporte, orden del cubo, recuperación y árbol de artefactos quedaron fijados en
el preregistro y su addendum.

La adquisición autorizada es un único POST PXWeb, sin GET adicional, sobre 79
meses consecutivos y dos indicadores: 158 celdas como máximo. Cualquier celda
ausente produce `NOT_ESTIMABLE_INCOMPLETE_PANEL`. Cualquier bandera fuente no
vacía que aún no tenga interpretación preregistrada produce
`NOT_ESTIMABLE_UNINTERPRETED_SOURCE_STATUS`. En ambos casos no hay fit,
forecast, posterior ni `Z_post`.

## Evidencia de software

Doce ensayos pasan. Cubren las invariantes matemáticas, la cronología mensual,
la ausencia de resets, la separación de targets, la cuarentena de julio de
2026, la portabilidad de rutas largas en Windows y tres terminales completos:
panel denso, panel incompleto y panel con bandera no interpretada. La corrida
sintética integral genera 79 meses, 78 transiciones y 713 artefactos antes del
manifest. Es sólo evidencia mecánica del software; no es evidencia científica
de mercado.

El primer ensayo integral encontró y permitió reparar antes del freeze una
falla real de rutas profundas en Windows. La corrección usa el namespace de
ruta extendida sin cambiar nombres relativos ni custodia. Ningún dato remoto se
abrió durante esa reparación.

## Fronteras científicas

La historia de Luke disponible hoy es una serie corriente y revisable, no una
colección de vintages de primera publicación. Por eso las 78 transiciones serán
un replay prequential retrospectivo y no recibirán autoridad de forecast
histórico prospectivo. La única freeze que puede adquirir autoridad prospectiva
real es agosto de 2026, porque ese target no aparece en la captura y no ha sido
abierto.

La celda julio de 2026 ya fue vista en la sonda anterior. Se excluye de pesos y
agregados de score; sus parámetros pueden actualizarse únicamente para
construir la freeze futura de agosto. Los resúmenes por año y mes calendario son
diagnósticos. No existe ganador global, pooling entre targets o jurisdicciones,
ni promoción automática.

## Consecuencia para BPM, HBP y BIND

Para BPM, el salto es de una sonda de dos valores a un experimento plurianual
reproducible sobre un producto físico homogéneo. Para HBP, aporta una nueva
cadena mensual con memoria estacional pero aún no integra Argentina ni
Eurostat. Para BIND, mejora la demostrabilidad técnica de un caso industrial
europeo, pero no valida precisión, utilidad humana, piloto ni readiness
comercial.

## Siguiente acción crítica

Encadenar este freeze como V8, pasar auditor y suite completa, commitear y
empujar la rama pública. Sólo después se autoriza el único POST histórico y la
corrida. Terminada Luke, se integrarán cabalmente Argentina y Eurostat bajo sus
jurisdicciones propias, y se buscarán nuevas fuentes complementarias antes de
diseñar una síntesis coral tipada sin pooling N→1.

