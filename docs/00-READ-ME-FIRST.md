# 00 — Tesis (una página)

**Fecha:** 2026-09-03. Evolución del proyecto: [roadmap](ROADMAP.md).
**Hardware Akida:** no hay placa. El fast loop es software.

## Qué es

echoAI no intenta construir un cerebro humano ni agrandar una LLM.
Construye un **ciclo cerrado** que permanece activo con el córtex apagado:

```
percepción → memoria → predicción → acción → consecuencia → aprendizaje
```

Formulación que sobrevive (investigación 2026 + inventario del repo):

> echoAI = un sistema cognitivo de dos tiempos, donde el estado rápido
> aprende y controla, el sistema lento abstrae y propone, y **ninguno
> de los dos tiene por sí solo la representación completa de la realidad**.

## Qué no es

- AKD1000 = cerebro reptiliano, LLM = neocórtex. **Descartado.**
- navi10 `--ask` como sustrato. `--ask` es un router (intent → plantillas
  / RAG → compositor). El SNN está lateralizado. echoAI **no se construye
  alrededor** de ese router: navi10 debe **dejar de ser el router** y
  convertirse en interfaz de un sistema que ya tiene estado, memoria,
  predicción y acción.
- Un árbol `nexus/amygdala.py` al lado de rxOS.

## Tres cosas que hay que separar (hoy están pegadas)

| Canal | Pregunta | Artefacto |
|---|---|---|
| Representación | ¿Qué ocurre? | WSP 16 B + vértice Q_N + CAM |
| Epistemología | ¿Lo sé? | VERIFY / DESCONOCIDO / extracto |
| Control | ¿Qué hago? | Q[s,a] + gate + 3 acciones |

Una LLM mezcla las tres y finge confianza. echoAI las obliga a no
cruzarse sin comprobación (**epistemic firewall**).

## Fast Control Substrate (no “reptiliano”)

```
Q6/Q_N + CAM + E[6] + STDP + Q-table + GATE + WSP
```

El AKD1000, cuando exista, acelera **poblaciones** (head de 3 acciones,
novedad, secuencia). No decide VERIFY, hechos, veto, IRQ, disco, `G_rxos`
ni la semántica WSP.

## Principio rector

El córtex es un recurso caro. CAM hit + VERIFY + C alta + acción
conocida → **no se llama**. UNKNOWN o plan complejo → entonces sí.

## Primer experimento

NEXUS-0: entorno sintético, 3 acciones (`UNIR` / `TEMER` / `OBSERVAR`),
Q-table 12 KiB, world model T(s,a) entero, córtex OFF, 256 turnos,
δ negativo cambia la política. Spec: `05-NEXUS-0-SPEC.md`.

No se avanza de peldaño en `06-LADDER.md` hasta que el KPI del actual
esté verde.
