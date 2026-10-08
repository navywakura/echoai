# 01 — Inventario del repo (hechos, no visión)

Corte: 2026-09-03. Si no hay archivo o KPI, no está hecho.

echoAI **reutiliza** esto. No lo vuelve a escribir. No construye un
sistema paralelo “alrededor de navi10”.

---

## 0. Tres capas del unikernel (ISO 2.1) + un artefacto host

| Capa | Qué | Dónde | Estado |
|---|---|---|---|
| 1. Tejido | SEB + actores LIF Q16.16, idle HLT | `kernel/event/` | en ISO 2.1 |
| 2. SNN app | Q6 64 LIF, PRISMA 5 sintético, NAVI-3 WSP | `kernel/navi/`, `userland/cli/prisma5.c` | en ISO 2.1 |
| 3. Silicio | probe PCI Akida `1e7c:bca1` | `drivers/npu/akida.c` | PLAN: sin placa = `absent` |
| 4. Host mind | `./navi10` Python + TUI Rust | raíz del repo, `tui/navi10-rs` | **fuera de ISO 2.1** |

2.1 es consola, event-driven, superficie honesta. Echo AI no va dentro
(`docs/ECHOS_2.1_HONEST.md`, `.gitignore` de esa línea).

---

## 1. RogexWSP — dos formatos, un nombre

### A. Vendor `vendor/RogexWSP/`

Protocolo de laboratorio `L = G[S(M,I,E)]`. 32 átomos + E[6]
(V A D C U B). Máscaras: JSON, compacto, binario **variable**, WAV,
SVG, web. v0.1 … v0.5 Hail Mary (polifonía, gramática etiquetada,
plano científico 32–127). Tests, galería, CLI `wsp`.

El binario vendor **no es de 16 bytes**. Cabecera `WSP` + versión + N
paquetes. Conceptos derivados de longitud variable.

Frases canónicas para el banco del encoder (NEXUS-0):

| Texto | rel esperado (aprox.) | Archivo |
|---|---|---|
| te quiero | AMOR (32) o DESEAR | `examples/te_quiero.json` |
| estoy aqui | SER | `examples/estoy_aqui.json` |
| estoy solo pero quiero conectar | SOLEDAD + DESEAR/CONEXION (2 paquetes) | `examples/estoy_solo_pero_quiero_conectar.json` |
| peligro | TEMER / PELIGRO | gallery `peligro` |
| no tengan miedo de lo que no conocen | TEMER invertido / DESCONOCIDO | `examples/no_tengan_miedo.json` |
| quiero hablar contigo en la wired | DESEAR + COMUNICAR + WIRED | `examples/quiero_hablar_contigo_en_la_wired.json` |

SPEC: `vendor/RogexWSP/docs/SPEC.md`, `SPEC_V0.5.md`.

### B. Kernel `kernel/include/wsp.h` — otro “v0.5”

```
src rel dst time     uint8  0..47
E[6]                 int8   V A D C U B  ±100
flags                L2 / RULE / VETO
ext                  domain, generator, style, slot, seq
sizeof == 16
```

Átomos 0–31 = primitivos SPEC. 32–39 = AMOR, SOLEDAD, COMUNICAR,
CONEXION, PELIGRO, BIENVENIDA, CONCIENCIA, WIRED. 40–43 = NONE, UNK,
HELP, PAD.

Código in-OS:

| Archivo | Rol |
|---|---|
| `kernel/navi/wsp.c` | encoder ES **por keywords**, no parser |
| `kernel/navi/wsp_lex.c` | ~150 n-gramas, first-match-wins, rellena el paquete entero |
| `kernel/navi/wsp_gen.c` | G_talk … G_teach |
| `kernel/navi/wsp_mem.c` | anillo 16 + anáfora |
| `kernel/navi/wsp_rxos.c` | lista blanca → `commands_dispatch` |
| NAVI-3 | transductor L3 ternario + veto L2 HDC (`WSP_FLAG_VETO`) |

`wsp_lex.c` es el precedente del encoder semántico. Portar la idea
(tabla, keys largas primero, átomos + E + gen), no el C al host
tal cual si no hace falta: se puede reimplementar en Python leyendo
las mismas reglas y el banco vendor.

### C. navi10 `navi10_wsp.py`

Mismo layout 16 B. **`event_to_wsp()` es FNV del texto.** Átomos =
`h % 32`, etc. Eso **no es pensamiento**. NEXUS-0 lo usa como
baseline a **perder**.

SEB tiene canal `SEB_CH_WSP`. Pool Heap-0 WSP 64 KiB.

---

## 2. Q6 / Q_N

### Q6 — lo único falseado como SNN

RFC: `NAVI_AI_SNN/RFC-2026-08-Q6.md`.

64 LIF, hipercubo grado 6, 192 aristas, codebook lineal **[6,3,3]**
8 palabras `0,7,25,30,42,45,51,52`. Hop gated radio 2.

```
Q6_0BIT      8/8
Q6_1BIT     48/48
Q6_2BIT      8/120
Q6_2BIT_HAM 120/120
DENSE_1BIT   6/48
```

Implementado en:

- `NAVI_AI_SNN/c/navi_q6.c` + `python/q6_*.py`
- `kernel/navi/navi_q6.c` (actor blando; self-test boot 48/48)
- `userland/cli/prisma5.c` (drive **sintético**, no EEG)
- CLI `navi fire`, `navi joules` (RAPL o negativa honesta)

Q6 no habla. Es ECC por atractor.

### Q_N (navi10)

Producto **Q8×Q8**: 65536 direcciones, LIF en **un spoke de 256**,
Hamming `popcount` O(1), codebook [8,4,4] 16 palabras.

```
Q8_CODEWORDS = 0,177,210,99,228,85,54,135,120,201,170,27,156,45,78,255
```

C: `NAVI_AI_SNN/qn/navi_qn.c`. Python: `navi10_qn.py` (`Layer256`).
**Importar. No clonar.**

---

## 3. CAM Heap-0

`navi10_cam.py` + struct C `navi10_cam_slot_t` (32 B en el núcleo):

```
wsp[16] vertex:u16 latency:u16 hits:u16
occupied flags persona E[6] weight has_fact
```

Host añade extract/source/label/kind/see/keys (no caben en 32 B).
4096 ranuras. Lookup FNV + Hamming. `destroyed` debe quedar 0.
`navi10_dag.allocate` reserva ranura en miss si plasticidad ON.

Flags: FACTUAL 0x01, ACTION 0x02, INHIBIT 0x04, METAPATH 0x08, ACTIVE 0x80.

---

## 4. Stream-to-Spoke, STDP, E[6]

- `navi10_spoke.py`: bytes → ventanas por delimitador → SimHash-16 +
  latencia (nibble alto) → ticks 256 neuronas. **No parsea español.**
- `navi10_stdp.py`: LTP/LTD int8 en `w_dim[8]`. Gates: C, U, A.
  Clamp peso ±40. `edge_energy = 32 - w`.
- Esto **no** es aprendizaje de política de 3 acciones. NEXUS-0 añade
  Q-table. STDP del spoke puede seguir existiendo; no sustituye a Q.

---

## 5. Diagnóstico navi10 (imprescindible)

`NAVI10Engine.think()` / `--ask` **no es un SNN que piensa**.

1. Intent por substrings (`navi10_intent.py`): TALK / FACT / EXEC.
2. TALK → plantillas (`navi9_self`, `say_self_intent`).
3. EXEC → `ifconfig.me` / `/proc`.
4. FACT → CAM + harvest wiki/PDF + crítico de sujeto.
5. LPU de servicio = compositor de marcos (`navi10_lpu.py`, n-gramas
   + ROM 8 ejes + atención entera). **No** muestrea el transformer.
6. `ingest()` sí corre Stream-to-Spoke y cuenta spikes. WSP de salida
   suele ser FNV.

Sedimento: importa `navi7_lab`, `navi9_self`, `navi75_voice`,
`navi86_skills`, `navi9_echo`, …

LPU-S ~57.68 M: overfit 32 líneas de `docs/NAVI10.md` (loss 9.24→0.0098).
`.pt` / `navi_lpu_weights.bin` de lab. **No está en `--ask`.**

TUI `tui/navi10-rs`: tesseract 4D, log WSP. Cara, no cerebro.

Meta `--meta`: señuelo Haldane-Koff INHIBIT, trampas, ACTION_REQ,
persona 0x00FF. Útil como precedente de veto, no como NEXUS-0.

**Conclusión para echoAI:** navi10 es interfaz y almacén (CAM, spoke,
qn). El bucle cognitivo nuevo vive en `echoai/nexus0/`. No envuelvas
`think()`.

---

## 6. Veto que ya existe (reutilizar la semántica)

- NAVI-3 L2: `hdc_sim` bajo → corrige átomos/E, `WSP_FLAG_VETO`.
- CAM `SLOT_FLAG_INHIBIT`.
- NAVI 9: LLM opcional atada al extracto; VERIFY de tokens o se cita
  el extracto crudo (`docs/NAVI9_HYBRID.md`).
- `G_rxos` lista blanca.

NEXUS-0 gate: función pura que **devuelve** OK/MODIFY/BLOCK. No
ejecuta syscalls.

---

## 7. L2 / L3 / NAVI-3 (contexto, no dependencia NEXUS-0)

- L2 HDC 1024 + RWKV ternario, ~66 KiB BSS (`NAVI_AI_SNN/l2/`,
  `kernel/navi/navi_l2.c`). Pesos L2 **no entrenados** de verdad;
  prototipos HDC.
- NAVI-3: habla WSP, no castellano. Encoder keywords. Pesos
  `NAVI3W01` ~474 KiB. Máscara ES = `G_*` determinista.

No los importes en NEXUS-0.

---

## 8. PRISMA / SEB / Heap-0

- PRISMA 5: seno entero 64, cubo Q6, `prisma5 stress`. No EEG.
- SEB: spikes 16 B aligned, canales timer/kbd/mouse/pci/net/WSP/sys.
- Heap-0: contrato **parcial**. `kmalloc` vive. Actor NAVI viejo usa
  kmalloc. Auditoría `docs/AUDIT_2.0.md`. NEXUS-0 host puede malloc
  en tests; el step de Q/T/CAM no.

---

## 9. Akida (detalle en `07-AKIDA.md`)

Hook: `kernel/event/rx_backend.c`. `available(akida)==false`.
Cinco cerraduras en `docs/AKIDA.md`. 0 cerradas. 0 placas.
Akida 1: InputData, conv, separable, FC enteros. Edge learning =
última FC binaria. **No come LIF/Q6 arbitrario.**

---

## 10. echo/ (producto viejo, no el workspace)

`echo/echo_router.py` + `docs/ECHO_MODELS.md` hablan de Echo-Lang /
Echo-Code / Echo-Sys. Está gitignorado en la línea 2.1. No es
NEXUS-0. No lo extiendas. El workspace nuevo es **`echoai/`**.

Echo protocolo (tipos de acto: meaning, hypothesis, …) vive en
`docs/ECHO.md` y navi9. El firewall usa esa distinción: hypothesis
≠ fact.

---

## 11. Tests existentes que no se rompen

No regresiones:

- `tests/test_navi10.py` y familia `test_navi10_*.py`
- Q6: `make -C NAVI_AI_SNN` / resultados `NAVI_AI_SNN/results/latest.txt`

NEXUS-0 añade `echoai/tests/`. No reescribe los tests de navi10.
