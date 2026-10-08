# ECHO-4.5 · S5-D (examen de S5) · contrato (fijado el 2026-09-26, antes de medir)

Roger: «si haz S5-D». S5 salió rojo con su contrato original y verde solo con versiones declaradas
después de los rojos (gym v2 y agente v5.2), ajustadas mirando gym-train. Este examen mide **una sola
vez**, con juegos que nadie ha mirado, para saber si ese verde es real.

## Qué se congela (sha256, primeros 16 caracteres)

| Archivo | Huella |
|---|---|
| `echo_arc/agent.py` | `39395d68cdeec015` |
| `echo_arc/runner.py` | `75f3c50074cc4232` |
| `seed/arc3gym.py` | `9586c22ac4b8b994` |

Si alguna huella cambia antes de terminar, el examen se anula.

## Juegos del examen

- **ARC3-GYM v2**, semillas **5000–5099**: 100 juegos nuevos, nunca generados ni vistos.
- Las familias salen del generador tal cual; no se eligen.

## Agentes

**v3**, **v5.2** y el **azar**, con 2000 acciones por juego y 3 semillas del agente (rep 0, 1 y 2).
Se ejecutan con `python -m seed.arc3gym run AGENTE --version 2 --split exam`.

## Criterio

| Id | Condición |
|---|---|
| D1 | el solucionador resuelve el 100 % de los 500 niveles y el mismo juego generado dos veces es idéntico |
| D2 | el azar completa **< 15 %** de los niveles |
| D3 | v5.2 completa **más niveles** que v3 (suma de las 3 semillas) |
| D4 | la puntuación oficial media de v5.2 es **mayor** que la de v3 (media de las 3 semillas) |
| D5 | repetir las partidas de v5.2 (rep 0) da 0 diferencias en acciones |

**S5-D verde = D1 ∧ D2 ∧ D3 ∧ D4 ∧ D5.** Se mide una sola vez y se publica sea cual sea el
resultado. Si sale rojo, S5 queda rojo.

## Resultado (2026-09-26) — VERDE

Datos: `lab/seed/arc3gym/s5d/`. Las huellas de los tres archivos congelados coinciden al terminar.

| Id | Resultado |
|---|---|
| D1 | ✅ 100 juegos, 500 de 500 niveles resueltos por el solucionador; generación idéntica |
| D2 | ✅ el azar completa 19 · 15 · 13 niveles = **3,1 %** |
| D3 | ✅ niveles: v5.2 **370 · 359 · 374 = 1103**, frente a v3 313 · 312 · 315 = 940 (+17 %) |
| D4 | ✅ puntuación oficial media: v5.2 **7,42**, frente a v3 0,66 (11 veces más) |
| D5 | ✅ repetir las 100 partidas de v5.2 (rep 0) da 0 diferencias |

**S5-D verde, así que S5 queda VERDE por examen.**

Por familias (niveles de 5 / puntuación):

| | laberinto | interruptor | palanca | caja | luces | flechas | mixto |
|---|---|---|---|---|---|---|---|
| v3 | 4,4 / 3,1 | 3,3 / 0,14 | 2,3 / 0,04 | 0,8 / 0,01 | 5,0 / 1,95 | 4,5 / 0,87 | 3,1 / 0,13 |
| v5.2 | **5,0 / 46,8** | **4,7 / 11,7** | **3,5 / 0,32** | 0,8 / 0,24 | 5,0 / 1,95 | 4,5 / 0,87 | 3,1 / 0,13 |

**Límites que siguen en pie:**
- la caja no se planifica;
- los juegos de clic son v3;
- el gym es nuestro, así que esto no sustituye al examen de ECHO-4.5 con los juegos oficiales.
