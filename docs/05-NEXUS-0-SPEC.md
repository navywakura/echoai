# 05 — NEXUS-0: especificación matemática y de software

**Sitio:** `echoai/nexus0/`  
**Imports:** `navi10_qn`, `navi10_cam`, `navi10_wsp`, `navi10_stdp`,
`navi10_spoke`, `navi10_dag` (repo raíz, `PYTHONPATH=.`).  
**Córtex:** OFF.  
**Hardware:** ninguno.  
**Prohibido:** clonar LIF; segundo bus; float; LLM; Akida.

Si este documento y el código discrepan, gana este documento hasta
que se actualice con un KPI.

---

## 1. Objeto del experimento

Demostrar, **sin LLM**, que un agente con WSP + CAM + Q-table + T(s,a)
+ gate:

1. parte de Q ≈ 0;
2. actúa 256 turnos en un entorno sintético;
3. deja de elegir una acción que produce recompensa negativa;
4. mantiene `false_facts = 0` y `destroyed = 0`;
5. emite WSP semántico (no FNV) con `rel` correcto en el banco vendor;
6. sobrevive a un cambio leve del entorno (fase F/G).

Eso es memoria + aprendizaje + un mínimo de generalización.

---

## 2. Espacio de estados y acciones

Estado interno de un turno (todo entero):

```
slot:    uint16     # 0..4095  (índice CAM / Q / T)
vertex:  uint16     # 0..65535 (Q8×Q8, se guarda en la ranura)
wsp:     bytes[16]
E:       int8[6]    # V A D C U B
ham:     uint8      # 99 = miss
novelty: uint8      # 1 si miss
```

Acciones:

| a | nombre | `rel` | enum `wsp.h` |
|---|---|---|---|
| 0 | approach | UNIR | 11 |
| 1 | avoid | TEMER | 18 |
| 2 | wait | OBSERVAR | 14 |

`N_ACTIONS = 3`. `N_SLOTS = 4096`.

---

## 3. Encoder semántico  (`encoder.py`)

### Entrada

`text: str`  o  `event: bytes`.

### Salida

`bytes` de longitud 16, layout idéntico a `wsp_packet_t` /
`navi10_wsp.pack`.

### Algoritmo (host)

1. Fold ASCII/ES como `navi10_spoke.fold_bytes` (minúsculas, quitar
   acentos).
2. First-match-wins sobre una tabla de n-gramas:
   - portar las claves útiles de `kernel/navi/wsp_lex.c`;
   - **más** las frases canónicas de `vendor/RogexWSP/examples/*.json`
     (source/relation/target/time/emotion → átomos + E).
3. Si hay match: rellenar src, rel, dst, time, E[6], domain, generator.
4. Si no hay match: asignar átomos por categorías (entidad / relación /
   tiempo) con reglas, **no** `h % 32` como primer recurso.
5. FNV (`navi10_wsp.event_to_wsp`) queda como **baseline** en el bench,
   no como encoder de producción.

`ext.generator_id` en NEXUS-0: `WSP_GEN_RXOS` (0x05) para el agente;
no G_talk de chatbot.

### Banco y KPI

Frases: JSON vendor + compactos de `examples/gallery/README.md` si
existen textos.

```
accuracy_src = correct_src / N
accuracy_rel = correct_rel / N
accuracy_dst = correct_dst / N
semantic_collision = (#distinct_texts that share identical 16 B) / N
```

Cierre encoder:

- `accuracy_rel` **estrictamente mayor** que FNV en el mismo banco;
- `accuracy_src` y `accuracy_dst` se reportan (no pueden ser 0 si
  rel es bueno: colapso src/dst = fallo);
- collision se reporta. Un encoder que mapea todo a YO→DESCONOCIDO→UNK
  pierde aunque rel “encaje” en un caso.

Paquetes múltiples (“estoy solo pero quiero conectar”): el encoder
de NEXUS-0 puede emitir **el primer** paquete y dejar el segundo para
NEXUS-1. Documenta esa limitación en el informe. No finjas dos
pensamientos en 16 B.

---

## 4. Mapa WSP → vértice → ranura

```
vertex = navi10_qn.simhash16(wsp)          # ya existe
slot   = cam.get(wsp) or cam.lookup_key…
if miss and plastic: allocate(...)         # navi10_dag
```

Stream-to-Spoke (`encode_event`) puede correr para `spikes` / latencia
del informe. **La política no usa el spoke como argmax.** Argmax = Q.

---

## 5. CAM = episodios (what happened)

Tras cada turno, si hay ranura:

```
extract  = f"a={a} r={r} next={s_next}"   # o más rico, pero entero/ASCII
has_fact = 1  solo si el entorno entrega un extracto verificable
              (etiqueta del cell). Nunca si el dato lo “inventó” prosa.
source   = "nexus0-env"
```

Campos extra (host, no caben en 32 B C): guardar `action`, `reward`,
`next_slot` en `label`/`kind` o un dict paralelo `echoai/nexus0/episode.py`
indexado por slot. **No agrandes `wsp_packet_t`.**

KCC: jamás borrar ranura. `destroyed` permanece 0. Si CAM lleno:
dejar de grabar episodios nuevos; Q sigue actualizándose sobre
ranuras existentes.

---

## 6. Q-table = política (what should I do)

`echoai/nexus0/qtable.py` — ya implementado. Contrato:

```
Q: int8[4096][3]   # 12288 B
γ = 7/8
α = 1/4            # Q += δ >> 2
clip [-127, +127]
```

```
δ = r + ((7 * max_a Q[s'][a]) >> 3) - Q[s][a]
Q[s][a] = clip(Q[s][a] + (δ >> 2))
```

`r` es int, ya escalado (±16, 0, +8).

Selección:

```
a* = argmax_a Q[s][a]
tie-break greedy: wait (a=2)
entrenamiento, fila empatada (Q≈0): approach — si no, el anillo
  0↔1 oscila y nunca se visita THREAT (visto en el primer banco)
ε-greedy entero: cada 8º turno (turn % 8 == 0) elige a = turn % 3
```

Test unitario ya cubre: reward negativo repetido en (s, approach)
hace que approach deje de ser argmax.

---

## 7. World model T(s,a)

`echoai/nexus0/world.py` — ya implementado.

```
T[slot][a] : uint16   # 0xFFFF = desconocido
N[slot][a] : uint16   # conteo de observaciones (satura 65535)
```

`predict(s,a)` → `Optional[int]` (None si 0xFFFF).

`observe(s,a,s_next)`: si N==0, escribe s_next; si N>0 y s_next
coincide, incrementa N; si discrepa, **no borra** (KCC): incrementa
un `conflicts` y **no** cambia T hasta que el nuevo valor gane en
conteo (mayoría simple, entero).

Error:

```
e = hamming16(vertex_pred, vertex_real)   # si hay predicción
  | 16                             # si no había predicción (miss T)
```

`surprise = e`. Se reporta `prediction_accuracy` = aciertos T / turnos
con T conocida.

NEXUS-0 no hace search multi-paso. Solo un paso.

---

## 8. Gate  (`gate.py`)

Función pura:

```python
def gate(wsp: bytes, *, cam_hit: bool, extract_ok: bool,
         E: tuple[int,int,int,int,int,int],
         proposed: int) -> tuple[int, int]:
    """Return (decision, action).
    decision: 0=OK, 1=MODIFY, 2=BLOCK
    """
```

Reglas NEXUS-0 (enteras, en este orden):

1. Si CAM flags INHIBIT y el sujeto coincide → **BLOCK**, action=wait.
2. Si `extract_ok` es falso y proposed == approach y el cell es
   amenaza (rel WSP == TEMER o flag env) → **MODIFY** a avoid.
3. Si U ≥ 60 y proposed == wait y hay amenaza → **MODIFY** a avoid.
4. Else **OK**, action=proposed.

BLOCK no llama córtex (no hay córtex). El WSP de salida puede encender
`flags |= 0x80` (VETO) en BLOCK/MODIFY.

No ejecuta ping, curl, ni `commands_dispatch`.

---

## 9. Entorno sintético  (`env.py`)

No robot. No EEG. No Wikipedia.

### Geometría

Anillo de `N_CELLS = 32` celdas. Estado del agente = índice `i`.
Cada celda tiene un `kind`:

| kind | WSP rel sugerido | approach | avoid | wait |
|---|---|---|---|---|
| GOAL | DESEAR / UNIR | r=+16 | r=0 | r=0 |
| THREAT | TEMER / PELIGRO | r=−16 | r=+8 | r=0 |
| EMPTY | OBSERVAR | r=0 | r=0 | r=0 |
| NOVEL | DESCONOCIDO | r=0, novelty=1 | r=0 | r=0 |

Layout inicial (fase A–E):

```
indices 0..31
THREAT at 7, 19
GOAL   at 3, 15, 27
NOVEL  at 11
resto EMPTY
```

### Dinámica

- `approach`: i ← (i+1) mod 32  **después** de cobrar r de la celda
  actual (te “metas” en ella).
- `avoid`: i ← (i-1) mod 32, r según tabla (evitar amenaza paga +8
  si kind==THREAT).
- `wait`: i no cambia, r=0.

El entorno **entrega extracto** de la celda (`kind` + índice). Eso
permite VERIFY del episodio. El agente **no** afirma hechos del mundo
exterior. `false_facts` cuenta si el loop escribe `has_fact=1` sin
extracto del env.

### Fases (bench)

| Fase | Turnos | Qué |
|---|---|---|
| A | 0 | Q≈0, T vacía |
| B | 0–255 | 256 interacciones |
| C | (durante B) | THREAT+approach debe acumular δ<0 |
| D | post-B probe | se coloca al agente en celda THREAT |
| E | 1 acción greedy (ε=0) | **no** elige approach |
| F | se mueve THREAT 7 → 8 (cambio leve) | |
| G | 64 turnos más + probe en 8 | avoid o wait en la amenaza nueva; la regla “no approach amenaza” se mantiene |

Semilla fija `seed=20260903` para reproducir.

---

## 10. Bucle de un turno  (`loop.py`)

```
observe cell
  → encoder.wsp_from_cell(cell)     # no FNV
  → vertex, lat = encode_event(wsp)
  → CAM lookup / allocate
  → ŝ' = T.predict(slot, a_prev) si hay
  → a_prop = Q.select(slot, turn)
  → decision, a = gate(...)
  → r, cell_next = env.step(a)
  → observe T(slot, a, slot_next)
  → e = d_H(ŝ', s') si había predicción
  → Q.update(slot, a, r, slot_next)
  → STDP opcional sobre w_dim (no sustituye Q)
  → grabar episodio CAM
  → metrics++
```

`cortex_calls` se incrementa **solo** si se llama a un módulo cortex.
En NEXUS-0 ese módulo no existe: el contador permanece 0. No pongas
un stub que sume.

Curiosity (métrica, no módulo):

```
store_priority = 1 if (novelty and surprise >= 4) else 0
```

Si CAM lleno, se prefieren episodios con `store_priority=1`.

---

## 11. Informe  (`bench.py` → `echoai/lab/nexus0_report.json`)

```
turns
verify
unknown
false_facts                 # debe ser 0
cortex_calls                # debe ser 0
destroyed                   # debe ser 0
mean_ham
wsp_semantic_acc            # accuracy_rel banco vendor
accuracy_src
accuracy_dst
semantic_collision
prediction_accuracy
prediction_hamming_error    # media e
action_success              # fracción r>0
policy_before               # Q snapshot slot amenaza, 3 valores
policy_after
negative_delta_causes_policy_change   # bool fase E
generalize_moved_threat               # bool fase G
encoder_beats_fnv                     # bool
```

Imprimir también compacto WSP de 8 turnos muestra (no FNV).

---

## 12. Tests de cierre

`echoai/tests/test_nexus0.py`

| Test | Pasa si |
|---|---|
| `test_q_negative_delta_flips_policy` | ya en `test_qtable.py` |
| `test_t_predict_observe` | T aprende una transición |
| `test_encoder_beats_fnv_rel` | rel vendor > FNV |
| `test_wsp_16` | len==16 siempre |
| `test_gate_inhibit_blocks` | INHIBIT → BLOCK |
| `test_false_facts_zero` | bench 256 → 0 |
| `test_destroyed_zero` | 0 |
| `test_cortex_off` | 0 llamadas |
| `test_phase_e_no_approach_threat` | greedy ≠ 0 en THREAT |
| `test_phase_g_generalizes` | amenaza movida no se approach |

Hasta que encoder/env/loop existan, los tests de integración pueden
ser `unittest.skip` **con el nombre del KPI**. No borres el test.

---

## 13. Archivos a crear / tocados

| Archivo | Estado |
|---|---|
| `echoai/nexus0/constants.py` | hecho |
| `echoai/nexus0/types.py` | hecho |
| `echoai/nexus0/qtable.py` | hecho |
| `echoai/nexus0/world.py` | hecho |
| `echoai/nexus0/encoder.py` | hecho (banco vendor exact-match; falta portar `wsp_lex.c`) |
| `echoai/nexus0/gate.py` | hecho (reglas §8) |
| `echoai/nexus0/env.py` | hecho |
| `echoai/nexus0/loop.py` | hecho (córtex ausente) |
| `echoai/nexus0/bench.py` | hecho |
| `echoai/nexus0/bank/canonical.json` | 6 frases vendor |
| `echoai/tests/test_qtable.py` | hecho |
| `echoai/tests/test_nexus0.py` | KPI verde en el corte 2026-09-03 |

No tocar `navi10_engine.py` en este sprint salvo un hook opcional
*después* de verde: `./navi10 --nexus0` que lance el bench. No es
criterio de cierre.

---

## 14. Fuera de alcance (aunque salga en papers)

MAP, V-JEPA 2, Titans, Dreamer, WorldEvolver, DMP-SNN, spiking
transformers, self-evolving world models: **apéndice bibliográfico**.
Cero dependencias pip de esos papers. Cero PyTorch en `nexus0/`.
