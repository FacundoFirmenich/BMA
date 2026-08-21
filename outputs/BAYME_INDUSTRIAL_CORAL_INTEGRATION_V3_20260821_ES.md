# BayME industrial coral V3 — integración posterior a RMK

Fecha: 2026-08-21

## Resultado

BayME queda mejor posicionado en los dos niveles pedidos.

En el nivel particular, RMK ya es una campaña BPM física cerrada y no sólo un candidato: 388 celdas, 1.008 observaciones y 14 comparaciones M1 reales con resultados mixtos. Argentina mantiene separados IPC/crédito/M3, UCII e IPI; Eurostat mantiene separado RC15 de la nueva capa STS país×actividad.

En el nivel coral, la integración conecta estados sin mezclar posteriors:

- RMK: precio y cantidad de madera por producto, medición, destino y evento;
- INDEC IPI/UCII: estado mensual de producción y capacidad industrial argentina;
- Eurostat STS: producción mensual armonizada por país y NACE;
- Prodcom: soporte anual por producto, país, cantidad y valor;
- Puertos: flujo físico mensual por puerto y naturaleza;
- TED: intensidad institucional por eventos CPV-NUTS.

## Dos saltos robustos

El salto cuantitativo combina densidad local real: RMK aporta 1.008 observaciones; RC15 conserva 69.498 contrastes arista-mes; STS abre un panel país×NACE y Prodcom un panel producto×país×año. Es suma de cobertura, no suma de likelihoods.

El salto cualitativo separa cuatro funciones antes confundibles: outcome de mercado, outcome industrial, soporte de identidad/escala y observador causalmente rezagado. Esa separación permite estudiar mecanismos sin convertir un puerto, una licitación o una estadística anual en “verdad” del precio de una subasta.

## Evidencia oficial revalidada

INDEC publica UCII e IPI mensuales y series por bloques o divisiones. La disponibilidad oficial hace reparable la custodia futura, pero no recupera automáticamente los payloads históricos perdidos.

Eurostat ofrece acceso REST/SDMX gratuito. Su base conserva la última versión, no un archivo de versiones anteriores; por ello toda cadena futura debe guardar la primera respuesta, su fecha de actualización y sus flags. Prodcom ofrece producción anual vendida en cantidad y valor; su cadencia impide usarlo como target mensual.

## Límites

La integración arquitectónica está materializada; la validación prospectiva nueva no ha comenzado. Persisten las brechas de bytes Argentina/RC15, el freeze UCII no autoritativo, IPI no recuperado, Eurostat julio incompleto, M2 RMK sin soporte, Comtrade en cuarentena y TED sin cantidad suficiente.

No hay ganador global, promoción ni claim industrial general. El siguiente gate es adquirir tres muestras mínimas oficiales con custodia de vintage y congelar el diseño antes de observar nuevos outcomes.
