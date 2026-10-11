# Correcciones de búsqueda, exploración y currículo — resultados

[Expediente público seleccionado](../../research-archive/20261012/README.md)
(con resultados completos comprimidos, auditorías y procedencia). Las rutas
`artifacts/` del informe identifican recibos originales del laboratorio;
no son archivos distribuidos en esas rutas.


La implementación está comprobada y el piloto tiene sus cuatro auditorías
válidas. **La búsqueda pasa de 0/18 a 12/18 en las tareas del generador
independiente y de 0/9 a 9/9 en las plantillas**, con el mismo presupuesto por
tarea. Persisten seis agotamientos de presupuesto; no es un cierre universal
de transferencia ni una promoción automática.

La ejecución final empezó el **12 de octubre a las 00:03:50** y terminó a las
**00:06:18**, hora de Madrid. Duró 147,32 segundos, auditorías incluidas, en CPU
y en segundo plano. No hubo llamadas al LLM ni uso de GPU.

## Implementación comprobada

| Intervención | Cambio realizado | Límite conservado |
|---|---|---|
| Firmas y reutilización | Cachés acotadas de rejillas, objetos, relaciones, transiciones y pérdidas; descarte de enlaces indefinidos y alias equivalentes en todos los datos públicos | Construcción, consultas y escrituras consumen presupuesto; no se agrupan reglas sólo porque coincidan en entrenamiento |
| Poda segura | Pérdida irreversible de colores bajo una propiedad comprobada del alfabeto; cota inferior de pérdida para ramas que ya no pueden entrar en la frontera | Dimensiones finales iguales no eliminan transformaciones intermedias de tamaño; los 326 operadores siguen disponibles |
| Verificación prioritaria | Tras el primer ajuste, el trabajo restante comprueba las alternativas pendientes, rechazando al primer contraejemplo | Se exige terminar el nivel retenido completo; una hipótesis compatible o una mayoría no bastan |
| Exploración híbrida | Frontera cercana normalmente; información ante bloqueo observado o estancamiento, con cuota y enfriamiento | Mismas observaciones, habilidades, memoria y planificación; el disparador es una política fija, no aprendizaje demostrado |
| Currículo eficiente | Saltar selección pesada con un único superviviente, parar sólo al alcanzar una cota máxima exacta y actualizar únicamente hipótesis aún compatibles | No se acepta el 90 % de una familia como certeza; adquisición y evaluación siguen pagándose |

La cota de pérdida usa una suma no negativa sobre demostraciones y un conjunto
de estados distintos ya evaluados. Incluye longitud y orden para conservar
desempates. Nunca poda por esta regla una rama que aún podría ajustar todas las
demostraciones. Las pruebas diferenciales comprobaron fronteras, resultados,
alias, macros y desacuerdos en consultas. La revisión separada no encontró
bloqueos en esta cota.

## Búsqueda: comparación con el mismo presupuesto

Cada brazo recibe el mismo JSON público: demostraciones y entradas de consulta,
sin respuestas de consulta, identificadores de familia ni programas testigo.
Se mantienen **326 átomos, profundidad máxima 4, frontera de 24 estados,
12.000 programas expandidos y 2.000.000 unidades de trabajo**. Los descartes
anteriores a la expansión tienen contadores propios y consumen ese presupuesto.
Por tanto, el número de expansiones no representa por sí solo trabajo equivalente.

La semilla 2.800.000 se registró antes de medir esta revisión. Son casos nuevos
de familias conocidas, no un benchmark externo ni una confirmación definitiva.

| Brazo | Independiente, 18 casos | Trabajo total | Plantillas, 9 casos | Trabajo total |
|---|---:|---:|---:|---:|
| Histórico (`baseline`) | 0/18 | 35.995.373 | 0/9 | 17.999.298 |
| Sólo reutilización (`memoized`) | 0/18 | 35.996.308 | 0/9 | 17.999.583 |
| Firmas y verificación (`certified`) | 6/18 | 29.476.235 | 0/9 | 17.999.420 |
| Lo anterior + cota de pérdida (`certified_bound`) | **12/18** | **25.951.431** | **9/9** | **11.814.821** |

El último brazo reduce el trabajo acumulado un **27,90 %** en el generador
independiente y un **34,36 %** en plantillas frente al histórico. La caché sola
no resuelve el bloqueo. La mejora adicional de la cota se observa en los mismos
casos y con todos los demás cambios conservados.

| Familia independiente | Histórico | Firmas/verificación | Con cota | Pendiente |
|---|---:|---:|---:|---|
| `outline_extract_scale` | 0/3 | 0/3 | 3/3 | Resueltos en profundidad 3 |
| `fill_extract_tile` | 0/3 | 0/3 | 3/3 | Resueltos en profundidad 3 |
| `inside_erase_crop` | 0/3 | 0/3 | 0/3 | Presupuesto agotado en profundidad 3; dos casos con una hipótesis compatible, sin consenso cerrado |
| `right_erase_crop_rotate` | 0/3 | 0/3 | 0/3 | Presupuesto agotado en profundidad 2, sin hipótesis compatible encontrada |
| `below_recolor_reflect` | 0/3 | 3/3 | 3/3 | Resueltos en profundidad 2 |
| `pack_reflect` | 0/3 | 3/3 | 3/3 | Resueltos en profundidad 2 |

Las tres familias de plantillas alcanzan 3/3 cada una con la cota. **No se
emitieron respuestas incorrectas en esta muestra**, ni se perdió ningún acierto
de los otros brazos. Esto no demuestra ausencia universal de errores o
regresiones. `test_verified` sigue siendo falso dentro del actor; el juez externo
compara las respuestas emitidas con las soluciones reservadas.

Hay otros seis controles independientes, fuera del denominador de 18:
tres ambiguos producen abstención y tres que requieren introducir un color
inexistente se rechazan por la propiedad del alfabeto. No se cuentan como tareas
resueltas. En desarrollo conocido, el brazo con cota obtiene 4/6 independientes
y 3/3 plantillas; esos casos tampoco se suman a la muestra nueva.

## Exploración

Se evaluaron los siete perfiles registrados, cuatro mundos por perfil, con
acciones y presupuesto iguales: **112 episodios y sus replays**.

| Selector | Misiones | Acciones | Trabajo |
|---|---:|---:|---:|
| Información | 28/28 | 322 | 264.261 |
| Frontera cercana | 28/28 | 332 | 248.277 |
| Frontera aleatoria | 28/28 | 357 | 300.762 |
| Híbrido | **28/28** | **332** | **237.220** |

El híbrido usa un **4,45 % menos trabajo que frontera cercana**, con las mismas
acciones. Sus registros contienen 296 decisiones de objetivo y 36 de frontera
cercana: **ninguna activación informativa**. En esta muestra la mejora procede
de comprobar elegibilidad sin calcular toda la puntuación informativa. El
disparador de bloqueo está probado en software, pero su ventaja en misiones no
queda demostrada. Haría falta compararlo con una frontera cercana igualmente
optimizada en una evaluación registrada aparte. No hay ventaja de acierto ni
prueba de equivalencia estadística entre selectores.

## Currículo

Ocho ejecuciones emparejadas, cuatro adquisiciones por ejecución, los mismos
conjuntos de hipótesis y datos por brazo, y presupuesto total de 2.000.000 por
ejecución. Los controles también actualizan sólo los supervivientes, para que
la comparación no dependa de conservar controles innecesariamente costosos.

| Selector | Aciertos finales | Aciertos durante los cuatro prefijos | Trabajo de aprendizaje | Trabajo total, evaluación incluida |
|---|---:|---:|---:|---:|
| Secuencial | 56/64 | 200/256 | 428.502 | 1.249.296 |
| Aleatorio | 56/64 | 224/256 | 419.120 | 1.132.054 |
| Adaptativo anterior | 64/64 | 240/256 | 2.004.771 | 2.701.505 |
| Adaptativo eficiente | **64/64** | **240/256** | **674.849** | **1.371.583** |

La optimización conserva selecciones, supervivientes y respuestas del adaptativo
anterior, reduciendo un **49,23 %** su coste total. Sigue costando un **21,16 %
más que el aleatorio optimizado**. El promedio de utilidad mejora frente a éste,
pero el intervalo descriptivo entre ejecuciones incluye cero; ocho ejecuciones
no acreditan superioridad general. Los 256 resultados de prefijos reutilizan
los mismos 64 casos finales: no son 256 problemas independientes.

Exploración y currículo reproducen las configuraciones de la revisión r2;
su repetición en r3 valida la integración final, no añade muestras independientes.

## Verificación y recibos

- Suite final: **499 tests, cero fallos, 26 omitidos por dependencias opcionales**;
  perfil nativo requerido: **32/32**. Una comprobación nativa ampliada previa
  pasó **80/80**, incluidos los tests del híbrido. Los recuentos se solapan.
- Piloto final: 44 resoluciones de desarrollo y 132 de la muestra nueva,
  repartidas entre cuatro brazos: **176 búsquedas y 176 reproducciones**.
- Cuatro auditorías válidas en procesos separados: desarrollo, búsqueda nueva,
  exploración y currículo. El replay comparte implementación con el actor;
  las soluciones construidas y el juicio nativo añaden referencias semánticas
  independientes. No es verificación formal de todo el sistema.
- Fuentes propias, heredadas y del anfitrión permanecieron iguales durante
  la medición. Los manifiestos y archivos de fuentes permiten su reproducción.

Recibo principal:
[`artifacts/efficiency-pilot-20261012-r3/result.json`](../artifacts/efficiency-pilot-20261012-r3/result.json).
Tests:
[`artifacts/efficiency-checks-20261012-r4/result.json`](../artifacts/efficiency-checks-20261012-r4/result.json).
Cada subdirectorio del piloto contiene `result.json`, `audit.json`, diarios y
recibos de procesos. Identidades de esta ejecución:

```text
Fuentes: 3c5d12a966910277953e050e1b8b2b44781b4b1e346a83f51b4d6d08e4131458
Plan:    66318f7d6320ff109aef3ea0d44bd2ff701182add4613478a679ccf0f05a69f2
```

Se conservan también los intentos previos. `efficiency-pilot-20261011-r1` se
detuvo por una incompatibilidad del evaluador con el campo `category` de las
plantillas antiguas; se corrigió su adaptación sin entregar metadatos al actor.
No tiene resultado científico aceptable. La revisión r2 terminó auditada:
5/18 independientes y 0/9 plantillas con `certified`. Su semilla 2.700.000 pasó
a desarrollo antes de añadir la cota; no se presenta como nueva confirmación.

## Uso y trabajo pendiente

Desde `ECHO-5`, la versión mejorada puede ejecutarse mediante la CLI existente:

```sh
.venv/bin/python -I scripts/run.py solve tarea.json --budget 2000000 \
  --synthesis-strategy certified --ranking-bound --trace artifacts/mi-busqueda.jsonl
```

El JSON de tarea contiene `train` y entradas de `test`. El diario debe ser nuevo.
La estrategia histórica sigue disponible. El plan completo se ejecuta con
`scripts/efficiency.py launch --output artifacts/otro-piloto`; repetir su semilla
registrada es reproducción, no evidencia en nuevas tareas.

Queda reducir el coste de `inside_erase_crop` y `right_erase_crop_rotate`,
especialmente el cierre de consenso en los dos ajustes aún incompletos. También
queda comprobar el cambio de fase informativa y la relación coste/utilidad del
currículo en más ejecuciones independientes. Un siguiente ensayo deberá registrar
semillas nuevas antes de medir y conservar estos resultados de desarrollo.

Las operaciones de trabajo son una contabilidad explícita, no FLOPs ni julios.
La ejecución no reabre el examen histórico, no amplía el verde acotado de r3
y mantiene **S6 fuera de alcance hasta después de ECHO-5.5**.
