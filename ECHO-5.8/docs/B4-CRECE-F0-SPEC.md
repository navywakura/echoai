# B v4 · CRECE · F0: el enchufe de piezas (especificación técnica)

21 de octubre de 2026. **Especificación técnica aprobada por Nav.**
Incluye la enmienda NOTE/HAND aprobada en la conversación; motivación en
`B4-CRECE-F0-INCIDENCIAS.md`.
Responde a los hallazgos 1 y 2 de `B4-CRECE-REVIEW.md` y **sustituye el §3.1
de `B4-CRECE-METODO.md`** (las firmas `veto`/`prefer` no bastaban). F0 no
mide nada científico, no llama a ningún LLM y no toca código congelado; su
única puerta es la equivalencia de §6. Los hallazgos 3–9 de la revisión se
resolverán en una enmienda del método antes de F1, no aquí.

## 1. Objetivo

Un agente, `HAgent`, que juegue **exactamente** como el agente de B v3
(`PAgent`, `echo58/b3/policy.py`) cuando se le enchufan las 5 piezas de B v3
reescritas como piezas externas, y exactamente como `PAgent` sin piezas
cuando no se le enchufa ninguna. Si eso se cumple, cualquier pieza futura
(escrita por un LLM en F1) entra por el mismo enchufe sin tocar la política.

## 2. Dónde y qué

| Archivo | Contenido |
|---|---|
| `echo58/crece/__init__.py` | vacío |
| `echo58/crece/runtime.py` | `HAgent`, `View`, efectos, aplicación y límites |
| `echo58/crece/pieces_b3.py` | las 5 piezas de B v3 reescritas como funciones puras |
| `echo58/crece/equiv.py` | corredor de la prueba de equivalencia (§6) |
| `tests/test_echo58_crece_f0.py` | tests de §6 y §7 |
| `lab/echo58/crece/f0-equiv.json` | informe de la equivalencia |

`memx`, `acumula`, `acumula2`, `b3`, `acumula3` y `enjambre` solo se
importan. Ningún archivo nuevo bajo `nexus0/`.

## 3. Cómo se construye `HAgent`

`HAgent(PAgent)` con `pieces=frozenset()` **siempre** (el constructor lo
comprueba y falla si recibe otra cosa). Así conserva, sin copiarlos, el
arreglo base de la mano y toda la contabilidad de `PAgent` que no depende de
las piezas (`picked`, `opened`, `visits`, `progress`, `dropped`, `idle`,
`blockdrops`, señales), y ninguna rama de las 5 piezas originales puede
ejecutarse: todas están protegidas por `"x" in self.pieces`. El
comportamiento de las piezas solo puede venir del enchufe.

`HAgent(source, learn, plugs=(...))` recibe una tupla ordenada de piezas
enchufadas. **El orden es parte de la configuración** (se guarda con el hash
de cada pieza).

## 4. Los cuatro momentos de enganche

Son exactamente los puntos donde `PAgent` consulta hoy `self.pieces`.

| Momento | Cuándo | Contexto extra | Efectos admitidos | Pieza B v3 que lo usa |
|---|---|---|---|---|
| `decide` | tras cada `super()._decide` dentro del bucle de hasta 8 pasadas de `PAgent._decide` | `intent`; `drop_for` = id de la casilla que el agente quiere coger tras soltar (o `None`) | `BAN`, `NOTE` | `commit`, `no_retoggle` |
| `outcome` | al final de `_outcome`, después de la contabilidad de `PAgent` | `intent`, `out`, `dropped_here` = lo que había en `dropped[cell]` **antes** de que `PAgent` lo quite | `BAN_UNTIL_PROGRESS`, `NOTE` | `no_repick` |
| `drop` | al entrar en `_drop`, si el mundo no es absoluto | `avoid` | `DROP_AT`, `GOTO`, `NOTE` | `clear` |
| `idle` | al final de `_decide`, con el contador `idle` ya actualizado, si el mundo no es absoluto | — | `GOTO`, `NOTE` | `wander` |

### 4.1 Composición

- En cada momento se llama a las piezas **en el orden de la tupla**. La
  primera que devuelve un efecto de acción gana ese momento; las demás no se
  llaman. `NOTE` no cuenta como acción: se aplica y se sigue llamando.
- **Abstenerse** es devolver `()`. Si todas se abstienen, el agente hace lo
  que haría `PAgent` sin piezas en ese punto.
- `decide`: si gana un `BAN`, el runtime lo aplica, vacía `belief_cache` y
  vuelve a decidir; como mucho 8 pasadas y una final bajo los bans, igual que
  `PAgent`. En la pasada final no se consulta el enchufe.
- Una pieza devuelve una tupla de 0 a 2 efectos: como mucho un `NOTE` y como
  mucho un efecto de acción.

### 4.2 Efectos (lista cerrada)

| Efecto | Significado | Comprobación del runtime |
|---|---|---|
| `BAN(id, act, scope)` | a partir de ahora `belief(id, act, ·)` responde `NOOP`; `scope` es `HAND` (solo con la mano actual) o `ANY` | `act` válido, id presente en el tablero |
| `BAN_UNTIL_PROGRESS(id, act)` | `NOOP` mientras `progress` no cambie | igual |
| `DROP_AT(cell)` | soltar en esa casilla vecina (girando antes si hace falta) | vecina, dentro del tablero, distinta de `avoid`, con algo en la mano |
| `GOTO(cell)` | dar un paso hacia esa casilla por el árbol de alcanzables | alcanzable, distinta de la posición |
| `NOTE(key, scope=EPISODE)` | suma 1 al contador `key` de esa pieza; HAND lo distingue además por el id sostenido | `key` entero pequeño (0–15); HAND exige mano no vacía |

Un `BAN` **solo puede hacer al agente más prudente** (convierte respuestas
en `NOOP`): nunca puede convertir un `HURT` en `PASS` ni levantar una
prohibición del núcleo. `GOTO` solo camina por casillas que el agente ya cree
`PASS`. No existe la regla «si todo queda vetado, se ignoran los vetos»
(la propuso el método, `PAgent` no la tiene y se elimina).

Las cuentas HAND persisten al soltar y recuperar el mismo objeto dentro del
episodio. Todas se reinician al comenzar otro episodio. `clear` usa NOTE(0,
HAND) cada vez que alcanza la rama de búsqueda, aunque no encuentre destino
o supere ocho intentos. Se valida toda la respuesta antes de aplicar efectos.

### 4.3 Fallos de una pieza

Si una pieza lanza una excepción, devuelve algo que no está en la tabla o un
efecto que no pasa la comprobación, el runtime lo trata como **abstención**,
lo anota en `r["plug_errors"]` (pieza, momento, tipo de fallo) y sigue. Las
5 piezas de B v3 tienen que dar 0 errores. Límites de tiempo, sandbox y lista
blanca del AST son para el código del LLM (F1) y no forman parte de F0, cuyas
piezas están escritas a mano y revisadas.

## 5. La vista `v`

Objeto de solo lectura que se crea en cada llamada. No expone el agente ni
ningún método que lo modifique; todo lo que devuelve es entero, tupla o
`frozenset`.

| Campo / consulta | Qué es |
|---|---|
| `pos`, `dir`, `hand`, `absolute` | estado del agente y del mundo |
| `grid` | tupla de tuplas de ids opacos |
| `progress`, `idle`, `steps` | contadores del episodio de `PAgent` |
| `picked(id)`, `opened(cell)`, `visits(cell)` | contadores del episodio |
| `note(key, scope=EPISODE)` | contador propio de la pieza; HAND selecciona el id sostenido |
| `wall`, `floor` | id del muro (el más común del borde) e id del suelo (el `PASS` más común), con el mismo desempate que `PAgent` |
| `belief(id, act, hand)` | la creencia actual del agente |
| `reach(start=None, blocked=None)` | `frozenset` de casillas alcanzables por casillas `PASS` (misma función `reach` de B v3) |
| `ids_near(start=None)` | ids de las casillas vecinas a lo alcanzable |

Esta lista es la mínima que necesitan las 5 piezas. Ampliarla es un cambio
del runtime (nueva versión y nuevo hash), no algo que decida una pieza.

Precisión de implementación: en OUTCOME, la vista conserva la observación
anterior a la acción (incluida la casilla del objeto que se acaba de coger),
y los contadores reflejan la contabilidad posterior. `out` describe el
resultado nuevo. Así se valida el id que realmente recibió la acción.

## 6. Prueba de equivalencia (la puerta de F0)

**Qué se compara, paso a paso:** la acción primitiva, la intención completa
y el resultado (`out`) de cada paso, y al final el diccionario de resultado
del episodio (éxito, daño, pasos, desperdicio, señales…, sin las claves
nuevas de `HAgent`).

| Caso | `HAgent` | frente a |
|---|---|---|
| E0 | sin piezas | `PAgent(pieces=∅)` |
| E1 | cada pieza sola (5 casos) | `PAgent` con esa pieza |
| E2 | `commit` + `no_repick` (la pareja de B v3) | `PAgent` con esa pareja |
| E3 | las 5 en orden `commit, no_retoggle, clear, wander, no_repick` | `PAgent` con las 5 |

**Mundos y semillas:** las familias de desarrollo de B v3 (`PROBE["dev"]`
de `acumula3/bench.py` y las de entrenamiento de `MIX`), con semillas
`7_000_000`–`7_000_199`, las que ya usó la investigación de B v3. Nunca
semillas de examen (`3_000_000+`, `6_000_000+`, `8_000_000+`).

**Dos protocolos de memoria**, porque las piezas cambian lo que se aprende:
sin memoria (`source=None`) y con la memoria de desarrollo de
`b3/probe_pieces.py` (memoria inicial con `CORRECTED`, copia de sonda que
aprende en línea, una copia por brazo restaurada idéntica).

**Cobertura:** cada pieza tiene que actuar (efecto aplicado) al menos 20
veces en el conjunto; si no, se añaden semillas del mismo rango hasta que
lo haga, y se declara cuántas.
Se empieza en 7_000_000 y se añaden en orden; se termina al cerrar una semilla
completa con la cobertura requerida en todos los casos y protocolos. Una
muestra abreviada no puede declarar la puerta oficial de F0 verde.

**Puerta:** 100 % de pasos idénticos en E0–E3 con los dos protocolos y
0 `plug_errors`. Cualquier diferencia se investiga con su primer paso
divergente; no se acepta «casi igual».

## 7. Tests

1. E0–E3 en una muestra pequeña (para que el test tarde menos de un minuto);
   la corrida completa la hace `equiv.py` y escribe `f0-equiv.json`.
2. `HAgent` rechaza `pieces` no vacío.
3. `pieces_b3.py` no importa `b3` ni `PAgent`, no usa atributos con `_` ni
   floats ni `/` (AST).
4. `View` no deja escribir: asignar un atributo o mutar lo que devuelve falla.
5. Una pieza que lanza una excepción, una que devuelve basura y una con un
   `GOTO` a una casilla no alcanzable se tratan como abstención y quedan en
   `plug_errors`.
6. Ningún `BAN` puede hacer que `belief` devuelva algo distinto de lo de
   antes o de `NOOP`.
7. Los hashes de B v3 (`acumula3.bench.frozen_state()`) coinciden con su
   `preflight.json`: F0 no ha tocado nada congelado.
8. Los tests de 5.8 que ya existen siguen en verde.

## 8. Fuera de F0

LLM, fichas de fallo, sandbox, lista blanca del AST para código ajeno,
puerta empírica, biblioteca en disco, generaciones, poda y examen. Todo eso
va en la enmienda del método y en F1–F4, con su aprobación aparte.

## 9. Coste esperado

Un día de trabajo: runtime (~200 líneas), piezas (~120), equivalencia y tests.
La corrida completa de equivalencia, unos minutos en CPU.
