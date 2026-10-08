# CLAUDE.md — echoAI MONAD / NEXUS-0

Lees este archivo **antes de tocar código**. Eres un implementador, no un
arquitecto de producto. El diseño ya está cerrado en `echoai/docs/`.
Si una idea tuya choca con un invariante, gana el invariante.

Repo padre: `/home/roger/REALRXOS/RXos` (este directorio es `echoai/`
dentro de ese árbol). El unikernel echOS 2.1 **no** se toca en NEXUS-0.

---

## Qué estás construyendo

**echoAI** no es un chatbot. No es “SNN + LLM”. Es un agente de dos
relojes cuyo **núcleo funciona con el córtex apagado**:

```
S_t → A_t → Ŝ_{t+1} → S_{t+1} → δ_t → learning
```

NEXUS-0 (este sprint) = memoria + política + aprendizaje + gate, en
host Python, **sin LLM, sin placa Akida, sin ISO 10**.

Hipótesis científica (no la reescribas):

> echoAI es un agente cognitivo híbrido de dos escalas temporales en el
> que una representación discreta compartida (WSP/QN) conecta percepción,
> memoria, predicción y acción; un sistema rápido entero mantiene el
> estado, aprende de consecuencias y ejerce control; un sistema cortical
> lento genera hipótesis y planes; y un mecanismo de verificación y veto
> impide que las hipótesis del córtex se conviertan en hechos o acciones.

---

## Orden de lectura (obligatorio)

1. Este archivo (invariantes, qué no tocar).
2. `echoai/CLAUDE_SITUATED.md`  ← programa situado, **cerrado**. MVP: `python3 -m echoai.nexus0.demo`.
3. `echoai/docs/STATUS.md`
4. `echoai/docs/CHATGPT_REVIEW.md`  (qué ya está vs qué pide ChatGPT)
5. `echoai/docs/02-INVARIANTS.md`
6. `echoai/docs/05-NEXUS-0-SPEC.md`  — origen; no lo reescribas
5. `echoai/docs/01-INVENTORY.md`     ← qué hay ya en el repo (no lo clones)
6. `echoai/docs/04-DECISIONS.md`     ← qué se tira, qué se queda
7. Código existente a **importar**, no copiar:
   - `navi10_qn.py`
   - `navi10_cam.py`
   - `navi10_wsp.py`
   - `navi10_stdp.py`
   - `navi10_spoke.py`
   - `navi10_dag.py`
   - `kernel/include/wsp.h`
   - `kernel/navi/wsp_lex.c`  (tabla ~150 n-gramas)

No hace falta leer navi5–navi9 para implementar NEXUS-0. No los
importes al núcleo.

---

## Dónde se escribe

| Sitio | Qué va ahí |
|---|---|
| `echoai/nexus0/` | Único código nuevo del sprint |
| `echoai/tests/` | KPI de NEXUS-0 |
| `echoai/lab/` | artefactos de bench (json), no pesos de LLM |
| `echoai/docs/` | ya escrito; no lo reescribas salvo error factual |

**Prohibido en NEXUS-0**

- Nuevo bus de eventos (`SPIKE_EVENT`, `STATE_EVENT`, …).
- `internal_state` en float. E[6] es `int8` ±100.
- Vector DB / embeddings float / FAISS / Pinecone.
- Importar `navi7_lab`, `navi9_self`, `navi75_voice`, `navi86_skills` al núcleo.
- Llamar a LPU / LLM / `think()` de navi10 en el banco principal.
- Clonar `Layer256` / `navi_q6_step`. Se **importa**.
- Meter δ en `E[V]`. δ vive en `Q[4096][3]`.
- Driver Akida, MetaTF, `.fbz` (Cerradura 0 es NEXUS posterior).
- Tocar `kernel/`, ISO, `userland/` salvo que el spec lo pida (no lo pide).
- Afirmar julios de NPU. No hay placa.
- Relabelar edge learning de BrainChip como STDP nuestro.
- Crear `brainstem.py` / `amygdala.py` / `nexus/` paralelo.

---

## Tres canales que no se mezclan

```
REPRESENTACIÓN   ¿qué ocurre?     WSP 16 B + vértice Q_N
EPISTEMOLOGÍA    ¿lo sé?          VERIFY = (d_H ≤ 3) ∧ extracto
CONTROL          ¿qué hago?       Q[s,a] + gate OK|MODIFY|BLOCK
```

**Firewall epistémico:** una hipótesis (córtex) nunca se escribe como
hecho en CAM. `FACT ∈ {VERIFY, DESCONOCIDO}`. La prosa no cambia eso.

CAM = “qué pasó”.  Q-table = “qué debo hacer”.  No son la misma tabla.

---

## Invariantes (rompe uno = bug de producto)

- `sizeof(wsp_packet_t) == 16` (`kernel/include/wsp.h`)
- 0 FPU en el paso rápido (enteros, `//`, popcount)
- CAM 4096 ranuras, `destroyed == 0`
- VERIFY exige extracto; si no, DESCONOCIDO
- Umbral neuronal no decide IRQ / disco / `#PF` / `G_rxos`
- Córtex OFF en el banco principal (`cortex_calls == 0`)
- Q6 1-bit del repo padre no se toca; no bajes 48/48

---

## Definición de hecho (NEXUS-0 verde)

```
cd /home/roger/REALRXOS/RXos
PYTHONPATH=. python3 -m echoai.tests.test_nexus0
# o: python3 echoai/tests/test_nexus0.py
```

Todos los KPI de `echoai/docs/05-NEXUS-0-SPEC.md` §12 en verde,
incluido:

- `false_facts == 0`
- `destroyed == 0`
- `cortex_calls == 0`
- `negative_delta_causes_policy_change == true`
- encoder semántico gana a FNV en `accuracy_rel` sobre el banco vendor

Fases A–G del entorno sintético: el agente parte de Q≈0, 256 turnos,
aprende a no `approach` lo que pega, generaliza un cambio leve del
entorno.

---

## Cómo implementar (orden)

Ya hay un NEXUS-0 mínimo **verde** (`python3 -m echoai.tests.test_nexus0`).
No lo tires. Extiéndelo.

Siguiente trabajo real (no rediseñar):

1. Portar `kernel/navi/wsp_lex.c` al encoder. El banco vendor (6 frases)
   ya gana a FNV; el fallback FNV sigue siendo un agujero para el resto.
2. Meter `seq`/átomos de `wsp_lex` sin romper el KPI de 256 turnos.
3. No enciendas córtex. No importes navi7–9. No MetaTF.

Si algo no está en el spec, no lo inventes. Pregunta.

---

## Hardware

**No hay AKD1000 en el laboratorio.** `neurocpu akida` se niega.
NEXUS-0 es 100 % software LIF + tablas enteras. Akida = coprocesador
futuro de un **head de 3 acciones**, nunca de VERIFY ni de WSP.
Ver `echoai/docs/07-AKIDA.md`.

---

## Tono

Laboratorio. Números o silencio. Si es metáfora, dilo. Si es PLAN, no
lo conjugues en presente. No uses la palabra AGI como objetivo.
