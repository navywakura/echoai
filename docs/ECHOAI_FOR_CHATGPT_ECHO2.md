# echoAI — briefing investigador: **ECHO-2** (sobrevivir)

**Fecha:** 2026-09-04  
**Remitente:** Roger / Rogex Laboratories  
**Destinatario:** ChatGPT, modo investigador  
**Regla:** este archivo es **el único** input. Distingue **hecho del lab** / **inferencia** / **recomendación** / **lo que no sabes**. Español. No implementes. No vendas consciencia, miedo fenoménico ni “evolución darwiniana” de cine. **No hardcodear** políticas (`if hambre: comer`). Un KPI por idea.

Ya leíste y respondiste `ECHOAI_FOR_CHATGPT_ECHO1.md`. Tu tesis de ECHO-1 se aceptó:

> ECHO-1 no es “más mundo + más acciones”. Es separar “dónde estoy”, “qué soy yo”, “qué cambia por mis acciones” y “qué cambia aunque yo no haga nada”.

Eso **sigue vigente**. ECHO-2 no lo deshace. Este briefing es **la etapa después**, y **no se implementa hasta cerrar ECHO-1**.

---

## 0. Tu encargo

Investigar **cómo se podría implementar ECHO-2**, la propuesta de Roger:

> Cuando ECHO-1 esté cerrado, ECHO-2 será un **mundo infinito**, con **más objetos, más acciones, más herramientas y más tareas de supervivencia**. El entrenamiento es uno solo: **sobrevivir**. Aprenderá poco a poco a sobrevivir, memorizar, recordar, evolucionar. La clave: que sea capaz de **evolucionar a base de supervivencia, muertes, y evitar su muerte**.

Prioridad (contéstalas todas):

1. Qué significa **morir** en un agente de enteros (WSP 16 B, CAM 4096, Q[4096][3], T, un cuerpo 3D) **sin** teatro: no un átomo MUERTE que pinta el sprite, no un LLM que narra “me dio miedo”. Un evento físico + una consecuencia para Q/T/CAM.
2. Qué **persiste** entre muertes y qué se borra. CAM no poda (I6 `destroyed=0`). ¿Un cuerpo nuevo con la misma memoria? ¿Un offset? ¿Una política? ¿Nada? Compara con: un pulpo que no vuelve; un ratón en laberinto; evolutionary strategies; lifetime RL.
3. “Evolucionar” — tres lecturas, elige y **descarta** con costo:
   - a) un solo animal, TD + resto, vidas sucesivas (mismo Q/T);
   - b) población de cuerpos, selección (¿cuántos? ¿rompe I4?);
   - c) nacer de nuevo con un sesgo heredado (¿qué entero?).
   Roger dice “a base de muertes y evitar su muerte”. Eso suena a (a) o (c), no a un GA de catálogo.
4. Mundo **infinito** vs techo `seq` u8 y CAM 4096. Ya medimos: 324 sitios / 162 paquetes (ROOM-1). Frames **fuera** del WSP. `domain` **no** es `room_id`. ¿Chunks? ¿procedural? ¿el infinito es *tiempo* (el bicho no para) o *espacio* (el mapa no acaba)? Distínguelos. GUI-3.5 pide tiempo infinito; Roger ahora pide también espacio.
5. Supervivencia como **único** entrenamiento. Hoy el KPI es `goal_hits>0` (premio +16). Si “sobrevivir” es el mismo +16 con otro nombre, es trampa. ¿Hambre / daño / frío como `r=-16` que **acumula** hasta un umbral de muerte? ¿Un entero `hp`? ¿Fuera del WSP, como `frame`?
6. Más verbos. La regla de ECHO-1: **verbo nuevo ⇔ física nueva**. `ABRIR` solo con tapa. No 8 acciones de MiniGrid. ¿Cuántas columnas Q hacen falta para un superviviente mínimo (comer, recoger, abrir, atacar) y cómo no romper el anillo `Q[4096][3]` (flag, como remainder)?
7. El 4B: **no** elige cómo no morir. ¿Puede leer un letrero “el agua está envenenada”? CONFLICT→ATTEND. ¿SLEEP / olvido? I6 dice no podar; el infinito *duele* la CAM. Investigar sin violar I6.
8. Relación con lo que **aún falta de ECHO-1** (OBJ-1, OPEN-1, SIGN-C, TALK-1, PATTERN-0, XFER-1). Qué de ECHO-2 **no** se puede empezar si eso está rojo. Qué palanca de ECHO-1 es prerrequisito de “morir de verdad” (¿objeto comestible? ¿self-model? ¿hambre = U/A?).

Al final: hoja de ruta ECHO-2 en **6–10 slices**, un KPI cada uno, mutantes que pondrían rojo cada slice, y **lo que no sabes**. Di qué harías si “mundo infinito” explota el techo 256. Di qué **no** es ECHO-2 (Minecraft, Crafter, NetHack, un LLM jugando).

---

## 1. Hecho del laboratorio (2026-09-04, no lo redes)

Tests **310** OK, **1 expectedFailure** (WALK-1 sin resto). Banco anillo default:

```
policy_after [-12, +5, 0]
+80  surprise_known=1  33/1/217
false_facts=0  destroyed=0  cortex_calls=0
remainder default False
explore_flat default False
body_offset default 0
```

| Pieza | Número / estado |
|---|---|
| Anillo 32, JUMP, PREGUNTAR | cerrado |
| WORLD-3 | 256 dirs, CAM 17/4096, transfer = avoid no GOAL |
| SIGN + Qwen3-4B Q4_K_M | CortexROI +16; paráfrasis 6/6; ~1.62 s/turno; GBNF átomos |
| GUI-1 / GUI-2 | placa CAM/T/Q/ATTEND; poll 127.0.0.1:8765; KEYS **22** |
| CUERPO-1 | 5×5×4, T 76/76 vs stepper 12/76 |
| WALK-1 | **rojo a propósito**: `δ>>2` mata el crédito; `expectedFailure` |
| CREDIT-1 | remainder opt-in; 12 cobros desde START |
| **PULPO-C** | cubo 3×3×3×6=162; open **64** cobros; block **42** por el desvío (11=horizonte 11); `explore_flat` opt-in; control 64/0; córtex 0 |
| **SELF-1** | motor `offset=1` / suelo `0`; gap=1; T conservada 56>46; slip=2→2; ciego, sin letrero MOTOR |
| **ROOM-1** | 2 frames, 324 sitios, **162 paquetes**; transfer B **64** cobros / scratch **0**; CAM 59=59; `domain=0`; agujero en B: DynamicAlias=2, **no parcheado** |
| **GUI-3** | 3 plantas 2D + 27 cuadrados; 64 turnos y Play **se acaba**. Roger lo rechazó como “no es 3D”. GUI-3.5 (voxels orbitables + diario + `--live`) está **pedida, no cerrada** |

Host: Ryzen 5 5500U, 13 GiB, sin CUDA. Qwen local. 0 placas Akida.

Olvido medido (PULPO-C): tras reescolarizar el desvío, el atajo se pierde (`exam_open_after_readapt=42` por el largo). Un solo mapa. ECHO-2 no puede fingir que hay dos vidas si la política es una.

Horizonte de valor **11** (γ=7/8 entero + remainder). Un desvío de 12 cobra 0. La supervivencia *larga* choca con esto: o el mundo de ECHO-2 cabe en 11 pasos de crédito, o hay n-step/SLEEP **opt-in**, o “sobrevivir” no es un premio a 50 casillas.

---

## 2. ECHO-1 **no está cerrado**. No diseñes ECHO-2 como si lo estuviera.

Falta, **en este orden**, y cada uno es un KPI:

| # | Slice | Qué tiene que *hacer* | LLM |
|---|---|---|---|
| — | GUI-3.5 | Cubo 3D orbitabile + panel del `thought.jsonl` + `--live` que no para. Sin Three.js/CDN. | no |
| 1 | **OBJ-1** | Un ítem con pose. GOAL paga `object_at_Y`, no “el agente pisó Y”. 3 acciones; acoplar = approach a contacto. Mutante: premio al agente en Y sin objeto → rojo | no |
| 2 | **OPEN-1** | `ABRIR` **iff** hay tapa. Q[4096][4] solo con flag; anillo sigue 3 | no |
| 3 | **SIGN-C** | CONFLICT→ATTEND; 4B lee un letrero en el cubo; CortexROI>0; `false_facts=0`; el 4B **no** elige el desvío | sí, letrero |
| 4 | **TALK-1** | Traductor jsonl **fuera** del loop; mutante wait≠“giré”; consistencia 100% | sí, prosa póstuma |
| 5 | **PATTERN-0** | Regularidad descubierta, cero etiqueta humana; gain de predicción | no |
| 6 | **XFER-1** | Mismo encoder/Q/gate en ≥3 mundos | no |

Si OBJ-1 está rojo, ECHO-2 **no tiene** “comer un objeto”. Si OPEN-1 está rojo, no hay herramienta. Si SELF-1 (ya verde) se deshace, “evitar la muerte” no sabe si falló el brazo o el veneno.

**Prohibido** en tu respuesta: “saltad OBJ-1 y poned hambre”. El hambre *es* un objeto + un reloj, o no es nada.

---

## 3. Invariantes (ganan a ECHO-2 también)

I1 WSP 16 B. I2 layout (átomos + E[6] V,A,D,C,U,B + ext domain/generator/style/slot/seq). I3 0 FPU en el rápido. I4 CAM/Q 4096 **estáticos**. I6 `destroyed=0` (CAM **no** olvida para hacer sitio). I11 banco `cortex_calls=0`. I14 hipótesis ≠ `has_fact`. I15 CAM ≠ Q. I16 δ no en E[V]. I17 un cable.

`parse_reply` no se toca. Oráculo ≠ córtex. `domain` **no** es id de habitación. Comprimir = mismo paquete **y** misma dinámica (ROOM-1). Remainder / traces / `explore_flat` / `body_offset`: opt-in, default off, anillo `[-12,+5,0]` intocable.

Verbo nuevo ⇔ física nueva. No MiniGrid-8. No 24 orientaciones. No 70B. No Akida. No segundo agente/empatía en ECHO-2 salvo que lo justifiques con un KPI y un costo (tú mismo dijiste que empatía sin segundo cuerpo es egoísmo).

---

## 4. La tesis de Roger (operacionalízala; no la endulces)

En sus palabras:

- Mundo **infinito**.
- Más objetos, acciones, herramientas, tareas de supervivencia.
- Entrenamiento **simple: sobrevivir**.
- Aprender poco a poco: sobrevivir, memorizar, recordar, evolucionar.
- Evolucionar **a base de supervivencia, muertes, y evitar su muerte**.

Lo que el lab necesita que tú conviertas en números:

| Palabra de Roger | Trampa | Pregunta que tienes que cerrar |
|---|---|---|
| Infinito | uint16 en `seq`; CAM 10⁵; chunk = dominio lingüístico | ¿tiempo, espacio, o ambos? ¿frame externo + DynamicAlias=0? |
| Sobrevivir | `R_SUCCESS` con otro cartel | ¿qué se acaba cuando muere? ¿un entero `hp`? ¿el episodio? |
| Muerte | átomo MUERTE; el 4B dice “he muerto”; reset de Q | ¿el cuerpo se acaba y T **sigue**? ¿Q se queda? ¿CAM? |
| Evitar la muerte | `if hp<3: avoid` | ¿la política sale de Q, o hay un U/A transitorio (tú lo rechazaste como amígdala.py)? |
| Memorizar / recordar | segundo cerebro; vector DB | CAM/T ya recuerdan. ¿qué *no* recuerdan hoy que la muerte exigiría? (olvido PULPO-C) |
| Evolucionar | GA, mutar pesos, “especies” | ¿vidas de un cuerpo, o hijos con un entero heredado? |

Analogía que Roger *no* quiere: un NPC de videojuego con barra de vida y un `switch(death)`. Analogía que *sí* encaja con el lab: un animal que, si lo matas, **el siguiente paseo usa lo que el anterior pagó con −16**, y si no aprendió, muere otra vez. Eso ya es CREDIT-1 + un terminal distinto de GOAL.

---

## 5. Piezas que ya tienes (no las reinventes)

- Tres acciones: approach / avoid / wait ≡ UNIR / TEMER / OBSERVAR.
- Choque = −16, no baldosa THREAT pintada.
- GOAL cobra +16 y **devuelve a START** (no bomba). Una “muerte” que teleporta a START *sin* perder el cuerpo es solo un GOAL al revés: dilo si es trampa.
- `body_offset` 0..5: self vs suelo.
- `frame` en el env, fuera del paquete.
- T no destrona un sucesor con el que un curriculum entero estuvo de acuerdo (KCC) hasta que el rival gana en cuenta.
- Horizonte 11. Remainder opt-in.
- `thought.jsonl` es el pensamiento **real** (enteros y átomos). Qwen traduce **fuera**. CoT póstumo = teatro (TALK-1).
- El 4B no camina. ATTEND 36/256 en el anillo con `--cortex`.

U/A que decae: `encode_cell` **reconstruye** E desde `kind` cada turno. No hay registro afectivo del agente. Si “miedo a morir” necesita persistencia, es un entero en el Agent (como `body_offset`), no un módulo `amygdala.py`, y **no** es el primer slice de ECHO-2.

---

## 6. Preguntas de implementación (alternativas + costo)

**A. Muerte.** ¿El env pone `dead=True` y `reset()` al cuerpo, dejando Q/T/CAM? ¿Un `hp` 0..N entero, −16 lo baja, +16 (comer) lo sube? ¿Morir es `r=-16` *y* fin de episodio, o solo fin de episodio? Mutante: `if cell==lava: hp=0` hardcodeado al mapa de un test.

**B. Infinito espacial.** Chunks de 3×3×3, `frame` = (cx,cy,cz) **fuera** del WSP. Local pose < 256. Dos chunks iguales **comparten** paquete (ROOM-1). Un chunk con lava: DynamicAlias>0, y entonces ¿qué distingue sin `domain`? ROOM-2 quedó abierto. No lo cierres robando `style` “porque sí”: mide primero.

**C. Infinito temporal.** GUI-3.5 `--live`: greedy para siempre. ECHO-2: el mismo bucle, pero un `hp` que puede llegar a 0. KPI: tiempo hasta la muerte **sube** respecto a un control que no recuerda las muertes anteriores (Q/T reseteados).

**D. Comer / beber / calor.** ¿Son objetos OBJ-1 con `kind` distinto y payoff, o un reloj `hunger += 1` cada N turnos? El reloj es física. “Hambre” como átomo en el WSP cada turno **sin** que el env lo genere es teatro.

**E. Población.** 1 cuerpo vs 8. 8×Q[4096][3] = 96 KiB, I4 “estáticos” se estira. Si recomiendas población, el KPI no puede ser “la media mejora”: tiene que ser **un** descendiente que, de cero, muere más tarde porque heredó **un entero** (p.ej. un `body_offset` o un prior de Q), no 4096 filas copiadas en silencio.

**F. El 4B en ECHO-2.** Sí: letrero, regla nueva, “esto es veneno” como hipótesis. No: pathfinding, “no mueras”, elegir el verbo de comer. `false_facts=0`.

---

## 7. Qué NO es ECHO-2

Minecraft. Crafter. NetHack. MiniGrid-8. Un LLM con herramientas fingiendo hambre. Un GA que muta floats. Subir CAM “porque el mundo es grande”. Pintar THREAT en cada lava para que el gate camine. Átomo CONCIENCIA. Segundo bus. Akida. 70B. Empatía. Espejo. 24 orientaciones.

No compite con Astra / GPT-4 / Intelligence Index. La pregunta sigue siendo:

> ¿Cuánto puede **no morirse** un cuerpo de enteros, **antes** de llamar al córtex — y cuánto mejora cuando el córtex lee un letrero, sin escribir hechos?

---

## 8. Formato de respuesta

1. Juicio en una página: ECHO-1 vs ECHO-2; qué queda de “sobrevivir / morir / evolucionar” cuando se baja a enteros.
2. Tabla: muerte / persistencia / infinito (tiempo vs espacio) / hambre / verbo extra → KPI → pieza existente o slice → LLM sí/no.
3. Las tres lecturas de “evolucionar”, con un ganador y el mutante que lo pondría rojo.
4. Qué de ECHO-1 es **puerta** (OBJ-1, OPEN-1, …) y qué de ECHO-2 se puede *diseñar* ya pero no *picar*.
5. Hoja de ruta **6–10 slices** ECHO-2, un KPI, orden. Primer slice **después** de XFER-1 verde (o di por qué uno podría intercalarse, y Grok lo rechazará si adelanta OBJ-1).
6. Mutantes / invariantes.
7. Lo que no sabes. Literatura 2025–2026 (lifetime RL, survival/intrinsic, world models, evolutionary RL) **citada**, no como autoridad para romper I1–I17.

La frase de Roger a respetar:

> El entrenamiento de ECHO-2 será simple: sobrevivir. Y aprenderá poco a poco a sobrevivir, memorizar, recordar, evolucionar — a base de muertes, y de evitar su muerte.
