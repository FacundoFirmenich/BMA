# Integración cabal de Argentina y Eurostat en HBP

Fecha: 2026-08-21

## Resultado sustantivo

HBP queda mejor posicionado porque Argentina y Eurostat ya no son sólo nombres
en el censo: cada campaña tiene target, corte causal, resultado, freeze futuro,
estado científico, custodia y autoridad local explícitos. La integración es
coral en sentido riguroso: una máquina de estados y un grafo de evidencias
comunes, nunca un pooling de likelihoods, posteriors o scores.

## Argentina

En julio de 2026 se observaron crédito +1.2%, M3 privado -0.1% e IPC nacional
+2.1%. Coupled-NIG obtuvo el mejor log score local en los tres targets
(-1.685668, -1.509923 y -0.935759), mientras el menor error puntual perteneció
a AR1 para crédito (0.367651) y a la mezcla para M3 (0.000462) e inflación
(0.029298). Las doce densidades congeladas cubrieron sus outcomes en los
intervalos centrales 50/80/90; la probabilidad bilateral mínima fue 0.692589,
sin eventos Z0.25/Z5.25. Esto demuestra complementariedad local entre calidad
de densidad y precisión puntual; no un ganador de variable ni de campaña.

El freeze de agosto conserva SHA-256
`4c65849b5001cb6b00cabb810472f5978c6c1418f3caa0b805066e79cab981ac`.
Los pesos Coupled-NIG futuros se actualizaron localmente de 0.537448 a 0.542022
en crédito, de 0.579368 a 0.579053 en M3 y de 0.644211 a 0.647420 en IPC.
Falta recuperar los bytes locales; por ello la cronología nativa y los hashes
dan autoridad documental, no custodia byte-completa.

UCII e IPI se separan. UCII observó 59.1% en junio y sus diagnósticos históricos
fueron z=-0.353230, PIT=0.362960 y cola bilateral=0.725921. Sin embargo, el
update gamma residual seguido de refit reutilizó evidencia: bajo la semántica
corregida de Z_post, el freeze local de septiembre se preserva como historia
pero no gobierna aprendizaje futuro. IPI continúa como freeze prospectivo
independiente e inmutable; sin su payload no se reconstruyen outcomes ni scores.

## Eurostat

RC15 cubre históricamente 198 meses, 27 países, 351 aristas y 69.498 contrastes
arista-mes. La autoridad histórica local fue: 83 joint, 4 independent, 121 both
y 143 abstenciones. Para agosto de 2026 el freeze declaró 130 joint, 15
independent, 155 both y 51 abstenciones. Las marginales nacionales son idénticas
por construcción; por tanto no existe un ganador-país.

Julio de 2026 conserva sólo el agregado EU27_2020=3.0 y 0/27 outcomes nacionales.
El panel es `NOT_ESTIMABLE_INCOMPLETE_PANEL`: no se adjudica, no actualiza el
posterior y no se reemplaza por estimaciones. El registro prospectivo conserva
SHA-256 `aba8ab5625441982ac2ae164232201f191ab583b690958aae8b9e2e82c02cc0e`;
los bytes locales siguen sin recuperarse.

## Significado y límites

El salto cualitativo es arquitectónico: campañas heterogéneas pueden convivir
sin falsificar comparabilidad. El salto cuantitativo ya disponible es local:
Argentina aporta scoring multivariable y Eurostat miles de contrastes por
arista. Ninguno autoriza una métrica agregada ni promoción automática.

Los defectos son reparables de forma desigual. La custodia se repara recuperando
payloads originales y verificando hashes. IPI se completa cuando aparezcan freeze
y outcome. Eurostat julio sólo se vuelve estimable con el panel oficial completo.
UCII no se arregla reinterpretando el freeze antiguo: requiere una nueva cadena
preregistrada que aplique Z_post una sola vez.

## Consecuencia para BPM/BUM/HBP y siguiente acción

HBP gana una columna vertebral coral explícita; BPM y BUM no absorben estas
campañas ni sus resultados. La siguiente acción crítica es cribar fuentes
oficiales abiertas que añadan resolución industrial o territorial real y
preregistrar probes mínimos antes de descargar volúmenes, crear cuentas o
atribuir autoridad científica.
