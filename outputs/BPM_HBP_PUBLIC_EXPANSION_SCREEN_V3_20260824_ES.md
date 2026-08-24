# BayME - criba p£blica BPM/HBP v3

Fecha: 2026-08-24  
Estado: `BOUNDED_SOURCE_SCREEN_COMPLETE_NO_NEW_MODEL_AUTHORITY`

## Resultado en plata

La campa¤a queda mejor posicionada porque ya no depende de ATLAS para encontrar
un candidato europeo £til. ATLAS y EquipmentWatch quedan descartados bajo la
autoridad actual: ambos exigen credenciales obtenidas mediante contacto
comercial, cuenta, clave o suscripci¢n. No se cre¢ ninguna cuenta, no se
contact¢ a terceros y no se aceptaron t‚rminos.

Aparecen dos candidatos que justifican trabajo adicional y dos soportes m s
lentos:

1. EUMOFA ofrece primera venta pesquera semanal y mensual con producto f¡sico,
   mercado, volumen, valor y precio. Es el candidato BPM nuevo m s fuerte por
   sem ntica de mercado; la interfaz de datos devolvi¢ HTTP 403 en esta sesi¢n,
   de modo que todav¡a no existe una muestra remota reproducible.
2. La Oficina Central de Estad¡stica de Letonia ofrece producci¢n industrial
   mensual por NACE/MIG desde 2000M01 hasta 2026M06, incluidos C16, C161 y C162
   para madera y transformaci¢n. El esquema API pas¢; el POST m¡nimo devolvi¢
   HTTP 400 y debe repararse antes de preregistrar.
3. La Agencia Forestal Sueca ofrece precios oficiales trimestrales de madera
   por surtido, modalidad y regi¢n. La ra¡z API fue p£blica, pero la rama qued¢
   temporalmente limitada por HTTP 429. Adem s hay un quiebre metodol¢gico en
   2025 y no se observ¢ una cantidad transaccionada separada.
4. Letonia ofrece precios semestrales de madera por especie y di metro. Es una
   fuente abierta y comprobada, pero su frecuencia no sirve para una cadena
   mensual mes-a-mes.

## Evidencia remota m¡nima

### Letonia - madera

La tabla oficial `MEI020` expone 20 indicadores y 39 semestres entre 2006H2 y
2025H2. Una muestra JSON-stat2 de abeto de 18-26 cm devolvi¢:

- 2024H2: 92,26 EUR/mü sin IVA;
- 2025H1: 101,12 EUR/mü;
- 2025H2: 105,87 EUR/mü.

La respuesta declar¢ `official-statistics=true`, fuente Central Statistical
Bureau of Latvia y actualizaci¢n 2026-04-02. Esto prueba acceso, esquema y
valores; no prueba utilidad predictiva ni autoriza convertir semestres en meses.

### Letonia - producci¢n industrial

La tabla `RUI020m` declara 40 celdas NACE/MIG, cinco variantes del indicador y
318 meses. Incluye manufactura total y divisiones f¡sicas como alimentos,
textiles, madera, papel, qu¡micos, metales, maquinaria, veh¡culos y muebles.
Electricidad y gas aparecen como una celda separada y quedan excluidos.

La consulta de metadatos pas¢, pero tres intentos m¡nimos de datos -C16 y
manufactura C, con y sin la dimensi¢n eliminable- devolvieron HTTP 400. El
estado correcto es `SCHEMA_PASS_SAMPLE_FAIL`, no fuente ejecutable.

### EUMOFA

La documentaci¢n oficial establece tablas avanzadas semanales, mensuales y
anuales, con descarga CSV/XLSX/ODS; la primera venta semanal cubre especies y
mercados seleccionados y la mensual cubre todas las especies transmitidas por
administraciones nacionales. Los campos disponibles incluyen volumen, valor y
precio. Sin embargo, el endpoint de datos devolvi¢ HTTP 403 en esta sesi¢n.
Debe probarse un £nico export manual o una ruta p£blica documentada antes de
cualquier preregistro.

### Suecia

La fuente oficial publica precios trimestrales ponderados por volumen para
troncos de pino, abeto, madera para pasta de con¡feras y frondosas y le¤a, con
regiones y modalidades de entrega. La metodolog¡a cambi¢ desde 2025 y los
resultados recientes pueden revisarse. La API enumer¢ p£blicamente la base, pero
la rama de madera devolvi¢ HTTP 429; no se reintent¢ de forma agresiva.

## Comparaci¢n cient¡fica

EUMOFA es superior como candidato BPM porque conserva la tr¡ada f¡sica
producto-cantidad-precio y una frecuencia compatible con aprendizaje
prospectivo. Letonia industrial es superior como candidato HBP porque ofrece una
cadena mensual larga, manufactura estricta y mecanismos sectoriales, aunque no
es un mercado transaccional. Suecia y Letonia maderera son soportes valiosos,
pero su frecuencia trimestral o semestral y sus quiebres impiden tratarlas como
sustitutos directos de Luke.

Prodcom sigue siendo el puente anual de producto f¡sico europeo: alrededor de
4.000 productos con volumen y valor, acceso API p£blico y riesgo expl¡cito de
confidencialidad, cambios de c¢digo y doble conteo. Sirve para identidad y escala
anual, no para rellenar outcomes mensuales.

## Estados adversos preservados

- `TBAUCTIONS_ATLAS_REJECTED_ACCESS_GATE`;
- `EQUIPMENTWATCH_REJECTED_ACCESS_GATE`;
- `EUMOFA_DATA_UI_HTTP_403`;
- `SWEDEN_ROUNDWOOD_BRANCH_HTTP_429`;
- `LATVIA_RUI020M_SCHEMA_PASS_SAMPLE_HTTP_400`;
- `LATVIA_MEI020_SAMPLE_PASS_LOW_FREQUENCY_SUPPORT_ONLY`.

Ning£n 400, 403 o 429 se reinterpret¢ como dato ausente, cero, ‚xito o
autorizaci¢n para crear cuentas.

## Consecuencia y siguiente gate

Para BPM, el siguiente gate de mayor valor es un export m¡nimo EUMOFA de una
especie, un mercado y tres meses, sin login ni descarga masiva. Para HBP, el
siguiente gate es reparar una sola consulta `RUI020m` y capturar tres meses de
una divisi¢n manufacturera no energ‚tica. S¢lo despu‚s corresponde congelar
esquema, hashes, soporte, priors, pesos, recovery e invariantes y preregistrar
una campa¤a. Las adjudicaciones ya congeladas de Luke, IPI, UCII y Eurostat
siguen teniendo prioridad temporal cuando aparezca su primer outcome oficial.
