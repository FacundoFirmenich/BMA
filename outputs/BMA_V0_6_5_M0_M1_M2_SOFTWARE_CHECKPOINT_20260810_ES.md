# Checkpoint sustantivo — BMA v0.6.5, antes de abrir 2022/2023

La posición científica queda mejor preparada, pero no mejora aún ningún resultado de mercado: se congeló y probó un núcleo causal para comparar M0, M1 y M2 sin abrir outcomes de 2022 ni 2023. M0 conserva exactamente las features de v0.6.4; M1 incorpora memoria armónica anual; M2 añade residuo mensual jerárquico con centrado de suma cero. Los pesos son independientes para participación, cantidad y valor y sólo cambian tras adjudicar el target correspondiente.

Esto reduce el riesgo metodológico de confundir edad de entrenamiento con fuga temporal o con una ventana N->1. No demuestra que exista estacionalidad, que M1/M2 ganen a M0, ni que cantidad o valor dejen de perder: esas siguen siendo hipótesis que sólo la cadena sellada 2022->2024 puede discriminar. La reparabilidad ante una interrupción es la del contrato de checkpoints y hashes; la incertidumbre dominante sigue siendo empírica.

Para BMA/BIND, el avance es de capacidad científica y custodia, no de validación comercial o industrial. El bloqueo real antes de ejecutar es ensamblar el runner de campaña sobre este addendum ya congelado y mantener el orden freeze->outcome->adjudicación->Z_post; ATLAS permanece en un gate de acceso/alcance/licencia separado. El addendum normativo es `preregistrations/AEAT_CH72_SEASONAL_2022_2024_V0_6_5_SOFTWARE_ADDENDUM.json`.
