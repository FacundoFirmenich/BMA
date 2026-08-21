# Nueva clasificación canónica de la familia BayME

Estado: `FROZEN_FOR_INVENTORY_V1`

Fecha de congelación: 2026-08-15

## Corrección que gobierna el trabajo

La clasificación nueva no está formada por BayME, BayME Pulse, BayME EVE y BMA. Esos nombres identifican procedencias históricas y linajes de trabajo que deben conservarse como metadatos de origen.

Los tres destinos canónicos nuevos son:

1. **BPM — Bayesian Physics Markets**: mercados de bienes y fenómenos físicos. Incluye lonjas, Mercabarna —frutas, flores y plantas—, comercio físico industrial AEAT/CN y cualquier otro mercado físico recuperado. **BMA queda subsumido permanentemente en BPM y deja de ser un nombre canónico vigente.** `BMA` se conserva sólo como alias histórico y procedencia de evidencia.
2. **BUM — Bayesian Unreal Markets**: mercados y análisis cuyo objeto es intangible. No es una categoría residual para todo lo que no entre en BPM.
3. **HBP — Hierarchical Bayes Predictor**: predictores jerárquicos cuyo objeto rector es territorial, institucional, organizativo o sistémico; ejemplos dados por el usuario: Argentina, Unión Europea y Mondragón. HBP no es una subclase de BPM ni de BUM.

## Regla de adjudicación

La unidad de clasificación es la pieza de evidencia, experimento, módulo, afirmación o conjunto indivisible con objetivo identificable; nunca el nombre de su carpeta histórica.

- `source_lineage` registra BayME, BayME Pulse, BayME EVE o BMA.
- `canonical_destination` admite únicamente `BPM`, `BUM`, `HBP` o `UNCLASSIFIED_PENDING_CONTENT_REVIEW`.
- Una procedencia histórica no determina automáticamente el destino.
- Si un artefacto indivisible contiene materiales de destinos distintos, se preservan sus bytes intactos y se crean relaciones o extractos derivados con procedencia; no se reescribe el original.
- La asignación a HBP se decide por el objetivo rector de predicción jerárquica, no por el hecho trivial de que exista una jerarquía estadística dentro de un modelo de mercado.
- `CN4`, `CN8` u otras nomenclaturas AEAT/UE son niveles administrativos de observación, no productos ni destinos ontológicos. Un experimento AEAT sobre bienes físicos pertenece a BPM por su objeto físico, no por la etiqueta CN.
- Ambigüedad real implica `UNCLASSIFIED_PENDING_CONTENT_REVIEW`; está prohibido completar huecos por analogía o por conveniencia archivística.

## Invariantes de custodia

- No borrar ni renombrar destructivamente originales durante el inventario.
- Preservar resultados adversos, abstenciones, cuarentenas, `NOT_ESTIMABLE` y protocolos supersedidos.
- No alterar la jurisdicción histórica de una evidencia al reclasificarla.
- No publicar una transferencia que materialice una taxonomía no validada.
- No usar BMA como cuarto destino ni como sinónimo contemporáneo de toda la familia.

## Aplicación inmediata al trabajo ya ejecutado

La cadena causal AEAT capítulo 72 de 2022–2024, Mercabarna flores y las demás pruebas de mercados físicos conocidas son candidatas a BPM, sujetas a inventario unitario. Esto no convierte a toda carpeta BayME, Pulse o EVE en BPM.

La mini-ejecución de carga preparada en la rama auxiliar `agent/bma-v065-upload-split`, commit local `9b0d18e`, queda pausada y no publicada hasta que sus unidades sean inventariadas con esta regla. La pausa no invalida sus resultados científicos; impide únicamente consagrar una custodia nominal equivocada.

## Techo de afirmación

Este documento congela la ontología operativa para inventariar y migrar. No afirma todavía que la recolección sea exhaustiva, que cada pieza haya sido adjudicada ni que BPM, BUM o HBP estén materializados como repositorios definitivos.
