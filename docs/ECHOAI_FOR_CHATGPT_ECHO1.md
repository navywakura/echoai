# echoAI — briefing investigador: de PULPO a **ECHO-1**

**Fecha:** 2026-09-04  
**Remitente:** Roger / Rogex Laboratories  
**Destinatario:** ChatGPT, modo investigador  
**Regla:** este archivo es **el único** input. Distingue **hecho del lab** / **inferencia** / **recomendación** / **lo que no sabes**. Español. No implementes. No vendas consciencia fenoménica. **No hardcodear** políticas, rutas, letreros ni “si pose== entonces”.

Un briefing anterior (`ECHOAI_FOR_CHATGPT_SCALE.md`) y tu respuesta (WALK → 3D → …) ya se ejecutaron en parte. **Estado actual = §1.** El encargo de hoy es **diseñar la etapa siguiente**, que Roger nombra **ECHO-1**, *después* de cerrar el pulpo.

En paralelo, el lab pega a Claude un prompt (`CLAUDE_PULPO.md`) para **cerrar pulpo al 100 %**. Tú asumes que ese cierre **puede** quedar verde (3D-162, walk, desvío al tapar el túnel, córtex off, remainder opt-in). Diseña ECHO-1 **encima** de eso, y di qué harías si pulpo-block sale rojo.

---

## 0. Tu encargo

Investigar **cómo implementar** ECHO-1, la segunda etapa:

> Espacio 3D virtual (más que un cubo 3×3×3). Cuerpo 3D. Consciencia **operacional** de su propio cuerpo 3D. Movimiento 3D. Cambiar de estrategia al tapar un pasillo y **seguir llegando al premio** (si pulpo ya lo tiene, ECHO-1 lo **escala**: más de un tapón, objetos). Herramientas. Ejercicios tipo **mover un objeto de X a Y para cobrar**. Modelo **yo vs mundo**. Uso del LLM para **transmitir** ideas y pensamiento interno a Roger — logs **reales**, no narración inventada.

Prioridad de investigación (contéstalas todas):

1. Arquitectura de ECHO-1 en 6–10 slices, un KPI cada uno, sin romper WSP/I1–I17.
2. Cómo un objeto portable (X→Y) entra en 3 acciones + átomos ya existentes (`UNIR`/`ABRIR`/…) **sin** MiniGrid-8.
3. Self vs mundo: el test de perturbación (cuerpo vs física externa) que ya recomendaste — KPI concreto sobre el cubo 3D.
4. Logs de “pensamiento”: qué es real hoy (`thought.jsonl`, T, Q, ATTEND) vs qué puede **traducir** Qwen **fuera** del loop vs qué sería teatro (CoT que no causó la acción).
5. Espacio 3D *grande* sin explotar `seq` u8 ni CAM 4096 (frames/rooms; **no** robar `ext.domain` lingüístico; I6 CAM no poda).
6. Cuándo llamar al 4B y cuándo no. CONFLICT→ATTEND.

Al final: hoja de ruta ECHO-1, riesgos, mutantes que pondrían rojo un slice, y **lo que no sabes**.

---

## 1. Hecho del laboratorio (2026-09-04, no lo redes)

Tests **260** OK, **1 expectedFailure** (WALK-1 sin resto). Banco anillo default:

```
policy_after [-12, +5, 0]
+80  surprise_known=1  33/1/217
false_facts=0  destroyed=0  cortex_calls=0
remainder default False
```

| Pieza | Número / estado |
|---|---|
| Anillo 32, JUMP, PREGUNTAR | cerrado |
| Pasillo HOME/SHIFT | T se equivoca donde el mundo cambió |
| WORLD-3 | 256 dirs, 17 sitios, 1 arista, transfer_gain=+256 **es avoid**, 0 GOAL en SHIFT |
| SIGN + Qwen3-4B Q4_K_M | CortexROI +16; paráfrasis 6/6 vs stub 0; ~1.62 s/turno; GBNF átomos |
| GUI-2 | poll `/turns.json` 127.0.0.1; `thought.jsonl` 17 claves, **sin prosa** |
| CUERPO-1 | tortuga 5×5×4=100, T 76/76 vs stepper 12/76 |
| WALK-1 | **rojo**: curriculum cobra; examen START 0; `credit_chain(2)=[13,8,4,0,…]` |
| CREDIT-1 | **verde**: remainder opt-in, trunc hacia cero (no `>>` en negativos). Examen `(0,0,E)`: **12 cobros, 192, 10 poses, 0 bumps**. Q camino `[3,4,5,6,-10,9,11,13,15,18]`. Anillo **con** remainder (sonda): `policy_after [-11,+12,0]` → **no default** |

Host: Ryzen 5 5500U, 13 GiB, sin CUDA. Qwen local.

**Pulpo 2D:** planta + caminar **con** resto. **No cerrado:** no hay 3D, no hay “tapas el pasillo y aún cobras” como `goal_hits>0` en `block`.

Claude está cerrando pulpo ahora: `body3d.py`, 3×3×3×6=**162** poses, 6 headings (caras), approach / ciclo de heading / wait, túnel corto + desvío, `block` tapa el corto, remainder on, córtex off, dos exámenes START canónico (`open` y `block` ambos `goal_hits>0`), T vs stepper +X, techo 256 medido no agrandado. **No hardcode.**

Tú diseñas **ECHO-1 asumiendo ese verde**. Si `exam_block_goal_hits=0`, di el plan B (más exploración del desvío, no una 4ª acción mágica).

---

## 2. Invariantes (ganan)

I1 WSP 16 B. I2 layout (átomos + E[6] V,A,D,C,U,B + ext domain/generator/style/slot/seq). I3 0 FPU en el rápido. I4 CAM/Q 4096 estáticos. I6 `destroyed=0` (CAM **no** olvida rooms). I11 banco `cortex_calls=0`. I14 hipótesis ≠ `has_fact`. I15 CAM ≠ Q. I16 δ no en E[V]. I17 un cable.

`parse_reply` no se toca. Oráculo ≠ córtex. `domain` **no** es id de habitación (es GENERAL/CÓDIGO/…). Comprimir = mismo paquete **y** misma dinámica. Remainder y traces: opt-in, no a la vez.

---

## 3. Qué es ECHO-1 (definición de Roger, operacionalízala)

No es AGI. No es delfín místico. Es la etapa **después** del pulpo 3D mínimo:

| Capacidad | Lo que tiene que *hacer* (tú precisas el KPI) |
|---|---|
| Espacio 3D virtual **mayor** que 3×3×3 | Varias celdas/rooms o un cubo que **no** quepa en 162 sin frames. AliasRate→0. |
| Cuerpo 3D + movimiento 3D | Ya nace en pulpo; ECHO-1: inercia / más de un cuerpo-objeto. |
| “Consciencia” del cuerpo 3D | **Self-prediction perturbation**: A = se altera el motor; B = se altera un voxel externo; el agente atribuye mal T a *cuerpo* vs *mundo* mejor que un control sin esa distinción. Cero átomo CONCIENCIA. |
| Estrategia al tapar pasillo | Pulpo pide un tapón. ECHO-1: varios tapones, o tapón **después** de haber memorizado el corto (transferencia, no reentrenar desde cero). |
| Herramientas | `ABRIR` (o el átomo que toque) **solo** con física de tapa/palo. Q pasa a 4096×4 si hace falta, flag, anillo sigue 3. |
| Objeto X→Y | Un ítem con pose; GOAL no paga hasta que el ítem está en Y. 3 acciones: ¿cargar = approach al ítem + approach al destino? ¿Un verbo `UNIR` hacia el objeto? Diseña **sin** 8 acciones. |
| Yo vs mundo | Mismo test que self-model; T_self vs T_world o dos predictores, no un string. |
| LLM transmite pensamiento | Ver §4. |

---

## 4. Logs de pensamiento — la trampa

**Hecho:** `thought.jsonl` es el pensamiento interno **real**: turn, cell/pose, kind, action, reward, WSP compacto, ATTEND, q_row, t_pred, n, s, δ, cortex_action, gate. Enteros y átomos. GUI-2 lo pinta en vivo. **No hay prosa.**

**Teatro:** pedir a Qwen “explica lo que pensaste” y guardar ese párrafo como si hubiera causado el `approach`. CoT póstumo no es el loop.

**Aceptable (recomienda cómo):**

- Traductor **fuera** del loop: lee una línea de jsonl → español (`YO → UNIR → AQUI`, Q `[3,0,0]`, T predice pose 40, surprise=1). GBNF o plantilla. **No** entra en CAM. **No** es `parse_reply`.
- Si ATTEND despertó el 4B, el log **ya** tiene `cortex_action` y el json del turno (`extract`, átomos). Eso sí causó hipótesis.
- Prohibido: segundo bus, WebSocket, “cadena de pensamiento” que el rápido no vio.

Diseña el mínimo traductor (prompt + qué campos) y el mutante: si el español dice “giré porque la pared” pero el jsonl es `wait` en EMPTY, el test es rojo.

---

## 5. Preguntas de implementación (contesta con alternativas y coste)

**A. Objeto X→Y con 3 verbos.** ¿El ítem es una pose más en el mismo encoder? ¿Cargar cambia el índice (agente+objeto = pose compuesta, explosion combinatoria)? ¿Un bit `carrying` en `ext.style`? Límite 256. Mutante: hardcodear `if cell==Y: success`.

**B. ABRIR.** Física mínima puerta/frasco. ¿4ª columna en Q solo en body3d, anillo 3? Transferir T al abrir (el sucesor de approach cambia).

**C. Frames espaciales.** Pulpo cabe en seq. ECHO-1 no. Campo WSP para `frame_id` **que no sea domain**. `style`? nibble? ¿Portal = JUMP 3D? CAM crece con frames distintos (I6 no borra). AliasRate si dos rooms iguales deben **compartir** paquete.

**D. Self vs mundo.** Cómo etiquetar el error de T sin un supervisor humano cada turno. ¿Dos layouts: “suelo resbaladizo” vs “heading invertido”? KPI SelfAttribution vs control.

**E. CONFLICT→ATTEND.** Q alto ∧ T mal → 4B. En ECHO-1 el 4B **no** elige el desvío del laberinto (eso es Q/T). Sí lee un letrero “la tapa gira al revés”. CortexROI>0, false_facts=0.

**F. Remainder.** ¿ECHO-1 default on en mundos 3D y off en el anillo (ya es así) o un n-step después? El anillo **con** remainder ya mueve `[-12,+5,0]→[-11,+12,0]`.

**G. Qué no entra en ECHO-1.** Espejo, segundo agente/empatía, SLEEP, Akida, 24 orientaciones, 70B, MiniGrid.

---

## 6. Formato de respuesta

1. Juicio en una página: pulpo vs ECHO-1; qué queda de “consciencia/herramientas/logs”.
2. Tabla capacidad → KPI → pieza existente o slice → LLM sí/no.
3. Diseño objeto X→Y (3 acciones) y ABRIR.
4. Diseño traductor de jsonl (fuera del loop) + mutante anti-teatro.
5. Hoja de ruta **6–10 slices** ECHO-1, un KPI, orden. Primer slice **después** de pulpo verde.
6. Mutantes / invariantes que rompen cada slice.
7. Lo que no sabes.

La pregunta científica sigue siendo:

> ¿Cuánto puede aprender, predecir y adaptarse **antes** de llamar al córtex — y cuánto mejora **cuando** el córtex traduce o lee un letrero, sin escribir hechos?
