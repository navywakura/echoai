# 06 — Escalera NEXUS (no avanzar sin KPI)

Cada peldaño demuestra una capacidad que el anterior **no** tiene.
Si un componente no entra en `S→A→ŝ'→S'→δ`, no entra al núcleo.

```
NEXUS-0   memoria + política + aprendizaje          ← este sprint
NEXUS-1   world model que gana al baseline
NEXUS-2   planificación multi-paso / contrafactuales
NEXUS-3   adquisición activa (UNKNOWN → PREGUNTAR)
NEXUS-4   córtex: hipótesis WSP, ATTEND, firewall
NEXUS-5   consolidación “sueño” (episodios → reglas T)
NEXUS-6   embodiment / multimodal (SKU Edge)
NEXUS-7   transferencia de tarea abierta
```

No hay NEXUS-8 “AGI”.

---

## NEXUS-0  (ahora)

Ver `05-NEXUS-0-SPEC.md`.

Puerta: `negative_delta_causes_policy_change` ∧ `false_facts==0` ∧
`cortex_calls==0` ∧ `encoder_beats_fnv`.

---

## NEXUS-1  world model

Añade: T consolidado por mayoría; `prediction_accuracy` **>** baseline
“predecir el mismo vértice / misma ranura”.

No añade LLM. No añade search.

Puerta: en el mismo env, error Hamming medio de T < error del
predictor constante.

---

## NEXUS-2  search / contrafactuales

```
T(S,A), T(S,B), T(S,C)  →  predicted Q/r  →  gate elige
```

Un paso de lookahead (o k=2 máximo). Sin LLM.

Puerta: en un env donde wait es local-greedy pero approach→GOAL a
distancia 2 paga más, el agente elige approach. NEXUS-0 no lo hace.

---

## NEXUS-3  PREGUNTAR

UNKNOWN deja de ser solo fallo: si el goal depende de una variable
ausente, emite WSP `rel=PREGUNTAR`. Un oráculo de test responde; CAM
graba; la acción siguiente usa el hecho.

Puerta: tasa de éxito con oráculo > tasa ciega. Sin oráculo, sigue
DESCONOCIDO (no inventa).

---

## NEXUS-4  córtex

ATTEND = MISS ∨ UNCERTAIN ∨ NOVEL ∨ CONFLICT ∨ GOAL_COMPLEX ∨ HUMAN.

Córtex (LPU o LLM opcional) **solo** emite ≤3 paquetes WSP `G_plan`.
No hechos. No acciones directas. Firewall: prosa no escribe CAM
factual. VERIFY de tokens si hay extracto.

Puerta:

- banco principal **sigue** pasando con `cortex=0`;
- con `cortex=1`, `cortex_calls` > 0 **solo** en ATTEND;
- 0 hechos nuevos sin extracto.

Planner / explainer / hypothesis como **tres salidas WSP** es
evolución *dentro* de 4, no un árbol de productos.

---

## NEXUS-5  sueño

WAKE: percibir, actuar, aprender.
SLEEP: episodios → si S,A → S' de forma consistente, T se marca
estable; Q no se reentrena con prosa.

Puerta: tras sleep, `prediction_accuracy` sube sin nuevos turnos
WAKE. chat.jsonl es input de sleep, no de `--ask`.

---

## NEXUS-6  cuerpo

SKU Edge: WSP+Q6+CAM+Q+gate, **sin** LPU. Sensores/actuadores
reales o el mismo env en el unikernel. USB/Akida si hay placa.

Puerta: el **mismo** bucle NEXUS-0 corre importando el C de Q6, no
solo Python. No es ISO 2.1. No es desktop.

---

## NEXUS-7  transferencia

Un segundo env (distinto layout, mismas 3 acciones). Q/T del
primero dan un arranque mejor que Q=0. Si no, no hay transferencia
que publicar.

---

## Akida en la ladder

No es un peldaño. Es un **backend** del head de 3 acciones a partir
de NEXUS-0 verde + Cerradura 0 (simulador). VERIFY permanece CPU.
Ver `07-AKIDA.md`.
