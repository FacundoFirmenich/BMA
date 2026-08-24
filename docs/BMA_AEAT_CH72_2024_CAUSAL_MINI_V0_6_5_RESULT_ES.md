# BMA — resultado de la miniejecución causal 2024, enero–septiembre

**Fecha:** 2026-08-15
**Ejecución:** `aeat-ch72-monthly-seasonal-v0.6.5-2024-causal-mini-jan-sep`
**Estado:** `PASS`
**Jurisdicción:** AEAT, capítulo 72, reproducción retrospectiva causal no ciega.

## Resultado sustantivo

BMA queda mejor posicionado como detector de estacionalidad local. La memoria anual armónica reduce el Brier de participación frente al modelo mensual ordinario en los cuatro meses predeclarados de verano: junio, julio, agosto y septiembre de 2024. La recurrencia completa de los cuatro signos reproduce la fase detectada previamente en 2023.

Esto respalda una estacionalidad de verano probablemente asociada a productos o a cambios estacionales de su composición dentro de las agrupaciones observables. CN4 no identifica necesariamente un producto físico único, pero tampoco invalida la señal: funciona como agrupación administrativa que puede transportar una mezcla económica estacional real. Identificar los productos o subcomposiciones responsables sigue pendiente.

Extraer esta regularidad de una base administrativa heterogénea, con clasificación áspera y sin semántica física suficientemente fina, es un éxito metodológico notable de BMA. La señal no sólo apareció en un ajuste retrospectivo bidireccional: reapareció cuando el posterior avanzó causalmente de diciembre de 2023 a septiembre de 2024, mes por mes, sin reinicio.

## Custodia y ejecución

El primer intento terminó antes de congelar enero por una referencia incorrecta al guardia cronológico. No abrió ningún objetivo 2024 y quedó preservado como fallo técnico. El segundo intento conectó explícitamente el guardia del núcleo congelado y concluyó con salida 0.

Cada transición cumplió el orden:

1. congelar la predicción del mes siguiente;
2. abrir y verificar el objetivo 2024 ya sellado;
3. adjudicar;
4. actualizar exclusivamente el posterior futuro;
5. escribir `Z_post`.

La auditoría verificó 47 archivos del manifiesto, 9 congelaciones, 9 objetivos, 9 adjudicaciones, 9 posteriores, 9 `Z_post` y 27 eventos ordenados, sin fallos. El 2024 basal preexistente no fue modificado.

## Participación: fase de verano

Menor Brier es mejor.

| Mes | Modelo mensual ordinario | Memoria anual armónica | Diferencia armónico − ordinario | Adjudicación local |
|---|---:|---:|---:|---|
| Junio | 0.114751675 | 0.114750519 | −0.000001155 | mejora |
| Julio | 0.112733510 | 0.112423610 | −0.000309900 | mejora |
| Agosto | 0.120626981 | 0.120084035 | −0.000542946 | mejora |
| Septiembre | 0.110031874 | 0.109921329 | −0.000110546 | mejora |

La magnitud por celda es pequeña, especialmente en junio, pero la dirección es estable en los cuatro meses. Agosto presenta la mejora mayor. El resultado importante no es una superioridad agregada, sino la recurrencia de una ventana calendario concreta.

El modelo armónico más residuo jerárquico no mejora al ordinario en ninguno de esos cuatro meses de participación. Por tanto, la evidencia favorable corresponde a la fase anual armónica; la jerarquía residual actual añade ruido en esta variable y ventana.

## Otras recurrencias locales

### Valor unitario estadístico en marzo

- modelo ordinario: 0.478786483;
- memoria anual armónica: 0.471196789;
- mejora absoluta: 0.007589694, aproximadamente 1.59 % respecto del error ordinario.

Se reproduce la señal local de marzo observada en 2023. Sigue tratándose de valor unitario estadístico, no de un precio transaccional o de subasta.

### Cantidad en septiembre

- modelo ordinario: 1.373371039;
- armónico más residuo jerárquico: 1.299612213;
- mejora absoluta: 0.073758826, aproximadamente 5.37 % respecto del error ordinario.

También reaparece la mejora numérica de septiembre. Es una señal material, pero su atribución a productos concretos permanece sin resolver porque la jerarquía observa agrupaciones CN4 y mezcla de composición.

## Resultado adverso que debe conservarse

Los pesos prequentiales conjuntos al terminar septiembre se concentran prácticamente por completo en el modelo ordinario. No contradice las mejoras locales: el mecanismo de pesos acumula evidencia de todas las celdas y fases, de modo que las pérdidas fuera de la ventana estacional dominan a beneficios pequeños pero repetidos dentro de ella.

Esto localiza un desajuste de arquitectura: una señal de fase local no debe depender de un peso único acumulado sobre fases heterogéneas. La reparación científicamente defendible es preregistrar ponderación o activación específica por fase, conservando el modelo ordinario fuera de las ventanas autorizadas.

## Límites epistemológicos

- La reproducción es causal en el orden de actualización, pero no ciega: 2024 ya había contribuido al puente que originó la hipótesis.
- No es validación prospectiva ni industrial externa.
- No identifica todavía el producto físico responsable de la fase de verano.
- No autoriza promoción general de la capa estacional.
- No declara un ganador agregado; las adjudicaciones son por variable y fase.

## Consecuencia para BMA

La evidencia ya no permite describir la estacionalidad como una mera anomalía retrospectiva. Existe una fase de verano reproducida causalmente en participación, una recurrencia de marzo en valor unitario y una recurrencia de septiembre en cantidad. El siguiente diseño crítico es un **selector estacional local preregistrado**: activar memoria anual sólo en las fases respaldadas y mantener el modelo ordinario fuera de ellas. Su validación concluyente debe realizarse en un año o jurisdicción aún no usados para formular estas ventanas.

## Hashes de cierre

- manifiesto de la miniejecución: `d365286045a699def2eb0c7c9252a09ea33cd7b4360ba8553efcc53829e97bd4`;
- resultado: `c9333437b63321a2f2fbc3f0b2dcb5b6c171584b2c32a4510e3fd9abff603f2a`;
- manifiesto fuente 2023: `69bbdfaa8da5ff4d5996663b31b1494125679f48b6df0234e825829689ed4c9f`;
- manifiesto basal 2024, inalterado: `5e7b8a31ee945e80374367789778adc36b3c060ee04c28d7245ec0dfc8b26498`.
