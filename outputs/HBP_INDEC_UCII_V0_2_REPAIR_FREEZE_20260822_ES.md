# UCII V0.2 — reparación congelada antes del fit

La reparación está mejor posicionada que V0.1 porque conserva el fallo y cambia
sólo la condición que lo causó. Los dos ceros sectoriales de abril de 2020 se
mantienen como evidencia. El nivel general, único target, conserva soporte
estricto, 126 meses y diez transiciones previas con destino julio.

No se cambió el modelo después de ver los ceros: M0 es persistencia acotada, M1
deriva acotada y M2 una regresión armónica anual local con dos armónicos. Los
tres tienen pesos iniciales iguales. No hubo fit, posterior, forecast ni score
V0.2 al emitir este documento.

La prueba conjunta V0.1/V0.2 pasa 6/6 y el lint pasa. El siguiente acto permitido
es una única ejecución sobre el workbook ya hasheado; julio debe permanecer
ausente y no existe ganador global.
