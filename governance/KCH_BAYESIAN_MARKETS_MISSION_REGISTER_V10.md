# Registro de misión KCH — Bayesian Markets V10

Estado: `ARGENTINA_EUROSTAT_ACTIVATION_FROZEN_BEFORE_NEW_TARGET_QUERIES`.

## Objetivo rector

Convertir la integración documental Argentina/Eurostat en cadenas locales
ejecutables, sin absorber jurisdicciones, sin reconstruir freezes históricos y
sin crear un ganador global. Después de ejecutar estos gates, ampliar la coral
con nuevas fuentes oficiales que añadan producto físico, cantidad, precio o
producción industrial estricta.

## Cambio material respecto de V9

La freeze Eurostat España NACE C de julio de 2026 fue verificada byte por byte:
los cinco archivos coinciden con su manifiesto y el target continúa sin haber
sido solicitado por esta campaña. Queda preregistrada una única consulta a
julio. Si el valor no está publicado, el resultado será `OUTCOME_PENDING` sin
score, sin posterior nuevo y sin freeze de agosto.

El XLS oficial INDEC IPI dejó de ser un bloqueo de formato. Un lector BIFF8
aislado y fijado en `xlrd==2.0.2` recupera 126 meses contiguos desde 2016-01
hasta 2026-06. Junio reconcilia exactamente por redondeo con el PDF oficial:
119,9 original y 119,1 desestacionalizado. Se congela una cadena separada para
el índice general desestacionalizado de julio; no se añade estacionalidad a una
serie que ya está ajustada estacionalmente.

UCII permanece separado de IPI. Su próxima descarga está limitada a una captura
de esquema con magnitudes numéricas ocultas; ajustar o pronosticar exige un
segundo preregistro. El freeze UCII legado con doble conteo sigue preservado
pero no gobierna esta cadena nueva.

## Autoridad y límites

1. IPI julio es prospectivo respecto del target, pero el diseño ya vio la
   historia hasta junio y no se presenta como holdout de selección ciego.
2. Eurostat julio sólo podrá aprender una vez si aparece un valor positivo y
   utilizable en la consulta exacta.
3. IPI, UCII y Eurostat STS no comparten likelihood, posterior, pesos ni
   `Z_post`.
4. Prodcom España × 16101035 × 2024 conserva `NOT_ESTIMABLE_NO_CELL`.
5. Gas, electricidad y precios administrados continúan excluidos.
6. No hay pooling N→1, ganador global ni promoción automática.

## Siguiente acción crítica

Publicar esta freeze V10. Después ejecutar, una sola vez, la freeze IPI local,
la consulta de outcome Eurostat y la captura de esquema UCII; adjudicar cada
resultado según su estado real antes de abrir nuevas fuentes.
