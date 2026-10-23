# ECHO-4 / WORLD-1 — resultados del primer slice software

Fecha: 2026-09-21. [Contrato](ECHO4-WORLD1-DESIGN.md).

> Orden posterior actualizado: SENSATION-1 y BOUNDARY-1 antes de SELF-1.
> Estos resultados históricos se conservan; véase el [programa vigente](ECHO4-EGO-PROGRAMA.md).

Encuadre actual: [ECHO-4 desarrolla el ego funcional de ECHO-AI](ECHO4-EGO-PROGRAMA.md).
Los resultados siguientes son su base de viabilidad, no una prueba de ego.

## Resultado

Implementado y probado un mundo renovable de dinámica entera, con
contabilidad explícita, verificador exhaustivo y conexión al agente
original. Sin hardware, METAVERSE-1, PX4, Gazebo ni LLM. ECHO-4 avanza
como programa de software; el hardware queda para después.

**Factibilidad física demostrada en este mundo; mantenimiento aprendido
todavía no demostrado.** No se emite un certificado de ECHO-4 ni se
considera cerrada E4-MAINTAIN-1.

| Medida | Resultado |
|---|---:|
| Estados corporalmente vivos enumerados | 16.002 |
| Transiciones examinadas | 48.006 |
| Estados del núcleo de viabilidad de observación completa | 15.954 |
| Estado inicial `(32,64)` dentro del núcleo | Sí |
| Prefijo del testigo encontrado | 83 acciones |
| Ciclo recurrente del testigo | 2 acciones |
| Pruebas nuevas | 45/45 |
| Pruebas de regresión seleccionadas | 48/48 |

El testigo converge al ciclo:

```text
(H=127, theta=112) --avoid--> (124,96) --approach--> (127,112)
```

Todas sus transiciones se vuelven a comprobar con la física pura y su
balance de recursos. La fuente de recarga es externa; no es una máquina
de movimiento perpetuo ni una simulación termodinámica real.

Control histórico: con los incrementos de HEAT-1b, el analizador devuelve
núcleo vacío, 71 acciones máximas desde el inicio y 276 como máximo entre
todos los estados vivos. Una prueba compara las 48.006 transiciones con
`ThermalDockEnv.step_homeostatic` real, sin modificarlo. El control sin
entrada de recursos también devuelve núcleo vacío.

## Primera ejecución del agente: resultado negativo conservado

El demostrador conecta **`nexus0.loop.Agent` original**, con Q inicial a
cero, una vida y aprendizaje en línea. No recibe el testigo ni la política
del oráculo. Se solicitan 256 turnos; se detiene al morir.

| Medida | Resultado |
|---|---:|
| Acciones ejecutadas, incluida la terminal | 37 |
| Causa de terminalidad | calor |
| Estado final | `H=49, theta=127` |
| Reinicios | 0 |
| Muertes | 1 |
| Entrada externa de recursos | 65 |
| Consumo efectivo | 48 |
| Derrame | 0 |
| Balance | `32 + 65 = 49 + 48 + 0` |
| Slots CAM ocupados | 6 |
| Slots destruidos / hechos falsos / llamadas a cortex | 0 / 0 / 0 |

Esto es una prueba de integración, no una campaña de entrenamiento ni una
comparación estadística de políticas. El agente aún no mantiene el cuerpo.
No se cambia la puntuación ni se añaden rescates para ocultar ese resultado.

## Límite perceptivo medido

El encoder existente produce 32 paquetes WSP distintos para los estados
vivos; contando también estados terminales, el dominio corporal completo
produce 45. En los 32 grupos vivos hay al menos una acción con resultados
observables distintos según el estado exacto oculto por las bandas.

Dos grupos mezclan estados del núcleo con estados condenados; 14 agrupan
estados con diferentes conjuntos de acciones viables. Cuatro paquetes
terminales térmicos coinciden con paquetes vivos. El ciclo de vida detecta
terminalidad mediante el contrato existente y prohíbe seguir actuando:
el WSP por sí solo no distingue todas esas situaciones.

Por eso `partial_observation_control_proven=false`. Esto no demuestra
imposibilidad de aprender con historia; identifica una brecha que el próximo
experimento debe tratar explícitamente. El evaluador no entrega el estado
exacto al agente como atajo.

## Reproducción

Desde `/home/user/REALRXOS/RXos/echoai`:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.. python3 -m echoai.echo4 audit
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.. python3 -m echoai.echo4 demo --turns 256 --trace
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.. python3 -m unittest echoai.tests.test_echo4_world1 -v
```

Los comandos del módulo emiten JSON en stdout. No guardan archivos ni
dependen de renderer o servidor. `--greedy` no congela aprendizaje. La
ejecución está limitada a 10.000 turnos y no reinicia al individuo.

Regresión ejecutada:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.. python3 -m unittest \
  echoai.tests.test_qtable echoai.tests.test_heat1 echoai.tests.test_echo2 \
  echoai.tests.test_nexus0.TestWorld echoai.tests.test_nexus0.TestEncoder \
  echoai.tests.test_nexus0.TestGate echoai.tests.test_nexus0.TestBench -v
```

No se ejecutó toda la suite histórica ni se reabrieron exámenes sellados.
Los 93 tests indicados cubren el módulo nuevo y esa regresión seleccionada.
Incluyen reproducción del audit en un proceso nuevo, rechazo de testigos
alterados, comparación con iteración de horizonte finito independiente,
balance, entradas inválidas, terminalidad, aislamiento del oráculo,
preservación del agente y ausencia de escrituras por `NAVI_THOUGHT_LOG`.

Huellas deterministas del resultado:

```text
grafo:   971c481fc4e0a9e9e816365904f07116ec7af53aad4877885e433d4c591f4554
nucleo:  bb296e24ab3a8390de27544402e3264ddf3441b4d0991955c7badf1b5aa19b20
testigo: 0f9b5225afc9d9358684f125a00b09d6e5e3b1fb8cd34733a748b45a8d952ec9
demo:    bc17fdff5fa691af64b873f0b861f5dbb9632a86c755796d87212d8c4ba7d38f
```

Son hashes de contenido reproducible, no certificados de campañas.

## Preservación y siguiente paso

No se modificó ningún `.py` de `nexus0/`. El inventario ordenado de esos
archivos y sus SHA-256 produjo, antes y después, el mismo digest:

```text
2612122246fef64f53b84717f87e59be1cc07421c4bfd268386340cf970b47b8
```

El código nuevo vive en [echo4](../echo4/README.md), fuera de los inventarios
amplios de las campañas anteriores. Se preservaron los cambios preexistentes
del usuario; no se tocaron kernel, hardware, METAVERSE-1 ni certificados.

Siguiente slice: E4-SELF-1, contrato de observabilidad y atribución
cuerpo/entorno. La continuidad y el mantenimiento con trabajo útil y daño
reparable siguen en el programa del ego funcional. Entrenamiento y evaluación
deben diferenciarse; no añadir un controlador oráculo dentro del agente ni
un segundo bus.
