# 07 — Akida AKD1000 (PLAN — no hay placa)

**Actualización 2026-09-09:** Roger fija el destino ECHO-2 en **AKD1500
M.2**. Ver [arranque ECHO-2](ECHO2-START.md) para la ruta vigente y fuentes
oficiales. Este documento conserva el plan histórico AKD1000; sus IDs y
restricciones específicas no certifican compatibilidad con AKD1500.

**Estado de laboratorio: 0 placas.** El interruptor `neurocpu akida`
existe y **se niega**. NEXUS-0 **no espera** silicio. Este archivo
existe para que un agente no “rellene” un NPU.

Fuente canónica del repo: [`docs/AKIDA.md`](../../docs/AKIDA.md).
No la contradigas.

---

## Qué es (hechos de ficha, no marketing nuestro)

- Procesador neural **digital**, event-based, borde. No memristor.
  No QPU. Enteros.
- AKD1000 = Akida **1**: ~20 NPUs, spikes, SoC con Cortex-M4.
- Capas Akida 1: InputData, convolution, separable conv, fully-connected.
  Pesos/activaciones 4/2/1 bit (Akida 2 sube a 8 y TENNs).
- Edge learning (Akida 1, no 2): **solo la última FullyConnected**,
  pesos e inputs **binarios**, `AkidaUnsupervised`. Plasticidad que
  solo baja. **Eso no es STDP de rxOS.** Si se usa, se etiqueta
  *edge learning de BrainChip*.
- Runtime `akida` / MetaTF: **propietario**. No se copia al unikernel
  ni se relicencia GPLv3.
- Simulador: se puede mapear un AKD1000 **virtual** en host Linux
  (`Model.map`) y el mapper rechaza incompatibilidades. Eso es
  Cerradura 0, no NEXUS-0.

Roadmap 2026 de BrainChip (Akida GenAI, TENNs, SSM, LLM-on-chip):
**fuera de este laboratorio hasta que haya ese silicon en mesa.**
No diseñes echoAI como si AKD1000 ejecutara una LLM.

---

## Qué ya hay en el árbol

| Pieza | Dónde | Hoy |
|---|---|---|
| IDs backend | `kernel/event/rx_backend.h` | SOFTWARE \| AKIDA \| LOIHI |
| Switch | `kernel/event/rx_backend.c` | akida available = false |
| Shell | `cmd_neurocpu` | se niega con frase honesta |
| Probe PCI | `drivers/npu/akida.c` | `1e7c:bca1`; sin placa = absent |
| Fabric | `kernel/event/rx_actor.c` | LIF/STDP en CPU |

Un umbral de Akida **nunca** cierra IRQ, disco, red, `#PF`.

---

## Cinco cerraduras (ninguna es NEXUS-0)

Del `docs/AKIDA.md`:

0. **Host MetaTF** — red entera existente (Q6 o **head de 3 acciones**)
   → `quantizeml` → `cnn2snn` → `.fbz` → `akida run`. Tabla software
   vs simulador. Sin placa.
1. **Descubrir silicio** — USB XHCI (hoy **no hay pila USB** en rxOS)
   o MMIO PCIe. `HwVersion` leído o se queda en software.
2. **HardwareDriver** bare-metal — read/write/scratch/visible_mem.
3. **Codec** WSP/Q6 → tensor uint8 `(n,x,y,c)`. G_math / DAG / VERIFY
   se quedan en CPU.
4. **Energía comparada** — RAPL CPU y NPU (o shunt) **mismo chasis**.
   Si falta un lado, no hay tabla. QEMU se rechaza.

ISO pública con NPU: solo tras log MMIO + cifra del mismo chasis
(pitch 2.1 / 2.5).

---

## Encaje con echoAI (cuando NEXUS-0 esté verde)

Hipótesis a probar **primero** (Cerradura 0, simulador):

```
WSP/QN feature tensor uint8
    → extractor pequeño compatible conv/FC
    → binary FC
    → 3 actions
```

### Akida NO decide

VERIFY, hechos, veto, IRQ, disco, `G_rxos`, semántica WSP, Q-table
como fuente de verdad (puede **proponer** a\* ; el gate CPU manda).

### Akida SÍ puede intentar

clasificación de patrón, novedad, head de acción, secuencias cortas.

### No forzar Q6 en el chip

Akida 1 no ejecuta LIF/Q6 arbitrario. Resultado válido de Cerradura 0:
“solo el head mapea; Q6 sigue en software”. Escríbelo. No tuerzas el
cubo.

Orden: software Q6/Q → simulador MetaTF → placa → Engine C++ in-OS.

---

## NEXUS-0

Cero imports `akida`, `metatf`, `cnn2snn`. Cero julios de NPU en el
informe. `backend = "software"`.
