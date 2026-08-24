# BMA — cadena causal continua 2022–2024 y mapa estacional local

**Fecha:** 2026-08-15

**Estado:** cadena retrospectiva causal completa, auditada y sin reinicios.

## Qué cambió

La limitación anterior era concreta: el 2024 basal disponible se había inicializado de forma independiente y, por ello, la recurrencia causal 2023→2024 no era estimable. Esa limitación quedó reparada. Ahora existe una cadena separada que transporta el posterior y `Z_post` desde diciembre de 2022 hasta diciembre de 2024, con una predicción por mes y exclusivamente para el mes siguiente.

La reparación no convierte el trabajo en prospectivo ni ciego: los objetivos 2024 ya eran conocidos por otro experimento. Sí permite comprobar si la señal sobrevive cuando el algoritmo se obliga a avanzar causalmente, sin reinicios ni condensación temporal.

## Mapa estacional reproducido

### Participación

- **Junio–septiembre:** la memoria anual armónica mejora al modelo ordinario en los cuatro meses de 2024. Coincide con la ventana observada en 2023.
- **Octubre–noviembre:** el armónico más residuo jerárquico mejora al ordinario en ambos meses de 2024. Coincide con la estructura observada en 2023.
- **Diciembre:** el residuo jerárquico presenta una mejora numérica, pero la adjudicación primaria se abstiene por `YEAR_END_UNCALIBRATED`.

Esto revela un cambio de mecanismo por fase: durante el verano domina una señal calendario común; en otoño pasa a dominar una señal jerárquica o composicional más localizada.

| Mes | Modelo ordinario | Variante local respaldada | Diferencia frente al ordinario | Lectura |
|---|---:|---:|---:|---|
| Junio | 0.114751675 | Armónico: 0.114750519 | −0.000001155 | mejora local |
| Julio | 0.112733510 | Armónico: 0.112423610 | −0.000309900 | mejora local |
| Agosto | 0.120626981 | Armónico: 0.120084035 | −0.000542946 | mejora local |
| Septiembre | 0.110031874 | Armónico: 0.109921329 | −0.000110546 | mejora local |
| Octubre | 0.110983718 | Jerárquico: 0.110956314 | −0.000027404 | mejora local |
| Noviembre | 0.110246505 | Jerárquico: 0.108744968 | −0.001501538 | mejora local clara |

La señal es compatible con estacionalidad de productos o de composición de productos. CN4 sigue siendo una agrupación administrativa y no identifica por sí sola un producto físico único; sin embargo, las agrupaciones pueden transportar una mezcla económica genuinamente estacional. El objetivo siguiente es localizar qué componentes generan la fase, no negar la fase porque la taxonomía sea imperfecta.

### Cantidad

La mejora de septiembre mediante el componente jerárquico reaparece en 2024: 1.299612 frente a 1.373371 del modelo ordinario, aproximadamente 5.37 % menos error. Octubre y noviembre no muestran mejora estacional. La señal queda localizada en septiembre, no extendida artificialmente al otoño completo.

### Valor unitario estadístico

La mejora armónica de marzo reaparece en 2024: 0.471197 frente a 0.478786, aproximadamente 1.59 % menos error. Octubre y noviembre no muestran mejora estacional. Continúa siendo valor unitario estadístico, no precio de transacción.

## Resultado adverso y significado arquitectónico

Los pesos prequentiales conjuntos terminan concentrados en el modelo ordinario. No borran las mejoras locales: demuestran que un peso acumulado sobre todas las fases y celdas es incapaz de explotar una señal que cambia de mecanismo según el mes.

La arquitectura siguiente debe ser un selector local congelado antes de nuevos datos:

- participación: armónico en junio–septiembre; jerárquico en octubre–noviembre; ordinario fuera de esas ventanas;
- cantidad: jerárquico sólo en septiembre;
- valor unitario: armónico sólo en marzo;
- diciembre: predicción registrada y posterior actualizado, pero abstención primaria mientras siga sin calibración de fin de año.

## Evidencia y límites

- Cadena: diciembre de 2022 → diciembre de 2024, sin reset de posterior ni `Z_post`.
- Contrato: cada mes predice exclusivamente el siguiente.
- Octubre–diciembre: auditoría PASS, 17/17 archivos y 9/9 eventos causales.
- Paquete enero–septiembre: auditoría PASS, 47/47 archivos y 27/27 eventos.
- El primer intento de cada nueva ejecución falló antes de abrir objetivos; ambos fallos se conservaron y las reparaciones tuvieron identidad propia.
- No hay validación prospectiva, ciega ni industrial externa.
- No se declara una adjudicación agregada entre variables o fases.

## Consecuencia

BMA ya no sólo detecta que existe estacionalidad: ha localizado una transición de régimen calendario reproducida en dos años consecutivos bajo posterior acumulado. El paso científicamente correcto es congelar el selector por fase y probarlo únicamente en un año o jurisdicción que no haya participado en su descubrimiento. En paralelo, la cadena completa permite preregistrar el estudio general de edad de entrenamiento con cohortes causales de distinta antigüedad y fases calendario alineadas.

## Hashes terminales

- manifiesto enero–septiembre 2024: `d365286045a699def2eb0c7c9252a09ea33cd7b4360ba8553efcc53829e97bd4`;
- manifiesto octubre–diciembre 2024: `2d4fa1ad70d028700946ff7ec286001359f601378ef5bf98db0bde3f815ff1e7`;
- resultado octubre–diciembre: `e46979df9caad9d38441a670be8f530da55fbaef05580bd03b5b4891bedc3afc`;
- posterior terminal diciembre 2024: `f5567f30de01d0111a68ebfd85b58dc9c21601a3f4f02612dcc98a37f8abb3b1`.
