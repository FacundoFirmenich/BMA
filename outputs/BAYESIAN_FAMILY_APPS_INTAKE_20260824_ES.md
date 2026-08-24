# BayesianFamilyApps — ingreso local, autoridad y evidencia

Fecha: 2026-08-24
Estado: `PASS_INTAKE_CLASSIFIED_NO_MODEL_UPDATE`

## Resultado sustantivo

El proyecto está mejor posicionado documentalmente y con evidencia nueva, pero
no tiene todavía una nueva victoria, pérdida ni actualización bayesiana
autorizada. Se localizaron exactamente 25 archivos creados o modificados dentro
de la ventana inicial de treinta minutos en
`C:\Users\User\3D Objects\{Kwan&Learning}`. Su contenido confirma que
pertenecen al universo BayesianFamilyApps/BayME/BMA/BIND; la declaración del
usuario completa esa atribución. Ninguno conserva `Zone.Identifier`, por lo
que no afirmo como hecho forense independiente qué navegador o chat produjo
cada descarga.

Se leyeron todos los bytes de los 25 originales y de 290 archivos extraídos,
incluidos ZIP anidados: 315 archivos y 19.965.044 bytes. No hubo traversal,
exceso de tamaño, error UTF-8 ni JSON inválido. Los nueve hashes declarados por
el paquete de transferencia BayME coinciden.

## Qué se incorpora y qué no se mezcla

### Autoridad nominal actual

Los documentos más recientes y explícitamente correctivos son el canon v0.6 y
el sync v5. Fijan:

- BUM = Bayesian Un Markets;
- BPM = Bayesian Physical Markets;
- HBP = Hierarchical Bayes Predictor;
- relación autorizada actual: `BayME~BMA → {BUM, BPM, HBP}`.

Los significados anteriores —Bayesian Updating Mechanism, Bayesian Predictive
Model y Hierarchical Bayesian Process— se conservan como historia, pero quedan
superados nominalmente. La jerarquía interna entre BUM, BPM y HBP no se inventa:
permanece `PENDING_PRIMARY_RECONCILIATION`.

También se preserva la regla científica del canon: lo local es obligatorio; una
comparación global sólo puede existir como último recurso hostil,
prerregistrado, y no crea un ganador global.

### Andalucía IDAPES

Los 16 pares `READ_1/READ_2` son byte-estables. Hay evidencia positiva en
Barbate, Cádiz, Huelva y Punta Umbría; doce mercados permanecen
`PENDING_EMPTY_NOT_ZERO`, no cero. Se observan ocho celdas especie: CTC=3,
PAC=3 y MUR=2; OCC=0 y MUT=0.

Esto es un éxito de extracción y custodia local, no todavía un resultado
predictivo. Faltan los bytes de las densidades numéricas congeladas el
2026-08-12: el hash maestro está verificado, pero Library respondió HTTP 502.
Sin esas densidades no corresponde calcular score, posterior ni `Z_post`.

### Eurostat HICP

El payload oficial `prc_hicp_fpd` contiene EU27, julio de 2026, release
`FIN`, valor 3,0. La normalización reproduce exactamente la celda raw y el hash
raw declarado coincide. Es evidencia oficial para esa cadena HICP; no es
autoridad para IPI, UCII, STS, Luke ni AEAT. Antes de adjudicar hay que localizar
y emparejar la freeze prerregistrada de esa cadena.

### BIND

El índice, checklist, control master y delta log son custodia de producto y
candidatura. Mejoran trazabilidad y preparación documental, pero no son inputs
del posterior científico ni prueban validación industrial o comercial.

## QA de los documentos BayME

Se leyó completamente el texto de ambos DOCX y ambos PDF. El marco tiene 102
páginas; Producto, Utilidad y Operación tiene 15. Las 117 páginas PDF fueron
renderizadas e inspeccionadas y no muestran truncamientos, páginas indebidamente
vacías, tablas cortadas ni desbordes visibles.

La similitud textual DOCX↔PDF es alta (Dice multiconjunto de tokens 0,918 y
0,955), pero no perfecta. LibreOffice no está instalado, de modo que no hubo
render visual directo de los DOCX. Por eso la conclusión correcta es que los PDF
son especificaciones visualmente coherentes, no que DOCX y PDF sean visualmente
idénticos.

Los documentos de julio son especificaciones extensas, no prueba de que todo el
sistema global descrito haya sido ejecutado o validado. Las secciones nominales
y de globalidad incompatibles con v0.6/v5 no se promocionan sin errata.

## Drive

La carpeta `15b_6OmGGlPBuNhIDz3mMFerK4DUhO_kt` fue renombrada y releída como:

`BayesianFamilyApps_BUM_BPM_HBP — BayME_BMA_BIND — Corpus canónico y Data Room 2026`

Conserva el mismo ID, padre y permisos owner-only. No fue movida ni compartida.

## Evidencia adversa y límites

La persistencia remota de Andalucía falló en 13/13 intentos para freeze y 18/18
para harvest; la carpeta remota quedó vacía y sin commit parcial. Ese fallo se
preserva: los originales locales siguen siendo la autoridad disponible.

No se copiaron los ZIP crudos al historial Git, porque duplicar 8,7 MB de
evidencia sin contrato de almacenamiento no aumenta autoridad y sí mezcla
custodia con código. El manifiesto fija ruta, tamaño y SHA-256 de cada original.
No se borró ni movió ningún archivo local.

## Consecuencia para BayME, BMA y BIND

BayME gana una cartografía nominal corregida y dos unidades de evidencia
recuperadas. BMA no cambia todavía sus posteriors: Andalucía está bloqueada por
densidades faltantes y HICP por el emparejamiento con su freeze. BIND mejora su
data room y trazabilidad, no su validación comercial.

La siguiente acción crítica es doble y local: localizar/hash-emparejar la freeze
HICP EU27 y recuperar las densidades congeladas de Andalucía. Cada cadena se
adjudicará una sola vez y por separado; no habrá pooling global, reseteo de
posteriores ni condensación de múltiples períodos sobre un único target.
