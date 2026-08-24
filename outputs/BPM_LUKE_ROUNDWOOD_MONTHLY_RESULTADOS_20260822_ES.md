# Resultados sustantivos: Luke Finlandia, troncos de abeto en venta en pie

Fecha: 2026-08-22  
Estado: `RETROSPECTIVE_REPLAY_COMPLETE_PROSPECTIVE_2026_08_FROZEN`

## Resultado en plata

La campaña encontró estacionalidad útil y físicamente interpretable dentro de
una jurisdicción de producto real: Finlandia completa, ventas en pie, troncos de
abeto. No depende de una agrupación administrativa desconocida. El patrón más
claro es un ciclo de volumen de primavera-verano y un ciclo de precio asociado:
el volumen aumenta fuertemente en abril-mayo, cae todos los julios observados y
rebota en agosto-septiembre; el precio sube de febrero a junio y tiende a bajar
de julio a octubre.

La memoria estacional no ayuda igual desde el comienzo. En 2021-2022 sus
resultados son débiles o mixtos. Desde 2023 mejora simultáneamente log-score y
error en ambos targets con mucha mayor regularidad. Esta dependencia de la edad
de entrenamiento es un hallazgo relevante para la futura investigación general,
pero no la sustituye: aquí sólo hay una cadena, una jurisdicción y 6-7 réplicas
por fase calendario.

## Integridad y cronología

La captura pública devolvió HTTP 200, 158 celdas densas, cero faltantes y cero
banderas. Su SHA-256 es
`1A04973327255BF1D04A5315751C74C8DE2AF9583E6131991D62CAA90330B0BD`.
No hubo GET de metadatos ni segundo POST.

La corrida produjo y verificó 713 artefactos más el manifest:

- 79 meses estructurados, de 2020-01 a 2026-07;
- 78 transiciones mensuales;
- 156 freezes, adjudicaciones, priors gzip y `Z_post`;
- 22 freezes bootstrap durante febrero-diciembre de 2020;
- siete checkpoints anuales sin reset;
- exactamente dos `Z_post` sin actualización de pesos: volumen y precio de
  julio de 2026, ya abiertos en la sonda V7;
- una freeze prospectiva de agosto de 2026, ausente de la captura.

Los 713 hashes y tamaños coinciden. No quedó staging ni subproceso activo.

## Patrón físico observado

Los cambios son mes contra mes dentro de la serie corriente de Luke. No son
vintages históricos de primera publicación.

### Volumen

- Abril aumenta en 6/7 años; cambio log medio equivalente a `+19,87 %`.
- Mayo aumenta en 6/7; cambio medio equivalente a `+78,31 %`.
- Julio cae en 7/7; cambio medio equivalente a `−62,21 %`.
- Agosto aumenta en 6/6; cambio medio equivalente a `+39,76 %`.
- Septiembre aumenta en 5/6; cambio medio equivalente a `+28,40 %`.
- Febrero cae en 6/7 y diciembre en 4/6.

No debe interpretarse que el volumen “es bajo todo el verano”. El ciclo exacto
es más interesante: fuerte acumulación primaveral, quiebre universal en julio y
rebote en agosto-septiembre.

### Precio

- Febrero, marzo y abril aumentan en 7/7 años.
- Mayo y junio aumentan en 6/7.
- Julio baja en 6/7.
- Agosto baja en 4/6; septiembre y octubre bajan en 5/6.
- Los cambios medios son mucho menores que en volumen: máximo aproximado
  `+2,48 %` en mayo y alrededor de `−1,27 %` en julio.

Esto es coherente con un mercado donde la cantidad tiene estacionalidad física
mucho más abrupta y el precio responde con una onda más suave y persistente.
La campaña no identifica por sí sola el mecanismo causal —clima, calendario de
corta, contratación, inventarios o composición— y no debe adjudicárselo post
hoc.

## Dónde añade valor predictivo la estacionalidad

La unidad primaria es target × mes × modelo. Los conteos siguientes comparan
contra M0 y exigen simultáneamente mejor log-score y menor error absoluto.

### Volumen

- Mayo: M1 mejora en 6/7 años; M2 en 5/7.
- Julio: M1 y M2 mejoran en 5/6.
- Febrero: ambos mejoran en 5/7.
- Abril: ambos mejoran en 4/7.
- Septiembre: ambos mejoran en 4/6.
- Diciembre: M1 mejora en 4/6 y M2 en 3/6.
- Agosto es adverso: M1 y M2 mejoran en 0/6 por ambos criterios.
- Marzo también es adverso: sólo 1/7.

El gran valor de julio no significa que el modelo espere una subida: significa
que aprende mejor la caída estacional. El posterior M2 atribuye a julio una
contribución calendario media aproximada de `−24,21 %` en la innovación del
nivel, sin intervalo post-outcome autorizado.

### Precio

- Abril: M1 y M2 mejoran en 5/7.
- Marzo y mayo: ambos mejoran en 4/7.
- Julio: ambos mejoran en 4/6.
- Agosto: M1 mejora en 4/6 y M2 en 3/6.
- Septiembre: ambos mejoran en 4/6.
- Octubre: M1 mejora en 4/6 y M2 en 3/6.
- Enero, junio y diciembre son débiles o mixtos.

Aquí el armónico M1 es suficiente con frecuencia: el residuo mensual M2 reduce
algo más el error total, pero no mejora el log-score tantas veces como M1.

## Aprendizaje por edad de la cadena

2020 es idéntico por construcción: M1 y M2 emiten M0 mientras aprenden en
sombra. En volumen, 2021 mejora levemente el log-score pero empeora el error;
2022 sigue casi neutro. Desde 2023 ambos criterios se vuelven favorables, y M2
alcanza sus mayores ventajas de log-score en 2024 (`+0,1035`) y 2025
(`+0,1165`) frente a M0.

En precio, 2021 empeora el log-score y 2022 es neutro/adverso. Desde 2023 M1 y
M2 mejoran log-score y error; la mejora de M1 frente a M0 crece de `+0,0632` en
2023 a `+0,1141` en enero-junio de 2026.

La lectura correcta no es “más meses siempre ganan”. Es: en esta cadena la
estructura anual necesita aproximadamente dos años posteriores al bootstrap
para estabilizar una ventaja clara. Esto motiva una investigación preregistrada
con cadenas causales de distintas edades y fases calendario alineadas.

## Agregados diagnósticos, sin ganador global

Sobre 77 targets puntuables por variable:

- Volumen: error log absoluto medio M0 `0,330120`, M1 `0,322237`, M2
  `0,314110`, persistencia `0,331273`. M2 reduce `4,85 %` frente a M0 y
  `5,18 %` frente a persistencia. Log-score medio: M0 `−0,640865`, M1
  `−0,604134`, M2 `−0,579820`.
- Precio: error log absoluto medio M0 `0,014066`, M1 `0,011661`, M2
  `0,011563`, persistencia `0,014407`. M1 reduce `17,10 %` frente a M0;
  M2 `17,79 %`; M2 reduce `19,74 %` frente a persistencia. Log-score medio:
  M0 `2,226722`, M1 `2,273607`, M2 `2,267757`.

Estos agregados describen esta jurisdicción y este target. No seleccionan un
modelo universal, no se comparan entre volumen y precio y no se transportan a
Argentina, Eurostat, RMK o AEAT.

## Freeze prospectiva agosto de 2026

Con julio observado en `429.000 m³` y `83,14 EUR/m³`, la mezcla congelada da:

- volumen: `439.468,30 m³`, aproximadamente `+2,44 %` respecto de julio;
- precio: `82,4343 EUR/m³`, aproximadamente `−0,85 %`.

Pesos target-locales:

- volumen: M0 `0,78 %`, M1 `13,22 %`, M2 `85,99 %`;
- precio: M0 `1,63 %`, M1 `60,08 %`, M2 `38,29 %`.

Los intervalos por componente de volumen son amplios. Para M2, el 90 % es
`[218.506, 892.860] m³`; para precio M1 es `[78,878, 86,092] EUR/m³`.
La mezcla no tiene intervalo preregistrado: `NOT_ESTIMATED`. Los puntos son
localizaciones transformadas y luego invertidas, no medias aritméticas del
outcome futuro.

## Significado y reparabilidad

Para BPM, esta campaña constituye un salto cualitativo respecto de CN4, Puertos
y TED: hay producto físico, modalidad contractual, cantidad, precio, calendario
y una señal estacional local que mejora predicción en fases específicas. Para
HBP, aporta una cadena larga útil para estudiar edad de entrenamiento y memoria
estacional. Para BIND, mejora la demostrabilidad de un caso industrial europeo,
pero aún no valida utilidad humana, piloto, producción ni readiness comercial.

Las debilidades son reparables sólo prospectivamente: capturar cada nueva
publicación como vintage inmutable; puntuar agosto y meses siguientes sin
reescribir la freeze; estimar un intervalo de mezcla en una versión futura
preregistrada; y multiplicar productos/regiones antes de atribuir generalidad.

## Siguiente acción crítica

Cerrar V9 y publicar estos resultados. Inmediatamente después, integrar los
activos existentes de Argentina y Eurostat con sus unidades, calendarios y
vintages propios; luego buscar fuentes públicas adicionales de producto físico
y producción industrial estricta. La síntesis coral deberá conservar
heterogeneidad, complementariedades y abstenciones, nunca condensar todas las
jurisdicciones en un único target ni declarar ganador global.

