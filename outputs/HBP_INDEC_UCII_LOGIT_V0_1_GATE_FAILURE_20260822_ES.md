# UCII V0.1 — gate adverso preservado

Estado: `GATE_FAIL_SECTOR_BOUNDARY_VALUE_BEFORE_FIT`.

La primera especificación UCII no llegó a ajustar ni a pronosticar. Su gate
exigía que tanto el nivel general como los doce bloques sectoriales estuvieran
estrictamente entre 0 y 100. La lectura numérica posterior al preregistro halló
dos valores 0,0 en abril de 2020: productos del tabaco e industria automotriz.

El nivel general sí cumple soporte estricto en los 126 meses: mínimo 42,0 y
máximo 69,6. Los dos ceros pertenecen a observadores sectoriales que ya estaban
excluidos de la likelihood del target general. Por tanto, el defecto es un gate
de soporte demasiado amplio, no una invalidez del target, del logit general ni
de los priors congelados.

La reparación permitida requiere una nueva preregistración. V0.1 queda
inmutable y no se reinterpreta. V0.2 podrá mantener idénticos target, modelos,
priors, pesos y calendario, pero exigirá soporte estricto sólo al nivel general;
los bloques se preservarán con soporte cerrado 0–100 y sus eventos de frontera
no entrarán en la likelihood general.

No hubo posterior, `Z_post`, score, freeze de julio ni ganador.
