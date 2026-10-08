# CLAUDE — OBJ-1b (pegar tal cual)

OBJ-1 el **animal** está verde. El control rojo es geométrico, y tu
tabla con DEST clavado en `(2,2,1)` es correcta **en ese corte**.
No retunees γ. No 4³. No bajes `green()`. No conviertas Q 21 vs 0
en el KPI. No lo dejes en `expectedFailure` como WALK-1: allí el
muro era `δ>>2` y no había otro entero. Aquí sí hay habitación.

Grok inundó **ítem y destino** sobre el suelo `open` que ya existe,
mismo `value_horizon()=11`, sin voxel extra, sin γ nueva.
`placements_that_cost_a_detour_and_fit` vacío era DEST congelado,
no el cubo. Hay **18 pares** con `collect ≤ 11`, dest-alone que
**no pisa** el ítem, `detour > 0`.

```
# los más holgados, brazos distintos (solo comparten START)

ITEM (0,1,0)  DEST (1,0,0)   collect 10  dest-alone 1  detour 8
ITEM (0,1,0)  DEST (2,0,0)   collect 11  dest-alone 2  detour 8
ITEM (1,0,0)  DEST (0,1,0)   collect 11  dest-alone 2  detour 8
```

El que picas:

```
ITEM_XYZ = (0, 1, 0)     # brazo largo, un paso +Y
DEST_XYZ = (1, 0, 0)     # brazo corto, un paso +X
```

No es el premio del pulpo. La mesa es un voxel, no `(2,2,1)`.
El test `DEST_XYZ == body3d.GOAL_XYZ` **se retira**: era el
candado que te dejó sin control.

Córtex apagado. Un KPI. Misma física de acoplar. No 4ª acción.
No `carrying` en el WSP. No OPEN-1.

---

## Por qué no las tres puertas que pediste

| Puerta | Por qué no |
|---|---|
| Subir horizonte / retunear γ | Prohibido. El 11 es el punto fijo de 7/8. |
| Cubo 4³ | 384 > techo 256. Prohibido. |
| Cerrar con Q 21 vs 0 y dejar el control a OBJ-2 | El animal nunca visitó la mesa vacía en el examen: Q=0 es default, no “aprendió que no paga”. La sonda 0/6 vs 6/6 es el **mundo**, no el niño que se sienta en la mesa. Sin trayectoria distinta, OBJ-1 no cierra. |

Tampoco un espolón `(2,0,1)` con mesa en `(2,2,1)`: collect 13>11.
Con DEST = premio del pulpo, tu teorema **sí** vale. Por eso se
mueve la mesa, no el cubo.

---

## Por qué este par y no `ITEM=(2,0,0) DEST=(1,0,0)` (collect 7)

Más holgado, mismo brazo. El control greedy falla el cobro en la
mesa, el `approach` lo empuja al vaso, y tu curriculum inverso le
enseñó “ve a DEST desde cualquier estado”. Vuelve con el vaso y
el env real cobra. `control_object_hits` seguiría >0.

Aquí los brazos son **disjuntos** salvo START. Dest-alone es un
`approach` a `(1,0,0)`. Si no cobra, el siguiente `approach` sigue
el corto hacia `(2,0,0)`, **no** hacia el vaso en `(0,1,0)`.
Pasarse de mesa no coge el vaso.

---

## Qué tocas

`echoai/nexus0/obj1.py` y `TestObj1`. No hinchas `body3d.py`.
`KIND_OBJECT`, `CELL_ATOMS`, `step`/`_payoff` propios, acoplar,
KEYS 22, anillo: **no se reabren**.

1. Cambia las dos constantes. `successor` / `distances` / `school`
   ya leen `DEST_XYZ` / `ITEM_XYZ`: un cambio actualiza el cubo.
2. **`cost_to_dest_alone` no puede llamar a `cube.distances()`.**
   Eso inunda al GOAL del pulpo. Hoy coincide porque DEST era ese
   voxel; el día que se mueve, miente. Inunda a `DEST_XYZ` con la
   misma aritmética de `successor` (manos vacías, sin cobrar).
3. `placements()` deja de congelar DEST. Reporta al menos este
   par, y `item_on_cheapest_dest_path == false`.
4. Quita los dos `@expectedFailure`. `green()` sigue exigiendo
   `control_object_hits == 0` y `mutant_object_hits == 0`.
5. El runner `obj1` rc=0 solo si `green()`. El test que hoy
   exige rc=1 se invierte.

Camino (inundado, no lo dibujes en el código): collect **10** ≤ 11.

```
(0,0,0,+X) avoid +Y → (0,1,0) acopla
           U-turn a casa → (0,0,0)
           a DEST (1,0,0) → approach cobra
```

Giro al aire en START (approach también anda: es el pasillo
corto). `explore_flat` on en la escuela, greedy en el examen:
es el mismo palo que PULPO-C, y allí cobró.

---

## KPI (los de OBJ-1, ahora pagables)

```
examen greedy START (0,0,0,+X) ítem (0,1,0)  object_hits > 0
item_costs_a_detour              true
item_on_cheapest_dest_path       false
shortest_collect                 ≤ 11          # 10 medido
cost_to_dest_alone               1
control_object_hits              0
control_went_to_dest             true
mutant_object_hits               0
mutant_pays_empty_Y              true          # sonda 6/6 vs 0/6
probe_empty_table_collects       0
acciones 3 · index_max 161 · domain 0 · style 0 · techo 256
false_facts 0 destroyed 0 cortex_calls 0 questions 0
```

Q 21 vs 0 **se queda en el informe** (sigue siendo verdad que
aprendieron mesas distintas). No entra en `green()`.

---

## Tests que cambian

- `DEST_XYZ == GOAL_XYZ` **fuera**. Afirma en su lugar:
  `ITEM` y `DEST` están en `floor_of(open)`, no son START,
  no son el mismo voxel, y el camino barato a DEST no contiene
  ITEM (inundado).
- Los dos `expectedFailure` se promocionan: `control_object_hits==0`,
  `mutant_object_hits==0`. El test que documentaba “el control
  trajo el vaso” se borra o se invierte.
- `obj1.main` rc=0. `green() is red` deja de ser la aserción.
- Trails hardcodeados del pasillo corto `(2,0,0,+X)(2,1,0,…)`:
  o se actualizan desde el flood o se afirma “ITEM y DEST
  aparecen en el trail del examen” sin dibujar la ruta.
- `test_landing_on_it_is_holding_it` usa las constantes, no
  `(1,0,0)`/`(2,1,0)` mágicos del layout viejo.

Mutantes de OBJ-1 (mesa=GOAL, paquete ciego, NEXT del pulpo,
pose×ítem, domain, teleport que no coge) **siguen**. No se
añade un duodécimo.

---

## Banco

```
PYTHONPATH=. python3 -m echoai.tests.test_nexus0
PYTHONPATH=. python3 -m echoai.nexus0.bench
PYTHONPATH=. python3 -m echoai.nexus0.body3d    # rc=0
PYTHONPATH=. python3 -m echoai.nexus0.self1     # rc=0
PYTHONPATH=. python3 -m echoai.nexus0.room1     # rc=0
PYTHONPATH=. python3 -m echoai.nexus0.obj1      # rc=0 solo si green()
```

Si el control sigue trayendo el vaso: **rojo**, y entonces
sí se habla. No adelantes ITEM/DEST a otro par sin medirlo.
No subas γ “un poquito”. No pintes DEST `KIND_GOAL`. No
piques OPEN-1.
