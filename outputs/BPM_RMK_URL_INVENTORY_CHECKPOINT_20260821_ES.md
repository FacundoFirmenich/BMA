# RMK Estonia: inventario causal previo a adquisición

Fecha: 2026-08-21

## Resultado

El candidato RMK sigue siendo científicamente valioso, pero queda menos listo
para replay que tras el primer XLSX. El inventario consultó únicamente HTML
oficial: 20 páginas, 17 eventos y 82 referencias de payload, equivalentes a 63
URLs únicas. Ningún XLSX/PDF/CSV histórico fue abierto.

Se identificaron 40 referencias de resultados, 15 ofertas/formularios, dos
referencias explícitas de normalización y 25 recursos inicialmente no resueltos.
Los nombres y páginas permiten fechar 31 filas de resultado y 15 de oferta. Hay
14 fechas con pares oferta-resultado en el primer corte; una reparación de rol
añade la oferta 2026-02-23. Trece páginas candidatas antiguas no están disponibles
en la ruta HTML construida.

## Significado

RMK ofrece un mercado físico real con precio y cantidad, pero el archivo web
actual es asimétrico: conserva resultados antiguos con mayor continuidad que
ofertas antiguas. Por ello no se puede afirmar que exista una cadena ciega
completa desde 2023. Los resultados 2023/2024 sólo pueden alimentar historia de
outcomes después de verificar sus campos y su comparabilidad; el replay con
oferta conocida empieza, como máximo, en 2025 y sólo para fechas empalmadas.

La estacionalidad permanece celda-local. Dos años nominales no bastan: se exigen
dos observaciones anteriores de la misma fase, producto, estándar y localización
comparable. Si faltan, el resultado es `NOT_ESTIMABLE_SEASONAL_SUPPORT`.

## Reparabilidad y siguiente acción

La falta de ofertas antiguas puede repararse parcialmente si los protocolos de
resultado contienen producto, localización, volumen y precio, y si existen
tarifas/distancias contemporáneas. Si no se dispone de normalización histórica,
sólo se comparan localizaciones idénticas; en otro caso se abstiene.

El paso siguiente es congelar una cola URL ordenada y metadatos HEAD, después
abrir resultados 2023 y 2024 uno a uno para un test de elegibilidad sin fitting.
Sólo entonces puede comenzar 2025 oferta -> freeze -> resultado -> posterior ->
Z_post -> prior futuro.
