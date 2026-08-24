# Expansión pública BPM/HBP: cribado, probes y preregistros

Fecha: 2026-08-21

## Posición resultante

El proyecto queda mejor posicionado en dos planos complementarios. BPM obtiene
un candidato de mercado físico europeo de madera con precio y cantidad reales;
HBP obtiene una arquitectura coral industrial que relaciona outcome productivo,
flujo físico e intensidad institucional sin fusionar sus posteriors ni sus
autoridades.

## Salto particular: RMK Estonia

RMK publica ofertas y protocolos de adjudicación de madera sin exigir cuenta
para la lectura. La muestra preregistrada del 30 de junio de 2026 contiene:

- 16 objetos y seis clases físicas de madera;
- 105.910 m3 ofertados;
- 34 filas de adjudicación;
- resultado para los 16 objetos y 105.910 m3 adjudicados;
- precio de adjudicación medio ponderado muestral de 64,31542064016617 EUR/m3.

La muestra prueba estructura y empalmabilidad, no estabilidad histórica ni
ganancia predictiva. Las ofertas se realizan en destino y RMK compara precios
normalizados descontando transporte; por eso la campaña queda bloqueada hasta
congelar tarifas y distancias anteriores a cada subasta. El modelado será
subasta-a-siguiente-subasta, por producto y localización comparable, año por año
y sin mirar targets futuros.

Fuente oficial: https://rmk.ee/kuulutused/metsa-ja-puidu-muuk/

## Salto coral: Eurostat, Puertos y TED

Eurostat STS devolvió 18 observaciones mensuales de manufactura española
PRD/NACE C/SCA/I21 entre enero de 2025 y junio de 2026. Todas tienen estado `p`
(provisional) y el dataset declara actualización 2026-08-19. Es un outcome HBP
válido sólo si cada primera publicación y cada revisión se guardan como vintages
separados.

Puertos del Estado aporta 45 hojas, 28 autoridades portuarias y 40 naturalezas
de mercancía. Hay soporte industrial directo para mineral de hierro, chatarra,
siderurgia, químicos, cemento/clínker, madera/corcho, papel/pasta, maquinaria y
vehículos. Es flujo físico mensual; no contiene precio de clearing y sólo puede
actuar como observador o covariable disponible al corte.

TED permite consulta anónima. Para adjudicaciones CPV 44, la consulta mínima
encontró 3.132 notices activas; las diez devueltas tenían fecha, CPV y territorio,
pero ninguna tenía cantidad y sólo cuatro tenían valor. Se admite únicamente
como recuento de eventos institucionales CPV-NUTS hasta que otra prueba congelada
demuestre suficiente completitud de cantidad/valor.

Fuentes oficiales:

- https://ec.europa.eu/eurostat/web/products-datasets/-/sts_inpr_m
- https://www.puertos.es/datos/estadisticas/mensuales
- https://docs.ted.europa.eu/api/latest/search.html

## Hallazgo adverso: UN Comtrade

El preview abierto devolvió 20 filas para España, junio de 2025 y HS 44, pero
eran agregadas, no reportadas, con cantidad y peso neto cero y
`legacyEstimationFlag=4`. Se preserva la respuesta y se rechaza su autoridad
para modelar cantidad física o outcome final. Puede reabrirse sólo si un probe
posterior encuentra filas reportadas, no agregadas, con vintage y cantidad.

Fuente oficial: https://uncomtrade.org/docs/un-comtrade-api/

## Reparabilidad, incertidumbre y consecuencia

RMK es el avance más fuerte, pero requiere inventario histórico y normalización
de transporte. Eurostat es utilizable, pero provisional. Puertos es robusto en
cantidad y débil por ausencia de precio. TED es robusto en eventos y débil en
cantidad/valor. Comtrade falla el gate actual.

Los dos preregistros congelados separan esas funciones. Ningún byte de probe
puede entrar a fitting o scoring; ningún agregado coral decide un ganador. La
siguiente acción crítica es implementar conectores de inventario sin abrir los
payloads históricos, congelar hashes/URLs/soporte y después ejecutar las cadenas
en orden cronológico.
