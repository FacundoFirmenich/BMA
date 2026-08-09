# Mercabarna Flor v0.5.0 - entrenamiento 1-20 de julio

## Posicion del proyecto

BMA queda mejor posicionado que en el checkpoint v0.4.1. El cold start de un
solo dia era materialmente insuficiente: al ampliar el entrenamiento al 1-20 de
julio, la cantidad pasa a superar los dos comparadores externos en el agregado
y, de forma mas clara, en el regimen ordinario. No se alcanza todavia evidencia
prospectiva ni validacion industrial.

## Fuente y soporte

- 180/180 objetos fecha x origen recuperados;
- 108 objetos positivos y 72 vacios completos para participacion;
- 742 filas positivas;
- 13 dias activos de 20;
- 137 celdas producto x origen, 98 productos y 9 origenes;
- 90 celdas con al menos 3 observaciones y 69 con al menos 5;
- manifest de fuente:
  `e91c14a8baf8802a56a57e4541aaf8b7b923bfad275d00a1756b1c926dd1e97c`.

La completitud declarada por el usuario autoriza ausencia de participacion,
pero no convierte una fila ausente en cantidad cero ni precio cero.

## Resultado agregado 21-31

| Capa/comparador | BMA | Control | Mejora relativa |
|---|---:|---:|---:|
| Actividad, Brier vs estado congelado | 0,105076 | 0,120455 | 12,77 % |
| Participacion, Brier vs estado congelado | 0,189078 | 0,195320 | 3,20 % |
| Participacion, log-loss vs estado congelado | 0,562133 | 0,575693 | 2,36 % |
| Cantidad vs estado congelado | 1,165045 | 1,237227 | 5,83 % |
| Cantidad vs persistencia | 1,165045 | 1,252766 | 7,00 % |
| Cantidad vs baseline fuerte | 1,165045 | 1,297821 | 10,23 % |

La cantidad cubre 427 intersecciones freeze-outcome.

## Cartografia por regimen

### Ordinario

En 283 celdas, BMA obtiene error 0,917697 frente a 1,105583 de persistencia
(mejora 16,99 %; 169-114) y 1,174073 del baseline fuerte (mejora 21,84 %;
179-104). Frente a su control congelado, la mejora adicional dentro del holdout
es pequena, 0,55 %: gran parte de la ganancia procede del entrenamiento 1-20,
no de reinformarse repetidamente en 21-30.

### Sabado

BMA pierde: 0,994814 frente a 0,885131 de persistencia y 0,941134 del baseline
fuerte. No hay ganancia frente al control congelado porque existe un unico
target sabado en el holdout. Estado: `ABSTAIN`.

### Fin de mes pre-agosto

BMA pierde: 1,949488 frente a 1,840608 y 1,813696. Aunque aprende respecto del
estado congelado, el comparador externo sigue siendo mejor. Estado: `ABSTAIN`.

### Precio

Sigue `DEGENERATE_METRIC_VETO`: solo 3 de 137 celdas cambian de precio y ninguna
presenta tres valores distintos en entrenamiento. No se emite claim de precio.

## Significado cientifico, tecnico y BIND

El resultado demuestra que el mecanismo puede extraer señal de una ventana
histórica corta y que la utilidad es local al regimen ordinario. Tambien
demuestra que no hay derecho a una afirmacion global: los dos regimenes
excepcionales son adversos y el precio no es identificable.

Para BIND, la demo defendible es actividad-participacion-cantidad con abstencion
explicita, no precio ni automatizacion de compras. El siguiente gate es una
revision independiente del codigo y un freeze verdaderamente prospectivo. La
historia 2019-2026 debe usarse despues para estacionalidad y estabilidad, sin
abrir el holdout futuro ni reescribir esta jurisdiccion.

Dos ejecuciones independientes produjeron el mismo manifest:
`63d019fd1500bfe033bcc4aa1e33e2cde7c400c163701f789d2ee7984786219b`.
