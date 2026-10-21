# MEMORIA-X · resultados del examen

20 de octubre de 2026. Examen único sobre el congelado `preflight.json`
(13:30 UTC, semillas `95a74114…`), contrato `MEMORIAX-DESIGN.md` + enmiendas 1 y
2. Datos: `lab/echo58/memx/exam/m01–m10.json` (10 × 3600 episodios),
`lab/echo58/memx/results.json`, memorias con cabeza SHA-256 en
`lab/echo58/memx/memories/`. Cálculo: `python3 -m echoai.echo58.memx.report`.

## Veredicto: **VERDE** (P1 ∧ P2 ∧ P3)

| Predicción | Qué pedía | Resultado | |
|---|---|---|---|
| **P1** daño A1 | aprendida ≤ 0,30 × vacía y < vacía, marginal, barajada, ortogonal (Wilcoxon, Holm, α = 0,01) | 24,2 frente a 150,0 (0,16×); marginal 98,9, barajada 67,3, ortogonal 75,7; p (vacía, marginal, barajada, ortogonal) = 1/1024, 1/1024, 1/128, 1/1024 | **pasa** |
| **P2** éxito | aprendida ≥ vacía y ≥ marginal, A1 y A2 | A1 174,4 / 50,0 / 38,8 · A2 122,5 / 50,0 / 44,0 (de 200) | **pasa** |
| **P3** transferencia de rol (A2) | DynObs16 daño ≤ 0,50 × vacía; UnlockPickup desperdicio ≤ 0,65 × vacía; mejor que vacía, marginal y sin_auto (5 Wilcoxon, Holm) | DynObs16 daño 0,0 frente a vacía 50,0, marginal 43,9, sin_auto 49,6; UnlockPickup desperdicio 232,9 frente a 480,6 (0,48×) y marginal 539,7; p ≤ 0,002 en las 5 | **pasa** |
| P3 solo DynObs16 (informativo, enm. 2 §10.6) | sin la familia cuyo código se leyó | pasa | — |
| P4 cota (informa) | sin_cota peor que aprendida | daño A1 25,7 frente a 24,2; A2 78,0 frente a 74,4; éxito −0,2 / −2,1 | se cumple, por poco |
| P5 ortogonal (informa) | ortogonal ≈ vacía en daño | 75,7 frente a 150,0 (A1); 124,7 frente a 150,0 (A2) | **falsa** (lo anticipó la enm. 2 §6) |

Medias por macro-semilla; cada macro = 50 mundos por familia (200 en P1/P2).

## Por familia (media de 50 mundos por macro; éxito / daño, desperdicio)

| Familia | Régimen | vacía | aprendida | sin_auto | ortogonal | marginal | barajada | techo |
|---|---|---|---|---|---|---|---|---|
| DistShift2 | A1 | 0 / 50 | **50 / 0** | 50 / 0 | 0 / 50 | 10,5 / 24,3 | 0 / 15 | 50 / 0 |
| DistShift2 | A2 | 0 / 50 | **0,2 / 49,4** | 0,2 / 49,4 | 0 / 50 | 12,1 / 23,1 | 5 / 10,6 | 47,8 / 2,2 |
| DynObs16 | A1 | 0 / 50 | 48,6 / 0 | 48,5 / 1,5 | 48,5 / 1,5 | 4,1 / 44,6 | 5 / 30 | 48,6 / 0 |
| DynObs16 | A2 | 0 / 50 | **48,5 / 0** | 0,4 / 49,6 | 0,3 / 49,7 | 4,2 / 43,9 | 5 / 30,3 | 48,6 / 0 |
| UnlockPickup | A1 | 50 / 0, w 481 | 50 / 0, w 175 | ídem | 50 / 0, w 175 | 7 / 0, w 620 | 5,8 / 0, w 1224 | 50 / 0, w 59 |
| UnlockPickup | A2 | 50 / 0, w 481 | 48,8 / 0, w 233 | ídem | 49 / 0, w 233 | 8,4 / 0, w 540 | 5,1 / 0, w 1258 | 46,8 / 0, w 295 |
| ShiftTest (ASG) | A1 | 0 / 50 | 25,8 / 24,2 | ídem | 25,8 / 24,2 | 17,2 / 30 | 27,7 / 22,3 | 50 / 0 |
| ShiftTest (ASG) | A2 | 0 / 50 | 25 / 25 | ídem | 25 / 25 | 19,3 / 28,9 | 19,6 / 25,6 | 49 / 1 |

## Lectura (lo que sí y lo que no)

1. **Lo fuerte (en A2): «lo que se mueve solo daña» transfiere a
   identificadores y tamaño nuevos.** DynObs16 en A2: aprendida 0 daños; la
   misma memoria sin lo aprendido sobre cosas que se mueven (sin_auto) 49,6 de
   50; ortogonal (solo DoorKey) 49,7. En A1, en cambio, sin_auto y ortogonal
   ya bajan a 1,5 daños sin ese rol; ese salto de 1,5 (A1) a 49,6 (A2) en los
   brazos sin rol **no está explicado** y queda abierto.
2. **La lava no transfiere en A2, y ahí la memoria empeora.** DistShift2 A2:
   aprendida muere 49,4 de 50 y logra 0,2 éxitos, **peor que barajada** (daño
   10,6, éxito 5) **y que marginal** (23,1 / 12,1). Todo su daño es
   `harm_other` y `harm_probe` = 0: no es que la memoria no reconozca la lava,
   es que le da una **creencia equivocada (no HURT)** y el agente entra. En
   desarrollo ya se vio (LavaCrossing9 A2 40/160). En A1 (ids fijos) sí: 50/0.
3. **ShiftTest (ASG): la mitad.** Aprendida 25/25 en ambos regímenes; idéntica
   a ortogonal: lo que ayuda es saber la meta y el suelo, no el rol de la lava
   de ASG. En A1, **barajada (27,7 / 22,3) supera a aprendida (25,8 / 24,2)**;
   por eso P1 frente a barajada da solo p = 1/128 (macro 4: barajada 0 daños
   frente a 22; macros 2 y 7 empatan). La memoria `techo` llega a 50/0.
4. **UnlockPickup: desperdicio a la mitad, pero lo da DoorKey.** Ortogonal
   (DoorKey solo) iguala a aprendida (w 175 / 233). En la macro 6 no hubo
   reducción (A2: 486 frente a 484 de vacía); en las otras nueve ≈ 0,43×. El
   éxito en A2 baja un poco: 48,8 frente a 50,0 de vacía. La regla «probar a recoger
   antes de accionar» nació de leer el código de esta familia (enm. 2 §3).
   P3 pasa también sin esta familia.
5. **P5 falsa.** Una memoria de una sola familia (DoorKey-6x6, 80 semillas) ya reduce el daño a
   la mitad en A1: parte del efecto de la memoria es genérico (meta, suelo,
   muro), no específico del rol.
6. **Vacía muere pronto en DynObs16 y DistShift2** tanteando (harm_probe 50/50:
   su primera prueba es entrar en algo desconocido). El 0,50 × vacía de P3 se
   apoya en eso; el control que lo hace honesto es sin_auto.

## Declaraciones que acompañan al verde

- n = 10 macro-semillas son 10 **bloques de mundos**, no 10 memorias
  independientes (enm. 2 §10.5). p = 1/1024 es el mínimo posible con n = 10.
- DistShift2 tiene trazado fijo; cambian la biyección de ids y la orientación.
- Se leyó el código de la caja de UnlockPickup antes del examen (enm. 2 §3).
- La capa 2 es una firma morfológica, no un «rol → rol» abstracto; la puerta es
  un filtro de creencias, no BLOCK/MODIFY explícitos (enm. 2 §8).
- GIFs: un caso por familia fijado antes del examen (semilla 901000, macro 1),
  no elegido por resultado. En ShiftTest ese caso sale bien; el promedio de la
  familia es 25/25.

## Verificación independiente

Un verificador independiente (20/10) recomputó P1–P3 desde `exam/m*.json` sin
usar `report.py` (Wilcoxon exacto propio, Holm propio): **CONFIRMADO**, todos
los p, banderas Holm, medias y las 72 celdas coinciden. Custodia: estado
congelado intacto, 30 memorias con cabeza igual a la congelada, 36000 celdas
únicas, daño = suma de sus tres contadores en todos los episodios. Sus
correcciones de lectura están aplicadas arriba. Nota: el brazo aleatorio
marca `wasted = −1` por episodio (−50 por macro) como centinela: no mide
desperdicio.

## GIFs

`lab/echo58/memx/media/memx-{DynObs16-A2,DistShift2-A1,UnlockPickup-A2,ShiftTest-A1}.gif`:
el mismo mundo, izquierda memoria vacía, derecha memoria aprendida (macro 1).

## Consecuencia para el roadmap

A queda en verde con su forma exacta: **transfiere el rol «se mueve solo ⇒
daña» a identificadores y tamaño nuevos (A2), y reduce acciones inútiles en
UnlockPickup (lo mismo que una memoria solo de DoorKey; sin ganancia de
éxito). No transfiere la lava en A2 (allí la memoria es peor que barajada) ni
el rol de ASG.** Se abren B (ACUMULA) y C (ENJAMBRE). Para B, el punto de
partida natural son los dos huecos medidos aquí: lava A2 y ShiftTest.
