# Bayesian Markets — checkpoint de recuperación, deduplicación y precedencia

Fecha: 2026-08-22

Estado: `MATERIAL_CUSTODY_IMPROVEMENT_NOT_EXHAUSTIVE`

## Resultado sustantivo

El proyecto queda mejor posicionado que en el checkpoint anterior porque cuatro
capas que estaban confundidas o incompletas ya pueden separarse: censo lógico,
bytes físicos, miembros de contenedores y fuentes conversacionales nativas.
Esto no añade una victoria predictiva ni reescribe una campaña; reduce el riesgo
de omitir, duplicar o reclasificar evidencia por el nombre de su carpeta.

## Censo local y deduplicación

Se recuperaron los cuatro artefactos del censo local V2 que el checkpoint
histórico citaba pero que faltaban en el repositorio canónico. Sus hashes
coinciden con las copias de sucesión:

- CSV: 1.544 entradas, SHA-256
  `9FC5CE7AEE8C4170F6E74016A586077F0D18FB717293717497026250377E5F2E`;
- JSON: SHA-256
  `9DB2DC01F801DBF80411ECB74D581D9DF4FC507A371A002B922477ED0FB49273`;
- errores: SHA-256
  `90B8103B64D54B9DE0AD7111BE94AB216BEE9F90AFD8681DC1CDDAA9DACEC9E2`;
- generador: SHA-256
  `41BEE575ECAE6D271464DC078D08EA77613D95BB7ACA359AD7F3602B17B6C217`.

La deduplicación V3 hasheó 1.506 archivos presentes y resolvió una entrada
histórica mediante un recibo de eliminación verificable. El resultado contiene
829 objetos SHA-256 únicos, 295 grupos de duplicados y 677 copias físicas
redundantes. Los 193.772.331 bytes presentes se reducen a 162.611.268 bytes
únicos lógicos. Esto es una medida de redundancia, no autoridad para borrar.

El ZIP ausente `bma-v065-b732c53.zip` no es pérdida científica: su recibo declara
la eliminación por falta de espacio y el superviviente conserva tamaño
131.996.730 y SHA-256
`34B8864FE7D6D1D39C076C5CEFB3702D992D43EC4A08A6812A645AB7657AF9B7`.
No se recreó la ruta eliminada.

## Contenedores

Diez contenedores únicos fueron inspeccionados sin extracción insegura. La
lectura produjo 613 miembros, 547 miembros de archivo y 484 hashes de miembro
únicos, con cero errores. El RAR en cuarentena se leyó por streaming y en
memoria, sin materializar rutas de archivo; contiene código, freezes,
adjudicaciones, priors, observaciones estructuradas, `Z_post`, resúmenes y
pruebas. Esto elimina el bloqueo técnico de contenido, pero no promueve por sí
solo la validez científica de esa ejecución.

El documento `Statistical Programming and BayME-EVE` aparece en Markdown, DOCX
y PDF. Los tres hashes son distintos porque son representaciones distintas. El
DOCX no contiene caracteres Unicode de sustitución; la aparente corrupción fue
un defecto de visualización de consola. El PDF contiene texto extraíble en sus
28 páginas. La adjudicación semántica es una sola unidad
`hbp-economic-political-core`: constitución y software alpha, no una nueva
unidad BPM o BUM ni validación del sistema completo. El gate visual permanece
`NOT_PASSED_VIEWER_ACL_BLOCKED`.

## Registro nativo V5

El registro V5 contiene 16 conversaciones nativas únicas. Quince aparecen en la
ventana reciente del proyecto y `Sistematización de fronteras` completa la
fuente histórica adicional ya conocida. Cinco conversaciones que no estaban en
V4 quedaron incorporadas:

- `Cosecha Bayes diaria`;
- `BayME bayesian macroeconomics agosto zarpadinguins`;
- `Arg.Bayme`;
- `BayME BSM Sep adjudica`;
- `Auditoría Library BayME`.

La lectura llega a EOF en todos los casos. Dos fuentes conservan límites de
transporte: PULSO tiene al menos dos ítems mayores que el máximo nativo y la
conversación macro tiene cuatro ítems truncados a 20.000 caracteres. El estado
correcto es `EOF_REACHED_WITH_TRANSPORT_TRUNCATION`, no lectura íntegra fingida.
Mondragón no aparece entre las 16 fuentes conocidas ni en los nombres del censo
local y permanece `NOT_YET_RECOVERED`.

## Precedencia BPM / BUM / HBP

La definición persistida gobierna sobre expansiones derivadas contradictorias:

- BPM = Bayesian Physics Markets;
- BUM = Bayesian Unreal Markets;
- HBP = Hierarchical Bayes Predictor.

BMA queda subsumido en BPM; BayME, BayME Pulse y BayME EVE son linajes
históricos. Una respuesta nativa que expandía las siglas como mecanismos o
procesos distintos queda clasificada como error derivado del asistente, porque
contradice los README y checkpoints específicos persistidos después de la
corrección Whisper.

## Argentina, Eurostat y expansión coral

La instrucción de integrar Argentina y Eurostat después de AEAT ya está
materialmente cumplida en el repositorio al 21 de agosto. El ledger mantiene
separados crédito, M3, IPC, UCII, IPI y RC15; la interfaz coral comparte estados
de evidencia, no likelihoods, posteriores, scores ni autoridad global.

También se ejecutaron los probes mínimos de Eurostat STS, Puertos, TED y
Comtrade. STS es utilizable con captura de cada vintage provisional; Puertos es
observador físico mensual sin precio; TED sólo admite recuento de eventos por
ahora; Comtrade falló el gate por filas agregadas/estimadas con cantidades
cero. RMK avanzó después hasta una campaña BPM causal cerrada. Estos resultados
adversos y parciales no deben repetirse ni promoverse.

## Incertidumbre, reparabilidad y siguiente acción

La cobertura sigue sin ser exhaustiva: faltan Mondragón, los bytes de varios
payloads de Library de Argentina/RC15, el contenido completo de seis ítems
nativos truncados y una inspección visual de las representaciones paginadas.
Ninguna de esas brechas se repara inventando contenido o reinterpretando hashes.

La siguiente acción crítica es transferir sólo estos artefactos validados al
repositorio canónico, ejecutar el auditor de integración y las pruebas, y
publicarlos en la rama sucesora sin tocar los trabajos AEAT no confirmados ni la
rama remota divergente. Después corresponde continuar la recuperación puntual
de Mondragón y de payloads originales; no repetir Argentina–Eurostat ni buscar
una métrica coral global.
