# ECHO-5 · 5.0.0a1

> **Research preview / NOT GREEN.** ECHO-5 sigue abierto: esta publicación
> no certifica cierre científico, calibración limpia, S6 ni vuelo físico.
> Estado vigente: [checkpoint del proyecto](../docs/PROJECT-CHECKPOINT-20261011.md).
> El recibo de contradicción convencional de la calibración carece de
> `ulog-parameters.json`; no permite declarar una calibración limpia.

Esta es una exportación adaptada al repositorio público aplanado. **Sus bytes
y hashes difieren de las fuentes originales auditadas**; las cifras históricas
de abajo conservan su alcance original, no certifican esta exportación.
[Frontera de adaptación, comandos y límites](docs/PUBLICATION-PORTABILITY.md).

Integración experimental en CPU: objetos y relaciones, programas compuestos,
conceptos persistentes, aprendizaje por interacción y recuperación del control
robótico anterior. El neocórtex está apagado en este banco. S6 mantiene su
estado abierto; esta versión no declara puntuación ARC ni validación física nueva.

Primera ejecución histórica terminada y auditada: **93 pruebas pasaron**. La representación
nueva alcanza 31/32 rejillas sintéticas y la memoria 32/32; las diferencias y
los resultados negativos están en [el informe](docs/RESULTS-20261010.md).

La ampliación de cierre añade transferencia estructural, controles de biblioteca,
búsqueda profunda, MiniGrid/BabyAI, réplica de contraejemplos y MissionAgent con
un ejecutor Gazebo/PX4. Su estado actual se mantiene en el
[checklist de cierre](docs/CLOSURE-CHECKLIST.md); los resultados de la primera
ejecución no certifican automáticamente estos cambios.

Para el panel y el entorno externo:

```sh
make setup-sandbox
make panel
# Abrir http://127.0.0.1:8765 o http://echoai.localhost:8765
make checks-background
# Después de corregir los fallos de desarrollo:
make development-background
```

El panel permite crear una misión, avanzar paso a paso, continuar o pausar.
Muestra la observación parcial, el mapa recordado, hipótesis, acciones y
consecuencias del diario existente. Su red LIF de diagnóstico ejecuta el módulo
histórico de 256 unidades; no representa 500.000 neuronas ni dirige la política
del sandbox. Los recibos y logs permanecen en `artifacts/`.
[Uso, custodia y reproducción](docs/CLOSURE-RUNBOOK.md).
[Ejemplo de una decisión registrada en simulación](docs/DECISION-EXAMPLE-20261010.md).

```sh
cd ECHO-5
make setup
make check
make test
make bench OUT=artifacts/mi-evaluacion
make audit OUT=artifacts/mi-evaluacion
```

CPython 3.12.13, `.venv` propia y biblioteca estándar. El directorio de salida
debe ser nuevo: las ejecuciones anteriores no se sobrescriben. `thought.jsonl`
registra observaciones, hipótesis comprobadas, acciones y consecuencias. Puede
seguirse con `tail -f`; su contenido nunca vuelve como instrucción al actor.

```mermaid
flowchart LR
    I[Demostraciones y observaciones] --> G[Objetos, papeles y relaciones]
    G --> H[Programas tipados y conceptos]
    H --> P[Búsqueda y planificación acotadas]
    P --> V[Simulador y verificador]
    V --> M[Memoria con evidencia y contraejemplos]
    M --> H
    A[Selector de desafíos resolubles] --> V
    V --> E[Evaluación en casos nuevos]
    S[Sensores públicos] --> P
    P --> R[MissionAgent, POWER y SAFE heredados]
    R --> O[Acción WSP y consecuencia observada]
    O --> M
```

| Módulo | Implementación | Comprobación |
|---|---|---|
| GROUND-1 | Segmentación anterior, papeles contextuales y relaciones espaciales | Colores/disposiciones nuevos y abstención ante empates |
| HIER-1 | Composición tipada, conceptos, expansión acotada y reutilización de prefijos | Mismos candidatos con/sin reutilización; coste completo |
| CONCEPT-1 | Recuerdos con demostraciones, procedencia, dependencias y cuarentena | Revalidación, persistencia y biblioteca vacía como control |
| ADAPT-1 / RETRO-1 | Hipótesis de consecuencias, pruebas informativas y búsqueda desde la meta | Cambios de mapa, meta y dinámica frente a exploración pasiva |
| Contraejemplos y reparación | Desafíos con testigo, archivo de fallos y nueva comprobación de cada candidato | Selección secuencial, aleatoria y adaptativa con igual límite |
| Robótica | Planificador relacional acotado conectado al MissionAgent completo; POWER/SAFE y gateway independientes | Recibos de ejecución, llegada, colisiones, reserva, sensores, controles convencionales y Gazebo/PX4 |
| Custodia | Juez externo al proponente, límites, hashes, auditoría y replay | Respuestas reservadas fuera del actor |

Para resolver un JSON con demostraciones `train` y entradas `test`:

```sh
.venv/bin/python -I scripts/run.py solve tarea.json --budget 8000000 --trace artifacts/decisiones-nuevas.jsonl
```

`--memory memoria.json` carga conceptos y `--learn-to memoria-nueva.json`
conserva lo aprendido en desarrollo. `solved` significa consenso de los
programas considerados tras comprobar las demostraciones. La consulta sigue
marcada `test_verified: false`; una hipótesis plausible no es una verdad
comprobada. La búsqueda por niveles y los dominios finitos limitan la inferencia.

La integración importa piezas anteriores mediante `legacy.py`; necesita el
checkout completo de echoAI. Esta carpeta todavía no es un paquete autónomo
ni un producto de robótica desplegable. No activa enjambres, entrenamiento
de pesos o automejora recursiva.

- [Diseño e interfaces](docs/IMPLEMENTATION-DESIGN.md).
- [Contrato numérico](docs/BENCHMARK-CONTRACT.json).
- [Resultados y límites de la primera evaluación](docs/RESULTS-20261010.md).
- [Programas y conceptos](docs/GROUNDED-PROGRAMS.md).
- [Interacción y planificación](docs/INTERACTION.md).
- [Integración robótica](docs/ROBOTICS-INTEGRATION.md).
- [Aprendizaje adversarial](docs/ADVERSARIAL-LEARNING-PROPOSAL.md).
- [Inventario previo](docs/MODULE-INVENTORY.md).
- [Desarrollo y reproducción](docs/DEVELOPMENT.md).
