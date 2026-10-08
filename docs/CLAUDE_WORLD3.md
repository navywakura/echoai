# CLAUDE — WORLD-3 (pegar tal cual)

CORTEX-1 y GUI-1 están **verdes**. No los reabras. No descargues un LLM.
No toques kernel, ISO, `parse_reply`, `plan.py`, `thought.KEYS`,
`sign.py` (salvo que un test de extract del anillo se rompa — no debería),
ni `lab/nexus0_report.json`.

Lees **antes de tocar código**: `echoai/CLAUDE.md`, `echoai/CLAUDE_SITUATED.md`
(programa situado **cerrado**), `echoai/docs/NOW.md`, `echoai/docs/NEXT_APPROACH.md`
§ grafo, `echoai/nexus0/corridor.py` (el patrón a copiar), `echoai/nexus0/sign.py`
(el patrón de informe).

Eres implementador. Un slice. Un KPI. No rediseñes.

---

## Qué construyes

Un **tercer env**, no el anillo, no el pasillo de 5, no SIGN. Un grafo
de **256 nodos**, 3 acciones, sucesor por **tabla** (como el pasillo:
nunca `(i+1)%n`, nunca un grid 2D que invente norte).

WORLD-3 es el primer **cuerpo-mapa**: la posición del animal **es** el
nodo. Mismo `Agent`, mismo WSP, mismo `encode_cell(index, kind)` de hoy.
ANTI-ALIAS (comprimir tipos) es el **siguiente** slice, no este: si CAM
se llena, **mídalo** y déjalo en el informe, no “arregles” el encoder.

El KPI se corre **con el córtex apagado**. Si solo funciona con Qwen,
el slice es rojo: eso sería un chatbot disfrazado, no un pulpo.

Esto no es AGI. Es un pasillo de 5 celdas crecido a 256 nodos, con
transferencia de T/CAM al cambiar la topología, como HOME/SHIFT.

---

## El mundo (`echoai/nexus0/graph.py`)

Contrato de env, igual que pasillo/SIGN: `cell/step/reset/teleport/reveal`
y atributo `kind` (lista). `Agent` ya admite `env=`. `reveal()` puede
ser no-op. `RingEnv.ask()` sigue **sin existir**. No pongas `KIND_NOVEL`
en el camino del KPI (dispararía PREGUNTAR y ensuciaría el brazo off).

```
N_NODES = 256
A, B, ... spine de 16 nodos compartidos (índice y kind idénticos en ambos layouts)
```

Dos layouts, **misma** lista `kind` en los nodos compartidos. Lo que
cambia es la tabla de sucesores, no las etiquetas (igual que el pasillo:
nada se repinta).

| layout | qué hace `approach` en el fork (nodo B del spine, índice que elijas y documentes) |
|---|---|
| `home`  | B → C → … → GOAL (un nodo GOAL al final del spine) |
| `shift` | B → X → … → GOAL, con X = THREAT (índice distinto de C, no el mismo nodo con otro kind) |

- `wait`: quedarse.
- `avoid`: retroceder un paso en el spine, o quedarse si no hay atrás.
- `approach` en GOAL: cobra y vuelve al inicio del spine (si no, bomba de reward, el pasillo ya lo resolvió).
- Nodos que no están en el camino: sucesor = sí mismos, para que la tabla sea total.
- Seed fijo (`BENCH_SEED`). Arranca en el primer nodo del spine.

Opcional, no bloquea el verde: 4 nodos del spine pueden llevar `extract_text`
en español (letreros). El KPI de este slice **ignora** el letrero
(`cortex=False`). No hardcodees un córtex.

`encode_cell` hoy usa índice: 256 nodos = 256 paquetes distintos si el
kind cambia, menos si muchos son EMPTY. Cuenta `cam` ocupado en el
informe. No cambies el encoder.

---

## El experimento

Como `corridor.py`: **un** Agent se entrena en `home`, se le cambia
`env.layout` (o se le entrega el env SHIFT **conservando** cam/q/t —
no construyas un Agent nuevo). Un control arranca de cero en SHIFT.

```
PYTHONPATH=. python3 -m echoai.nexus0.graph
```

Escribe `echoai/lab/nexus0_world3_report.json`. **Nunca** pisa
`nexus0_report.json`, `nexus0_cortex1_report.json`, ni el jsonl de GUI.

Turnos: los que hagan falta para que el spine HOME tenga T con
evidencia en los nodos compartidos. **No** toques `BENCH_TURNS` del
anillo. Constantes propias en `graph.py` (`TRAIN_TURNS`, `SHIFT_TURNS`).

### KPI (todos a la vez)

```
false_facts = 0
destroyed = 0
anillo default intacto  (si corres el banco, cortex_calls=0, policy_after [-12,5,0])

en WORLD-3, córtex APAGADO:
  nodos = 256
  T del spine HOME sobrevive al SHIFT en los nodos compartidos
      (conf ≥ 1 en al menos el fork B, sucesor predicho = C de HOME
       — y en SHIFT el sucesor real es X: el agente se equivoca donde
       el mundo cambió. Eso es el punto, como el pasillo.)
  transfer_gain > 0
      define transfer_gain = reward_sum_SHIFT del agente transferido
                           − reward_sum_SHIFT del control (Q/T/CAM vacíos)
      mismo número de turnos, mismo seed, greedy
  el control no copia T: unseen en nodos del spine que el transferido ya vio > 0
  3 acciones nada más
```

Nombra `transfer_gain` en el JSON. Si el transferido **no** se equivoca
en el fork (porque no usó T), dímelo claro: no bajes el KPI.

Cita el pasillo: no retunees rewards. `R_SUCCESS` / `R_THREAT` / `R_EMPTY`
los de siempre.

---

## Qué no se toca

- `parse_reply`, `oracle.accept`, `RingEnv` geometría, JUMP, pasillo,
  SIGN texts, `sign_cortex.py`, `thought.KEYS`, `plan.py` default 0.
- `lab/nexus0_report.json`.
- Encoder / ANTI-ALIAS / sleep / Akida / Qwen / GUI-2 / cuerpo físico.
- Subir wakes del anillo. No corras `--cortex` para “ayudar” a este KPI.
- MiniGrid, 8 acciones, grid 2D, FAISS, HTTP, pesos.

---

## Tests (`echoai/tests/test_nexus0.py`)

Añade una clase. Sin red, sin GGUF, sin `NAVI_CORTEX_CMD`.

1. `test_graph_has_256_nodes`
2. `test_home_and_shift_share_spine_packets` — mismo `encode_cell` en
   nodos compartidos; el fork **cambia** el sucesor, no el paquete de B.
3. `test_three_actions_only`
4. `test_wait_does_not_move`
5. `test_goal_does_not_pump` — approach en GOAL vuelve al inicio.
6. `test_transferred_t_knows_home_successor_at_fork`
7. `test_control_does_not` — control T vacía / unseen mayor.
8. `test_shift_world_is_not_home` — step(approach) desde B ≠ sucesor HOME.
9. `test_transfer_gain_positive` — el número del informe.
10. `test_false_facts_zero`
11. `test_ring_report_untouched` — no reescribas `nexus0_report.json`.
12. `test_graph_module_does_not_import_cortex_cmd` — WORLD-3 no enchufa LLM.

Si un test necesita 512 turnos y tarda, que sea el del informe, no
docenas de copias. Reutiliza `graph.experiment()` como el pasillo.

Al final, desde `/home/roger/REALRXOS/RXos`:

```
PYTHONPATH=. python3 -m echoai.tests.test_nexus0
PYTHONPATH=. python3 -m echoai.nexus0.bench
PYTHONPATH=. python3 -m echoai.nexus0.graph
```

Tests ≥ los que había (185+). Bench default candados. Informe `green: true`.

---

## Informe que me pegas a Grok

- tests OK / N
- candados del banco (copia `policy_after`, `false_facts`, `cortex_calls`, +80 si lo corriste)
- `transfer_gain` y los T del fork HOME vs SHIFT
- slots CAM ocupados / 4096
- archivos tocados
- si algo del KPI no salió: dímelo claro, no lo escondas

Si el grafo de 256 hace el train demasiado lento en este portátil,
**baja a 64 nodos**, déjalo escrito en el JSON (`nodes_requested=256`,
`nodes=64`, `reason=host`), y no finjas 256. 64 con transferencia real
gana a 256 de teatro. No bajes de 64.
