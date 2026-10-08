# Claude — XFER-1: el mismo animal en tres mundos

PATTERN-0b está verde. No lo reabras: **80 / 40 / +40**, memoria de
contexto entera y acotada, 29/29 mutantes requeridos, auditoría de
aislamiento cerrada. La suite canónica queda en **443 tests OK** con el
único `expectedFailure` histórico de WALK-1 sin resto.

El siguiente y único tajo es **XFER-1**. Si queda verde, cierra ECHO-1.

---

## Pregunta única

> ¿La misma instancia del animal conserva conocimiento útil al pasar por
> tres mundos compatibles y supera a nacimientos desde cero en los dos
> cambios, sin consultar el nombre del mundo?

No basta con ejecutar la misma clase tres veces. No basta un total positivo
pagado enteramente por un mundo. No basta copiar tablas a tres agentes. El
brazo transferido es **un solo `Agent` vivo**, con las mismas instancias de
CAM, Q, T y PatternMemory antes y después de cada frontera.

---

## Los tres mundos

Crea un solo adaptador de física, table-driven, con tres layouts declarados:

```text
PARK_A  escuela
PARK_B  primer cambio
PARK_C  segundo cambio, distinto del primero
```

Los tres comparten encoder, identidades WSP, acciones y la mayor parte de la
dinámica. B y C deben cambiar **física real** mediante tablas de sucesores;
no pueden ser sólo otro nombre, semilla, color o posición inicial. Cada salto
debe introducir al menos una transición contradictoria conocida de T y dejar
otras transiciones aprendidas todavía correctas. Publica ambas cantidades por
frontera.

Usa tres acciones. No metas ABRIR: XFER-1 prueba transferencia, no vuelve a
probar OPEN-1. Los layouts pueden vivir en `xfer1.py`; ningún nombre PARK_A/B/C
puede aparecer en `loop.py`, `pattern.py`, `qtable.py`, `world.py`, `gate.py`
ni `encoder.py`.

Incluye dentro del mismo adaptador una región de prueba con la regularidad de
orden dos de PATTERN-0. La regla compartida debe derivarse de una tabla/ciclo,
no de ramas `if PARK_*`. Puede haber regiones variables alrededor, pero deben
quedar al menos dos contextos maduros cuya semántica sea idéntica en A, B y C.

No copies `GraphEnv`, `PatternEnv` ni el bucle de `Agent`: importa, compón o
subclasifica la física existente donde corresponda.

---

## Qué memoria cruza

El mismo animal conserva, por identidad y sin serializar/copiar:

```text
ag.cam
ag.q
ag.t
ag.pattern_memory
```

PATTERN-0 debe entrar como extensión **opt-in** del predictor del mismo Agent.
No dupliques `turn()`. El default sigue sin PatternMemory y sin coste medible.
Cuando está encendido:

```text
(prev_slot, slot, action) -> pattern.predict(...)
si no hay regla madura     -> T.predict(slot, action)
tras el paso               -> T y PatternMemory observan la misma transición
```

Es el mismo canal de predicción/error; no una segunda T, CAM, Q, bitácora ni
thought-bus. PatternMemory nunca escribe las tablas de World.

Al cambiar de mundo se limpia sólo el latch efímero `prev_slot`: una
transición no puede empezar en PARK_A y terminar ficticiamente en PARK_B.
Limpiar ese latch no es borrar memoria. CAM/Q/T/PatternMemory permanecen por
identidad.

Si el hook exige tocar `loop.py`, debe estar apagado por defecto y acompañado
de un test que pruebe que `Agent()` no crea PatternMemory ni cambia sus
números canónicos.

---

## Protocolo causal

Constantes de turnos, semillas, posiciones de entrada y criterio se declaran
antes de ejecutar el examen.

### Brazo transferido

1. Nace una vez en PARK_A y se escolariza.
2. Se congelan/registran identidades y hashes de sus cuatro memorias.
3. Se reemplaza solamente `ag.env` por PARK_B y se limpia el latch efímero.
4. Entra en una posición declarada y corre la ventana B.
5. El **mismo objeto** cambia a PARK_C y corre la ventana C.

No reconstruyas el Agent entre pasos. No cargues snapshots en otro Agent.

### Controles scratch

Para PARK_B y PARK_C nace un Agent vacío independiente. En cada comparación:

- misma clase/layout de env;
- misma semilla;
- misma posición y estado físico de entrada;
- mismos flags y número de acciones;
- mismos turnos de adaptación/examen;
- mismos valores de `turn` entregados a la política, para que `% 8` no pague
  el resultado;
- mismo modo greedy/exploratorio en cada paso.

Añade un control de edad: un Agent que ha consumido los mismos turnos previos
en una física sin la regularidad/transferencia no puede obtener el gain. Así
separa conocimiento conservado de haber avanzado el reloj o calentado el
arnés.

### Sonda PatternMemory

Antes de aprender en B y antes de aprender en C, pregunta en puntos del riff
compartido con todas las memorias congeladas:

```text
pattern_transfer_hits_B > pattern_scratch_hits_B
pattern_transfer_hits_C > pattern_scratch_hits_C
pattern_observes_during_entry_probes == 0
```

`None` es fallo y no sale del denominador. Los dos brazos se puntúan sobre los
mismos puntos y sucesores revelados después de predecir. La sonda no da
recompensa ni escribe Q/T/CAM.

---

## KPI de cierre

Todo debe cumplirse a la vez:

```text
worlds                                      == 3
same_agent_across_worlds                    true
same_cam/q/t/pattern_objects                true
world_physics_differences_A_B               > 0
world_physics_differences_B_C               > 0
t_known_rows_on_entry_B/C                   > 0
t_contradictions_on_entry_B/C               > 0

transfer_reward_B - scratch_reward_B        > 0
transfer_reward_C - scratch_reward_C        > 0
aggregate_transfer_gain                     == gain_B + gain_C
aggregate_transfer_gain                     > 0
age_control_gain_B/C                        <= 0

pattern_entry_points_B/C                    > 0, mismos puntos por brazo
pattern_transfer_hits_B                     > pattern_scratch_hits_B
pattern_transfer_hits_C                     > pattern_scratch_hits_C
pattern_observes_during_entry_probes         == 0

world_name_branches_in_core                 0
false_facts / destroyed                     0 / 0
cortex_calls / llm_calls / human_labels     0 / 0 / 0
N_ACTIONS / thought.KEYS                    3 / 22
```

Si el cuerpo no puede dar gain positivo en B **y** C con un protocolo
emparejado, XFER-1 es rojo. No sustituyas reward por cobertura de Q ni escondas
un cero dentro del agregado. La utilidad predictiva de PatternMemory se mide
aparte porque hoy el predictor no es una acción.

---

## Mutantes mínimos

Cada afirmación necesita un contraejemplo independiente:

1. nace un Agent nuevo al entrar en B;
2. nace otro al entrar en C;
3. copia snapshots a otro Agent y afirma que es el mismo;
4. borra CAM en una frontera;
5. borra Q;
6. borra T;
7. borra PatternMemory;
8. conserva memoria pero no limpia `prev_slot`, creando una transición entre
   mundos;
9. PatternMemory no recibe las mismas transiciones que T;
10. la sonda aprende durante el examen;
11. `None` cuenta como hit;
12. los no cubiertos salen del denominador;
13. transfer y scratch se puntúan en turnos distintos;
14. scratch entra desde otra posición;
15. scratch usa otra semilla o fase de exploración;
16. el total positivo oculta `gain_B <= 0`;
17. el total positivo oculta `gain_C <= 0`;
18. PARK_C repite exactamente la física de PARK_B;
19. una rama por nombre de mundo entra en el core;
20. el control de edad recibe la regularidad verdadera;
21. el informe borra un mutante requerido;
22. un mutante futuro vivo intenta pasar con contadores mentirosos.

Aplica desde el principio la disciplina TALK-1c/PATTERN-0b: lista requerida,
entradas válidas, sin duplicados, todos los vivos contados aunque sean futuros,
y `green()` recalculando total/muertos desde la lista.

---

## Archivos y aislamiento

Esperados:

```text
echoai/nexus0/xfer1.py
echoai/tests/test_nexus0.py
echoai/lab/nexus0_xfer1_report.json
echoai/docs/STATUS.md
```

`loop.py` sólo si hace falta el hook opt-in de PatternMemory. `pattern.py`
debería permanecer intacto: PATTERN-0b ya cerró su contrato.

El runner escribe sólo `nexus0_xfer1_report.json`. No toca informes ni jsonl
anteriores. Sin red, Qwen, subprocess, numpy, torch, floats en el paso rápido,
etiquetas humanas ni nombres de mundo en el animal.

---

## Banco de entrega

```bash
PYTHONPATH=. python3 -m echoai.nexus0.xfer1
PYTHONPATH=. python3 -m echoai.tests.test_nexus0
PYTHONPATH=. python3 -m echoai.nexus0.pattern0
PYTHONPATH=. python3 -m echoai.nexus0.talk1
PYTHONPATH=. python3 -m echoai.nexus0.signc
PYTHONPATH=. python3 -m echoai.nexus0.graph
PYTHONPATH=. python3 -m echoai.nexus0.room1
PYTHONPATH=. python3 -m echoai.nexus0.bench
```

Reporta las filas B y C completas, las sondas de patrón, identidades antes y
después, batería, mutantes en fuente y archivos tocados. Confirma los candados
del anillo y que PATTERN-0 sigue en 80/40/+40.

Si cualquiera de los dos gains es cero, si PatternMemory no gana en una de las
dos fronteras o si aparece una rama por nombre en el core: **XFER-1 es rojo**.
No empieces ECHO-2 ni VITA-1.
