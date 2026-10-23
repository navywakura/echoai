# C v1 · ENJAMBRE-1 — contrato (APROBADO por Nav el 21/10/2026; §2–§8 sustituidos por la enmienda 1, §11)

21 de octubre de 2026. Pista C del [roadmap](ROADMAP.md). Requisito cumplido:
A verde ([MEMORIA-X](MEMORIAX-RESULTS.md)), B verde ([ACUMULA-3](ACUMULA3-RESULTS.md)).
Encargo de Nav (21/10): «varios ECHO comparten memoria pero cada ECHO
también tiene su propia memoria: una memoria singular y una memoria global.
Entre ellos deben resolver una tarea y ayudarse. El mentiroso, para C v2
(retomando LINK-3)». **C v1 no tiene mentiroso.**

## 1. Afirmación (y lo que no afirma)

> Un equipo de ECHO con **memoria privada + memoria global** compartida por
> postales WSP, que **se ayuda** (quien termina va a ayudar a quien se
> atasca y recibe sus notas), termina una misión de varios mundos nuevos en
> **menos rondas** que el mismo equipo sin memoria global, sin ayuda, sin
> memoria privada, con la global barajada o con agentes aislados.

**No afirma:** resistencia a mentirosos (C v2), que el equipo gaste menos
episodios en total que un agente solo (se informa), ni nada fuera de MiniGrid.

## 2. Tarea: la misión

- Una **misión** = 8 mundos fijos (familia, semilla), uno por familia, en
  régimen A2 (ids opacos sorteados por mundo; reintentar un mundo da el
  mismo mundo con los mismos ids). La misión está **resuelta** cuando los 8
  mundos se han resuelto (meta alcanzada) al menos una vez.
- **Equipo:** N = 4 agentes. Una **ronda** = cada agente juega un episodio en
  el mundo que tiene asignado, en paralelo. Presupuesto: R = 30 rondas.
- **Asignación:** al empezar, los agentes cogen los mundos 1–4; quien
  resuelve el suyo coge el siguiente mundo sin dueño.

## 3. Memorias

- **Privada (singular):** la memoria de MEMORIA-X de cada agente (capa 1,
  identidad: lo que sabe de los ids *de ese mundo*; capa 2, roles). Solo la
  escribe su dueño, a partir de sus propias consecuencias.
- **Global:** registro append-only de **postales WSP de 16 B**
  (`Memory.postcards()`): cada postal es una regla de rol de la capa 2 con
  sus cuentas (n total, n de la mejor salida). Cada agente publica sus
  postales al final de cada episodio. La vista global suma, por clave, la
  **última postal de cada remitente** (reenviar no duplica evidencia) y
  habla solo con la misma cota inferior que la memoria privada.
- **Lectura:** primero la privada (identidad, luego rol); si la privada calla,
  la global. Si la privada y la global se contradicen, gana la privada (la
  experiencia propia en ese mundo).
- `destroyed == 0` en todas las memorias; enteros; córtex apagado.

## 4. Ayuda

1. **Ir a ayudar:** un agente sin mundo libre se une al mundo sin resolver
   con más episodios fallidos (si empatan, el de menor número). Un mundo se
   resuelve si cualquiera de los que lo juegan llega a la meta.
2. **Pasar las notas:** al unirse, el que ayuda recibe por postales las
   entradas de capa 1 (identidades de **ese** mundo) de la memoria privada de
   quien lo jugaba. Las guarda aparte, como notas de otro, y las lee después
   de su propia memoria y antes de la global.

## 5. Agente

El agente de B v3 (`b3/policy.py`, con el arreglo de la mano) con **todas
las piezas encendidas** y la configuración de memoria por defecto, igual en
todos los brazos. Sin automejora (eso fue B). Cada agente empieza con
**memoria vacía**: el equipo aprende desde cero en la misión.

## 6. Brazos

| Brazo | Privada | Global | Ayuda |
|---|---|---|---|
| **enjambre** | sí | sí | sí |
| sin_global | sí | no | sí |
| sin_ayuda | sí | sí | no (quien termina se queda quieto) |
| sin_privada | no (cada uno lee y escribe solo la global, con la capa 1 incluida) | sí | sí |
| global_barajada | sí | sí, claves permutadas | sí |
| aislados | sí | no | no |
| uno_solo (**se informa**) | sí | — | — (un agente, mundo a mundo, con 4 × 30 episodios) |

## 7. Mundos y semillas

- **Desarrollo:** DoorKey-5x5, LavaGapS5, SimpleCrossingS9N2,
  KeyCorridorS3R2, BlockedUnlockPickup, DistShift1, Dynamic-Obstacles-5x5,
  FourRooms. Semillas 9 100 000+.
- **Examen (cerradas; no se juegan ni se miran antes del examen):**
  DoorKey-16x16, SimpleCrossingS9N3, SimpleCrossingS11N5,
  MultiRoom-N2-S4, MultiRoom-N4-S5, RedBlueDoors-6x6, KeyCorridorS4R3,
  LockedRoom. Ninguna aparece en el código ni en los documentos de ECHO-5.8
  (comprobado con grep; DoorKey-8x8, LavaGapS6 y Unlock se descartaron
  porque B v1 los usó). Semillas 9 500 000+.
- **20 macros**, cada una un equipo nuevo con una misión nueva.

## 8. Predicciones (escritas antes de medir)

Métrica principal (elegida por Nav el 21/10): **suma de rondas por mundo**:
por cada uno de los 8 mundos, la ronda en que se resolvió por primera vez
(31 si no se resolvió en 30); se suman los 8 (mínimo 8, máximo 248). Menos es
mejor. Se informan al lado los mundos resueltos, los episodios fallidos y el
daño.

- **E1 · la global ayuda:** enjambre < sin_global y enjambre < global_barajada.
- **E2 · ayudarse ayuda:** enjambre < sin_ayuda.
- **E3 · la privada importa:** enjambre < sin_privada en **episodios
  fallidos del equipo** (sin_privada puede igualar en la métrica principal).
- **E4 · equipo frente a aislados:** enjambre < aislados.

Cinco Wilcoxon de una cola sobre las 20 macros, Holm, α = 0,01.
**Verde = E1 ∧ E2 ∧ E3 ∧ E4 ∧ `destroyed == 0` ∧ todas las postales de 16 B.**

Se informa: uno_solo (rondas = episodios, frente a los episodios totales del
equipo); cuántas postales y notas se pasan; qué reglas globales usó cada
agente que no había aprendido él.

## 9. Desarrollo y congelación

Desarrollo solo con familias y semillas de desarrollo, para ajustar lo
que no está fijado aquí (cuándo un agente se considera atascado, tamaño de
las postales de notas). Si en desarrollo las misiones se resuelven todas en
pocas rondas o ninguna, se ajusta el presupuesto R **antes** del `preflight`,
con enmienda escrita. Revisor independiente antes de congelar; el examen
corre una vez.

## 10. Riesgos

1. Algunos mundos de examen pueden ser inalcanzables para la política
   (DoorKey-16x16, MultiRoom-N4-S5, KeyCorridorS4R3, LockedRoom): suman 31
   en todos los brazos y solo diluyen la diferencia (por eso la métrica es
   la suma por mundo y no «misión entera»).
2. Si los roles que transfieren son pocos (lava, puerta/llave), la global
   ayuda al principio y luego no: E1 puede salir justo.
3. E3 es la apuesta menos segura: si todo lo útil es de rol, la privada
   no aporta y E3 sale rojo.
4. Con 20 macros y Holm, cada comparación necesita casi siempre ganar
   (p exacto mínimo ≈ 1·10⁻⁶; el umbral más duro es 0,002).

Invariantes: WSP 16 B, enteros, `destroyed == 0`, córtex apagado, nada nuevo
bajo `nexus0/`, `memx/` `acumula*/` `b3/` sin tocar (el código nuevo en
`echo58/enjambre/`), campaña ARC intacta.

## 11. Enmienda 1 — rediseño (21/10/2026, antes de cualquier examen; APROBADA por Nav el 21/10)

El primer diseño (misiones de MiniGrid en A2) se cerró en desarrollo: ningún
brazo se distinguía ([nota](ENJAMBRE1-DEV-NOTE.md)). Nav eligió rediseñar la
tarea. Esta sección **sustituye §2–§8**; los nombres de los brazos y la
métrica elegida por Nav (suma de rondas por mundo) se mantienen. El código
del primer diseño queda como registro en `echo58/enjambre/bench_a2.py`.

**Mundos compartidos propios** (`echo58/enjambre/coop.py`; enteros; mecánica
de MiniGrid: girar, avanzar, coger, soltar, accionar). Varios agentes juegan
**a la vez el mismo mundo**, por turnos estrictos; cada uno ve a los demás
como un id. Un **idioma común**: el mismo id significa lo mismo en todos los
mundos (régimen A1), salvo la excepción local. Cuatro tipos, dos de cada uno
por misión (8 mundos):

| Tipo | Qué hay |
|---|---|
| puerta | pared con puerta cerrada con llave; la llave está en el lado de salida |
| lava | columna de lava con un hueco |
| placa | pared con una compuerta abierta **solo mientras alguien pisa la placa**: no se puede resolver solo |
| local | lava con dos huecos; uno está guardado por una baldosa decorativa que **aquí quema** (en los demás mundos es inofensiva) |

Si alguien llega a la meta, el mundo queda resuelto para el equipo. Caer en
lava (o en la baldosa local) acaba solo el episodio de ese agente.

**Memorias.**
- **Privada:** la de MEMORIA-X (identidad y rol) más **«lo que viví aquí»**
  (la capa de identidad del mundo en el que está, que se consulta primero) y
  la **memoria remota**: «entrar en p cambió g en otro sitio», contada frente
  a todas las veces que entró en p.
- **Global:** postales WSP de 16 B con roles, **identidades** (posible gracias
  al idioma común) y reglas remotas; última postal de cada remitente; misma
  cota inferior.
- **Lectura:** aquí → privada (identidad, rol) → notas → global (identidad,
  rol).

**Ayuda.**
1. *Ir a ayudar:* quien no tiene mundo libre va primero a un mundo marcado
   como «necesita ayuda» (alguien supo cómo abrir pero estaba solo), luego al
   de más fallos. Recibe las notas de ese mundo (identidades y reglas remotas).
2. *Pedir y sujetar:* si una compuerta cerrada le corta el paso, sabe (por
   cualquier memoria) que pisar p la abre y ve a un compañero, el agente
   publica una petición (p, g) en el tablón del mundo y espera junto a la
   compuerta (máximo 60 pasos). Un compañero que ve la petición va a la placa
   y se queda encima hasta que el que pidió ha entrado. La petición lleva p:
   quien ayuda no necesita saberlo.

**Agente:** el de B v3 con todas las piezas (`b3/policy.py`), más
`enjambre/cagent.py` (memoria remota, pedir, sujetar). Un id «se mueve solo»
solo si deja una casilla y aparece en otra (una compuerta que cambia en su
sitio no se mueve). Memoria vacía al empezar.

**Semillas:** desarrollo 9 100 000+; examen 9 500 000+ (nunca jugadas). 20
macros (equipos), 4 agentes, 30 rondas, 300 pasos por agente y episodio.
`uno_solo` (se informa): un agente, mundo a mundo, 120 episodios en total, 30
como máximo por mundo.

**Predicciones** (métrica principal: suma de rondas por mundo, 31 si no se
resolvió; menos es mejor):

- **E1 · la global ayuda:** enjambre < sin_global y enjambre < global_barajada.
- **E2 · ayudarse ayuda:** enjambre < sin_ayuda. **Declarado:** los mundos
  de placa no se pueden resolver solo, así que E2 es en parte por
  construcción; se informa también E2 sin los mundos de placa.
- **E3 · la privada importa:** enjambre < sin_privada en **episodios
  fallidos del equipo** (lo que decía §8).
- **E4 · equipo frente a aislados:** enjambre < aislados (también en parte
  por construcción, por las placas).

Cinco Wilcoxon exactos de una cola sobre las 20 macros (los empates se
descartan), Holm, α = 0,01. **Verde = E1 ∧ E2 ∧ E3 ∧ E4 ∧ `destroyed == 0` ∧
todas las postales de 16 B.**

**Desarrollo** (6 macros, `lab/echo58/enjambre/dev2-20261021T003339.json`):

| Brazo | Puntuación | Resueltos (de 48) | Fallidos | Daño |
|---|---|---|---|---|
| **enjambre** | **237** | 47 | 189 | 56 |
| sin_global | 278 | 47 | 214 | 72 |
| sin_ayuda | 506 | 36 | 392 | 46 |
| sin_privada | 332 | 43 | 297 | 111 |
| global_barajada | 325 | 46 | 238 | 74 |
| aislados | 536 | 36 | 406 | 63 |
| uno_solo | — | 27 | 571 | 43 |

Macro a macro, el enjambre gana 6 de 6 a sin_global, global_barajada,
sin_ayuda y aislados. Frente a sin_privada en fallidos: 3 ganadas y 3
empates (110 = 110, 9 = 9, 14 = 14). **Riesgo principal:** si en el examen hay
muchos empates o alguna derrota frente a sin_privada, E3 sale rojo. Con 20
macros sin empates el p mínimo es ≈ 1·10⁻⁶. Si hay empates, cada uno resta
una macro (con solo 6 distintas de cero, el p mínimo es 0,016 > 0,01).

**Declarado:** el mundo cooperativo y la
excepción local los diseñé yo (Claude) para que la ayuda y la privada *puedan*
importar. Que importen de verdad es lo que mide el examen.

## 12. Enmienda 2 (21/10/2026, tras la revisión independiente, antes de `preflight`)

El revisor (sin jugar ninguna misión de examen) repitió un trabajo de
desarrollo dos veces con semillas de hash distintas: **idéntico byte a byte**.
Encontró tres bloqueos y varios arreglos, todos corregidos:

1. **Mundos sin salida:** las baldosas (que en el mundo local queman) podían
   caer junto al hueco seguro; en el 23 % de los mundos locales no había
   salida, y eso forzaba empates. Ahora las casillas junto a los huecos
   quedan libres, solo cuentan como inicio las casillas con salida segura, y
   el mundo se vuelve a sortear (de forma determinista) si hay menos de 4.
2. **Placa delante de la compuerta:** un agente solo podía pisar la placa y
   entrar (5,6 % de las semillas). La placa ya no puede ir ahí.
3. `uno_solo`: 30 episodios como máximo **por mundo** (antes se acumulaba).
4. El denominador de la regla remota en las notas cuenta todas las entradas
   en ese mundo; las notas se vacían al ir a ayudar a otro mundo; la petición
   se retira en el propio turno del agente; «necesita ayuda» solo se marca si
   el agente estaba solo; el agente **sabe cuántos compañeros comparten su
   mundo** (declarado, como la propiocepción) en lugar de deducirlo de verlos
   moverse.

Declaraciones:
- `sin_privada` recibe notas al ir a ayudar (salen de las memorias privadas
  de los demás): favorece al control.
- `global_barajada` no permuta la firma de la capa 1 y deja algunos puntos
  fijos: es un control más callado que equivocado.
- `destroyed` no puede subir en este código (nada borra): esa condición del
  verde se cumple por construcción.

Desarrollo tras la enmienda (`lab/echo58/enjambre/dev2-20261021T012207.json`,
6 macros; puntuación por macro):

| Brazo | Puntuación (suma) | Por macro | Fallidos |
|---|---|---|---|
| **enjambre** | **237** | 31 · 52 · 43 · 31 · 37 · 43 | 110 |
| sin_global | 258 | 35 · 54 · 39 · 41 · 44 · 45 | 122 |
| sin_ayuda | 525 | 82 · 97 · 90 · 82 · 86 · 88 | 398 |
| sin_privada | 545 | 31 · 248 · 52 · 37 · 135 · 42 | 352 |
| global_barajada | 293 | 42 · 68 · 56 · 42 · 45 · 40 | 154 |
| aislados | 538 | 84 · 99 · 86 · 88 · 91 · 90 | 402 |

El enjambre gana 5 de 6 a sin_global (pierde m3), 5 de 6 a global_barajada
(pierde m6) y 5 de 6 a sin_privada en fallidos (pierde m6). Con Holm hacen
falta casi 20 de 20: **E1 y E3 pueden salir rojos**. No se ajusta nada más.
