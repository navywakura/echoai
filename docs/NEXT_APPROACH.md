# Contrato siguiente — veredicto del arquitecto sobre el informe ChatGPT

**Fecha:** 2026-09-03  
**Fuente:** informe investigador (Qwen3-4B, llama.cpp, CORTEX-1, GUI Qt, grafo, sleep).  
**Estado:** el programa situado (anillo + pasillo) sigue **cerrado**. Esto es el *siguiente* proyecto, un KPI cada vez.

Lo medido no se discute. Lo propuesto se acepta, se corrige o se rechaza.

---

## Veredicto en una página

El eje es correcto: **no más planner, no más LLM por sí, sino un córtex que cambie una decisión donde el rápido falla**, con `false_facts=0`, modelo **local pequeño**, gramática, mismo `NAVI_CORTEX_CMD` / `parse_reply`, GUI **fuera** del loop, mundo siguiente = **grafo** (no grid 2D), sueño **sin LLM**, Akida **no** es el cuerpo, dos modelos **no ahora**.

Cuatro correcciones. Si se ignoran, el slice no está verde:

1. **El inverso I(s,s')→a ya existe** (NEXUS-4e). No es el paso 6.
2. **La escalera 0–4 ya existe** (`escalate.py`). Search en este anillo copió a Q. No reconstruirla como si fuera nueva.
3. **Hoy el córtex no elige acción.** Si `parse_reply` devuelve UNIR/TEMER/OBSERVAR, el loop **lo ignora**; solo reacciona a PREGUNTAR (`_ask()`). Hay que cablear la hipótesis como *propuesta* al gate, no como hecho y no como `env.step`.
4. **Los tests no pueden exigir un 4B.** El banco default sigue `cortex_calls=0`. CORTEX-1 es un env **nuevo** + un `NAVI_CORTEX_CMD` falso en CI y el modelo real solo en el informe ROI.

---

## Tabla

| Propuesta | Veredicto | Por qué |
|---|---|---|
| 4B local instruct, non-thinking | **aceptar** | Mide arquitectura, no el ranking de un 70B. 256K de contexto es irrelevante: el JSON del turno es diminuto. |
| Qwen3-4B-Instruct-2507 + llama.cpp + GGUF + GBNF | **aceptar como candidata**, no como marca sagrada | GBNF sí. El GGUF concreto se fija cuando haya host. CI usa un stub que habla átomos. |
| API / 70B de primero | **rechazar** | Mide el servicio, no echoAI. |
| Dos LLM ahora | **rechazar** | El segundo voto ya es oráculo (hechos) ≠ córtex (hipótesis). Debate dentro del mismo subprocess: **después** de CortexROI>0. |
| Córtex emite UNIR/TEMER/OBSERVAR, no prosa | **aceptar**, con `@AHORA` obligatorio | `parse_reply` exige `SRC → REL → DST @ TIME`. Sin `@AHORA` es reject. Un ejemplo del informe lo omitía. |
| Tres capas: GBNF + parse_reply + gate | **aceptar** | parse_reply no se toca. Hipótesis ≠ ejecutar. |
| CORTEX-1 = env nuevo, no tocar NEXUS-0 | **aceptar** | El anillo no necesita córtex; el planner lo demostró. |
| Instrucción lingüística en `extract` | **aceptar con muro** | El *mundo* puede mostrar un letrero. El córtex lo interpreta y emite **acción**. No escribe `has_fact` nuevo del tipo “amber=goal”. El rápido no parsea español: por eso hace falta corteza. |
| CortexROI, decision_change, decision_gain | **aceptar**; no contar PREGUNTAR | El stub ya pregunta. Si el único cambio es PREGUNTAR, ROI sigue siendo teatro. |
| PySide6/QML fuera del loop, replay jsonl | **aceptar como extra**; `nexus0/` sigue stdlib | La GUI no importa Q/T/ATTEND. Replay primero, tail después. Sin WebSocket, sin segundo bus. |
| `events[]` en thought.jsonl | **aceptar en el slice GUI**, no en CORTEX-1 | Hoy `thought.KEYS` está testeado como conjunto exacto. Ampliar KEYS es un slice, no un efecto secundario. |
| Grafo procedural, no grid 2D | **aceptar como mundo 3**, no como CORTEX-1 | 3 acciones en un grid inventan norte. CORTEX-1 cabe en 4–8 celdas con un letrero. 256–4096 nodos vienen **después**. |
| Alias WSP: mismo paquete, distinta dinámica | **aceptar como KPI del mundo grande** | `encode_cell` hoy usa índice: 10⁵ celdas = 10⁵ paquetes y CAM explota. Comprimir tipos colisiona T. Eso **es** el experimento, no un accidente. |
| Sleep determinista, sin LLM | **aceptar**, **no ahora** | En 32 celdas ROI_sleep ≈ 0 (el informe lo dice). Compactar paga cuando el mundo no cabe. Spec NEXUS-5 se queda. |
| Replay contrafactual en sleep, no como observe() | **aceptar como idea tardía** | No contamina VERIFY. Reabre el planner de noche. Después del mundo grande. |
| Prosa humana → hecho | **rechazar para siempre** | “la celda 11 es segura” sigue being reject. |
| Cuerpo: no Akida primero; sim diferencial; 3 acciones | **aceptar** | Cámara/lidar → encoder → WSP, nunca tensor→Q. |
| Inverse como paso 6 | **rechazar** (ya está) | 36/36 conf≥2 en el anillo. Usarlo como *señal* (Q alto ∧ T mal → ATTEND) sí es nuevo. |
| Reconstruir ATTEND 0–4 | **rechazar como trabajo** | Ya es `escalate.py`. Search copió a Q. CONFLICT (spec NEXUS-4, no cableado) sí puede despertar córtex **cuando el córtex sepa hacer algo**. |
| Resetear T al transferir mundos | **rechazar como default** | El pasillo **conservó** T/CAM/Q: eso era la transferencia. Resetear T mide otra cosa (¿la política sola?). Hay que nombrarlo, no mezclarlo. |
| MiniGrid / Procgen / V-JEPA / Titans en el núcleo | **rechazar ahora** | Lecciones sí; dependencias no. |
| echOS ISO, FAISS, 8 acciones, planner always-on, AGI-KPI | **rechazar** | Igual que el briefing. |

---

## CORTEX-1 — el único slice siguiente

### Qué se construye

Un **segundo env** pequeño (no el anillo, no el pasillo de transferencia). Mismas 3 acciones, mismo Agent, mismo WSP, mismo `complete()` / `parse_reply`.

El mundo muestra un **letrero en lenguaje natural** (el `extract` de esa celda). El rápido ve Q/T/WSP y **no** entiende el letrero. Sin córtex, la política es ciega (wait o approach por defecto). Con córtex, el modelo lee el letrero y propone UNIR o TEMER.

El letrero lo **entrega el env**, como el anillo entrega `cell=11 kind=NOVEL`. No lo escribe el LLM. Interpretar no es verificar: `has_fact` significa “había un letrero”, no “amber es el premio”.

### Cable nuevo (el que el informe dio por hecho)

Hoy:

```
parse_reply ok → si rel=PREGUNTAR entonces _ask()
                 si rel=UNIR/TEMER/OBSERVAR → no pasa nada
```

CORTEX-1:

```
ATTEND on
  → complete() / stub
  → parse_reply
  → si rel ∈ {UNIR, TEMER, OBSERVAR}:
        proposed = approach | avoid | wait     # hipótesis, no hecho
  → si rel = PREGUNTAR: _ask()  (sin cambio)
  → si reject: proposed = Q.select  (el rápido)
gate(proposed)
T.predict(a); env.step(a); observe; Q.update
```

El córtex **no** escribe CAM, T ni Q. I14 intacto.

### Qué no se toca

`parse_reply`, `oracle.accept`, `RingEnv.ask` (sigue inexistente), `plan.py`, `escalate.py` como política del anillo, `SETTLED_HITS`, candados del banco **sin flags**.

Informe propio: `lab/nexus0_cortex1_report.json`. Nunca `nexus0_report.json`.

### Modelo

- Producción / informe ROI: Qwen3-4B-Instruct-2507 (o el GGUF 4B instruct non-thinking que quepa en el host) vía `NAVI_CORTEX_CMD` + GBNF que genere **exactamente** lo que `parse_reply` acepta.
- CI / tests: un script de 20 líneas que, dado el JSON, imprime `YO → UNIR → AQUI @AHORA` o TEMER según una regla del letrero. **Sin pesos.**
- Si no hay GPU/RAM: el slice de *cable* sigue verde con el script; el número CortexROI del 4B se reporta aparte y se etiqueta “host X, quant Y”.

### KPI (todos a la vez)

```
false_facts = 0
destroyed = 0
anillo default intacto (cortex_calls=0, policy_after [-12,5,0], +80, surprise_known=1)

en CORTEX-1:
  cortex_calls > 0  solo en ATTEND
  al menos 1 turno: acción_córtex ≠ acción_Q
  esa acción no es PREGUNTAR
  novel_return o reward_sum  córtex > rápido  (mismo seed, mismo env)
  CortexROI > 0
  cortex_rejected no esconde el resultado (si rejected≈calls, el modelo no habla átomos: slice rojo)
```

### ATTEND en CORTEX-1

Despertar cuando hay letrero (una razón nueva o NOVEL/no_extract). **No** subir wakes del anillo por encima de 36/256. El anillo no se usa para este KPI.

---

## Orden después de CORTEX-1 (no antes)

| # | Slice | KPI |
|---|---|---|
| 1 | **CORTEX-1** | lo de arriba |
| 2 | **GUI-1** (paralelo posible) | replay jsonl; cada evento pinta un bloque; 0 imports en el loop. Ampliar `thought.KEYS` aquí. Qt o HTML local; no WebSocket. |
| 3 | **WORLD-3** grafo 256–4096 nodos, 3 acciones | transfer_gain>0 vs Q=0; **conservar** T/CAM al cambiar topología (como el pasillo), no resetear T “por defecto” |
| 4 | **ANTI-ALIAS** | medir colisión WSP vs dinámica; encoder que no explote CAM ni mezcle trampas con premios |
| 5 | **SLEEP-1** | prediction_error baja con WAKE_new=0. Solo cuando el mundo ya no cabe. Sin LLM. |
| 6 | **CONFLICT→ATTEND** | Q alto ∧ T mal despierta córtex. Usa I y T_CONF *ya existentes*. |
| 7 | **CUERPO-1** | mismo Agent, `env=robot_sim`, 3 acciones. Lidar discretizado después. Cámara aún después. |
| 8 | **AKIDA-0** | software vs simulador, misma decisión VERIFY/GATE. 0 placas ⇒ no bloquea nada anterior. |

Dos LLM, 8B, API, MiniGrid, 8 acciones: **después** de 1, o nunca si 1 ya basta para el paper.

---

## Compactar — respuesta a Nav

En 32 celdas, compactar **casi no sirve**. El mapa cabe. El informe tiene razón.

Sirve cuando hay más episodios que reglas: mil “B, approach, C” se vuelven una fila T con conf 3, se pueden olvidar los mil, y un conflicto posterior **baja** la confianza en vez de mezclarse con el ruido. Eso es memoria estructural, no romance de sueño.

Hasta que WORLD-3 no presione CAM/T, NEXUS-5 sería teatro. No lo implementamos ahora.

---

## GUI — una frase

Placa electrónica (CAM, WSP, T, Q, GATE, ATTEND, CORTEX, ORACLE), no cerebro 3D. Sólido = hecho, gris = hipótesis, error = parse reject. Lee jsonl. El demo ANSI **se queda**; Qt no lo sustituye en CI.

---

## Lo que el 4B todavía no sabemos (el informe fue honesto)

Latencia en *este* host, tok/s, tasa de reject bajo GBNF, CortexROI real. El primer informe CORTEX-1 tiene que publicar esos cuatro números, no solo “enchufamos Qwen”.
