# Argentina + Eurostat — primera ejecución causal y gate adverso UCII

## Posición

El proyecto queda mejor posicionado, aunque no uniformemente. IPI ya tiene un
forecast prospectivo reproducible; Eurostat conserva una ausencia honesta;
UCII abrió una serie suficientemente larga pero su primera especificación fue
detenida por un gate demasiado amplio antes de aprender.

## Resultados locales

**INDEC IPI desestacionalizado, julio 2026.** M0: 119,0982, intervalo 90%
[111,6820; 127,0068]. M1: 118,9832, [111,5479; 126,9140]. Los pesos siguen
0,5/0,5 y no hay preferencia previa al outcome.

**Eurostat STS España manufactura, julio 2026.** La consulta exacta devolvió
`OUTCOME_PENDING`. No se calculó score, no se actualizó posterior y no se
congeló agosto.

**INDEC UCII.** El workbook oficial contiene 126 meses y 13 series: nivel
general más doce bloques. Julio está ausente. V0.1 no produjo forecast: abril
de 2020 contiene 0,0% en tabaco y automotriz, contradiciendo su gate de soporte
estricto para todos los bloques. El nivel general sí permanece entre 42,0% y
69,6% y reconcilia junio en 59,1%.

## Significado y reparación

La pérdida UCII es útil: demuestra que un observador sectorial puede tocar la
frontera sin invalidar el target general. V0.2 debe corregir sólo esa frontera,
manteniendo los sectores fuera de la likelihood y preservando los dos ceros.
No se permite reetiquetar V0.1 como éxito.

Los tres manifiestos ejecutados contienen 4, 3 y 3 archivos respectivamente,
con cero fallos de hash o tamaño. La suite completa pasa 119 pruebas.

## Consecuencia coral

Argentina aporta ahora dos objetos separados: producción desestacionalizada y
capacidad acotada; Eurostat aporta producción armonizada pero todavía sin
outcome de julio. La coral gana cobertura y contraste de estados, no una
medición agregada ni un ganador.

## Próxima acción

Custodiar V11, preregistrar públicamente UCII V0.2, ejecutar su freeze sin abrir
julio y luego iniciar la criba de nuevas fuentes oficiales.
