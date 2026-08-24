# BMA — contrato canónico de sucesión a Terra

Fecha: 2026-08-10

Estado: `FROZEN_SUCCESSION_CONTRACT`

Repositorio: `https://github.com/FacundoFirmenich/BMA`
Rama de continuidad: `agent/bma-v065-terra-succession`

Estado GitHub al cierre: `LOCAL_READY_AUTHENTICATION_BLOCKED`. La rama local
termina en el commit que contiene este documento. El push de la rama nueva no
transfirió bytes porque GitHub CLI invalidó su token. No fusionar ni forzar la
rama remota histórica `agent/bma-v061-aeat-industrial-holdout`; reautenticar
`gh`, empujar esta rama y abrir PR draft contra `main`.

## 1. Misión y configuración

Terra hereda el proyecto como investigador e ingeniero con criterio, no como
ejecutor mecánico. Debe razonar en alto para decisiones científicas,
arquitectura estacional, cambios de contrato y adjudicación. Puede bajar a
medio para ingestión, pruebas, manifests, hashing y ejecuciones ya congeladas.
Si aparece una contradicción científica o un cambio material de jurisdicción,
debe detener la apertura de outcomes y explicarlo antes de modificar el plan.

Objetivo gobernante: continuar Bayesian Markets App (BMA), aplicación de
mercados físicos de la arquitectura general BayME, dentro de la línea BIND.
BayME no se renombra. Los nombres históricos congelados tampoco se reescriben.
BMA no se reduce a Galicia, xurelo, Mercabarna, flores, madera ni AEAT: son
jurisdicciones distintas de una misma aplicación y no transfieren autoridad.

## 2. Lectura obligatoria antes de actuar

Leer en este orden, sin saltos:

1. `README.md`.
2. `docs/NAMING_AND_LINEAGE.md` y `docs/EVIDENCE_BOUNDARY.md`.
3. `docs/SOURCE_THREAD_AUDIT_ES.md` y `docs/BIND_2026_POSITION_ES.md`.
4. `docs/BMA_AEAT_MONTHLY_SEQUENTIAL_V0_6_4_RESULT_ES.md`.
5. `outputs/BMA_AEAT_V0_6_4_CIERRE_SUSTANTIVO_ES.md`.
6. `docs/BMA_SEASONAL_LEARNING_2022_2024_DESIGN_V1_ES.md`.
7. `preregistrations/AEAT_CH72_SEASONAL_2022_2024_V0_6_5.json`.
8. `docs/INDUSTRIAL_DAILY_SOURCE_CANDIDATES_V3_ES.md`.
9. `preregistrations/EU_INDUSTRIAL_DAILY_SOURCE_ACQUISITION_V0_7_0.json`.
10. `preregistrations/BMA_SUCCESSOR_PROGRAM_20260810.json`.

Después verificar, no asumir, el estado actual con:

```powershell
git status -sb
git log --oneline -8
python -m pytest -q
python -m ruff check .
python scripts/audit_aeat_monthly_sequential_v064.py `
  evidence/runs/aeat-ch72-monthly-sequential-v0.6.4
```

Los chats nativos relevantes son:

- origen BIND/BayME completo: `codex://threads/019fe4ca-9d4c-72c3-ba7e-0e82f26ede44`;
- tarea BMA que produce este relevo: `codex://threads/019fe5a4-7b88-7cb2-9515-fa70a52cf0ef`.

Si ambos están disponibles dentro del proyecto, su cronología nativa prevalece
sobre cualquier síntesis. Este documento sirve de contrato de navegación y
ejecución; no reemplaza la fuente conversacional.

## 3. Estado científico recibido

### AEAT mensual v0.6.4

La cadena 2024 correcta contiene 11 transiciones contiguas: cada mes predice
únicamente el siguiente, el outcome produce adjudicación y `Z_post`, y el
posterior se transfiere al siguiente freeze. No hay pooling retrospectivo de N
meses para predecir un único mes ni reinicio entre meses.

- Participación: Brier `0.210459` frente a control `0.505664`; 10 victorias y un
  empate mensual.
- Cantidad: MALE `1.504852` frente a persistencia `1.189449`; 0/11 victorias.
- Valor unitario estadístico: `0.525392` frente a `0.373300`; 0/11 victorias.
- Diciembre: `YEAR_END_UNCALIBRATED`.
- Clasificación: `RETROSPECTIVE_DEVELOPMENT_REPLAY`; no prospectivo, no ganador
  global y sin promoción.

La participación mejora materialmente la posición científica. Cantidad y valor
siguen siendo resultados adversos aunque la brecha disminuya; no deben
rescatarse mediante narrativa de convergencia. La trayectoria puede mezclar
subentrenamiento, composición y estacionalidad.

### Evidencia diaria e industrial

No hay aún una fuente diaria industrial europea autorizada para entrenar.
TBAuctions/ATLAS es el candidato principal de eventos post-subasta; requiere
cuenta, muestra y prueba de alcance. EquipmentWatch es alternativa sólo si
demuestra cobertura europea y derechos. Gas, electricidad y precios regulados
o administrados están excluidos. La madera sigue incluida, sin sustituir la
prioridad de producción industrial estrictamente no biológica.

### Cuarentenas

v0.6.1 y v0.6.2 son experimentos inválidos; v0.6.3 fue superado antes de
ejecución. Los cinco payloads locales de v0.6.2 están ignorados por Git y no se
leen, reportan, comparan, reutilizan ni publican. El marcador
`INVALID_DO_NOT_USE.md` sí queda publicado para preservar el resultado adverso.

## 4. Línea A — aprendizaje mensual plurianual y estacional

Ejecutar primero el contrato v0.6.5, no una campaña inventada durante la marcha.
La unidad atómica permanece siendo un mes que predice el mes inmediatamente
siguiente. La información se acumula únicamente mediante posterior sellado y
`Z_post` future-only. El modelo nunca recibe 10, 12 o 24 meses condensados como
un bloque para acertar un único mes.

Orden obligatorio:

1. implementar M0/M1/M2 sin abrir 2022 ni 2023;
2. demostrar con fixtures y estado 2024 ya conocido la cronología, ausencia de
   fuga, invariantes de suma cero, pooling jerárquico y equivalencia exacta de
   M0 con v0.6.4;
3. congelar hashes de software y un addendum de ejecución;
4. ejecutar enero de 2022 → febrero de 2022 y continuar sin reinicio hasta
   diciembre de 2024;
5. emitir checkpoint inmutable, manifest y explicación sustantiva tras cada
   año; no esperar al cierre completo para informar hallazgos materiales;
6. separar resultados por participación, cantidad y valor; conservar pérdidas,
   abstenciones, soporte bajo y diciembre;
7. sólo después decidir si 2021 o el rango 2019–2021 reduce un bloqueo real.

La disponibilidad 2019–2026 fue afirmada por el usuario, pero no autoriza abrir
años adicionales sin una pregunta discriminante. El estudio general de tiempo
de entrenamiento debe comparar cadenas causales con distinta edad de
posterior, alineadas por fase calendario; nunca ventanas N→1. Si se comparan
longitudes, la evaluación debe cubrir bloques equivalentes y declarar qué
posterior acumulativo tenía cada modelo en cada freeze.

## 5. Línea B — candidato europeo diario

Esta línea corre en paralelo sólo en trabajo barato y remoto mientras v0.6.5 se
implementa. No descargar archivos masivos al disco local.

Orden obligatorio:

1. revalidar la documentación oficial de TBAuctions/ATLAS;
2. obtener cuenta o acceso sólo con autoridad explícita del usuario cuando el
   paso implique contrato, mensaje externo, pago o aceptación de términos;
3. pedir primero esquema y muestra mínima remota, no histórico completo;
4. comprobar los diez gates del preregistro de adquisición;
5. registrar `PASS`, `FAIL`, `SOURCE_UNAVAILABLE` o `PARTNERSHIP_REQUIRED` sin
   convertir ausencia de acceso en ausencia de mercado;
6. sólo tras `PASS` crear el preregistro científico diario específico de esa
   fuente, con unidad evento/día basada en datos raw y sin precios regulados;
7. si ATLAS no pasa, evaluar EquipmentWatch; no mezclar sus contratos ni usar
   índices diarios como outcomes raw.

Drive, GitHub y VPS son recursos disponibles, no permisos ilimitados. Derivados
pequeños, código y recibos pueden vivir en GitHub. Raw pesado o restringido no.
El VPS sólo se usa cuando el volumen o la licencia lo justifiquen y después de
resolver acceso, ruta, custodia y autorización.

## 6. Invariantes no negociables

- ciclo: `freeze → outcome oficial → adjudicación → Z_post → future prior`;
- `Z_post` estructura evidencia; no sustituye al posterior económico;
- `capacidad != permiso != soporte != autoridad != ejecución`;
- claim indexado por producto × mercado × nodo × horizonte × régimen × target
  × comparador × arista de decisión;
- `global_winner: null` salvo evidencia excepcional explícita;
- no RAW-to-prior, no reescritura retrospectiva, no datos sintéticos como
  evidencia de mercado, no promedios mensuales presentados como raw diario;
- valor estadístico aduanero por kg no es precio de transacción;
- pruebas y manifests demuestran software/custodia, no eficacia de mercado;
- no borrar evidencia material ni automatizar limpieza de disco.

## 7. Definición de terminado del heredero

El relevo habrá producido progreso real cuando exista al menos uno de estos dos
resultados, sin debilitar el otro:

- campaña v0.6.5 completa, auditada y explicada, capaz de discriminar si la
  memoria estacional mejora M0 por target y dónde; o
- fuente europea diaria con contrato de evidencia `PASS` y preregistro de
  campaña diaria congelado antes de abrir outcomes.

Un conector, una muestra, tests verdes o acceso a una API no bastan por sí solos.
Cada checkpoint material debe decir en castellano: resultado observado,
comparación, frontera de evidencia, significado, reparabilidad, incertidumbre,
consecuencia para BMA/BIND, artefactos cambiados, bloqueo real y próxima acción.
