# METAVERSE-1 · Etapa 0 — custodia de assets

**Estado:** verde en su alcance declarado. 21 de septiembre de 2026.
**Fase padre:** METAVERSE-1 ([contrato](METAVERSE1-DESIGN.md)).
**Reanuda desde:** [acta de congelado](METAVERSE1-FREEZE-20260920.md) §4.
**No cierra DRONE-3 ni sube ECHO-3 de 14/15.** Esto es custodia de ficheros,
no hardware y no física.

```bash
cd /home/user/REALRXOS/RXos
PYTHONPATH=. python3 -m echoai.tests.test_metaverse1     # 40/40
PYTHONPATH=. python3 -m echoai.metaverse1.bench          # certificado intacto
```

---

## 1. El defecto, dicho entero

`metaverse1/assets/build_world.py` escribía su recibo en `out/<name>.json`.
Cuando la declaración de entrada tenía el mismo nombre y vivía en el mismo
directorio —que es exactamente cómo se construyó `wide-3x2` el 20/09— **el
recibo sobrescribía la declaración fuente**.

Estado encontrado hoy en `lab/metaverse1/worlds/wide-3x2.json`:

```json
{ "world": ".../wide-3x2.json", "mesh": "wide-3x2.glb", ... }
```

Un recibo que se declara a sí mismo como su propia fuente. Los campos de la
declaración —`schema`, `domain`, `solids`, `start`, `goal`— ya no estaban. La
malla existía; la prueba de qué la produjo, no.

Esto no invalidaba el certificado de META-WORLD-2, porque ese banco no
certifica la tubería Blender. Sí impedía cualquier afirmación de
reproducibilidad del artefacto, y por eso iba primero.

## 2. La reparación

Tres artefactos, tres rutas fijas y distintas:

```
<mundo>.declaration.json     fuente inmutable
<mundo>.glb                  resultado visual
<mundo>.build-receipt.json   herramienta, parámetros y hashes
```

Las reglas no viven en el driver de Blender sino en `metaverse1/assets/`
**`custody.py`**, un módulo que no importa nada fuera de la librería estándar
—ni `bpy`, ni echoAI— para que lo puedan importar igual el intérprete de
Blender y la suite de pruebas, y para que la tubería de assets no pueda
arrastrar el agente a un renderer.

Lo que `custody.plan()` rechaza:

- que declaración, malla y recibo no sean tres rutas distintas;
- que la declaración no exista o no sea un fichero;
- un nombre de mundo con separadores de ruta;
- sobrescribir una malla o un recibo existentes sin `--overwrite`.

Lo que `custody.build()` garantiza, en este orden:

1. se hashea la declaración **antes** de exportar;
2. se ejecuta la exportación;
3. se lee la malla como contenedor glTF —magia `glTF`, versión 2, longitud
   declarada igual al tamaño real, chunk JSON que parsea y trae `asset`—;
4. el llamante puede añadir una validación más fuerte: `build_world.py`
   **reimporta el GLB en Blender** y cuenta objetos;
5. se vuelve a hashear la declaración y se exige que no haya cambiado;
6. **sólo entonces** se escribe el recibo.

Si la exportación lanza, si no deja fichero, si el contenedor está truncado o
si la reimportación falla, **no se escribe recibo ninguno**. Un build fallido
no puede dejar un recibo verde para que alguien se fíe de él más tarde.

`custody.verify()` relee un recibo y contrasta cada afirmación contra el disco:
hashes, existencia, y las tres formas de auto-referencia —incluida la que dejó
a `wide-3x2` sin fuente.

`build_world.py` además comprueba el `schema` de la entrada, así que pasarle un
recibo en lugar de una declaración falla dos veces, no una.

## 3. Pruebas

Doce pruebas nuevas en `tests/test_metaverse1.py`, y siguen la regla que esta
fase heredó de DRONE-3: **un control que no puede salir rojo no demuestra
nada**. Cada regla se rompe a propósito y debe ser cazada.

| # del handoff | Qué exige | Prueba | Mutante que la hace fallar |
|---|---|---|---|
| 1 | la fuente sigue intacta byte a byte | `test_declaration_is_untouched_by_the_build` | — |
| 2 | entrada, GLB y recibo son tres rutas | `test_the_three_artefacts_have_three_paths` | `..._receipt_that_would_land_on_the_declaration_is_refused` |
| 3 | el recibo apunta a la declaración | `test_receipt_points_at_the_declaration_not_at_itself` | `test_verify_catches_a_self_referencing_receipt` |
| 4 | los hashes coinciden con los ficheros | `test_recorded_hashes_match_the_files` | `test_verify_catches_a_mesh_changed_after_the_build` |
| 5 | reconstrucción headless da un GLB importable | `test_a_passing_reimport_is_recorded` + el build real | `test_a_truncated_mesh_is_not_accepted` |
| 6 | un fallo no deja recibo verde engañoso | `test_a_raising_export_writes_no_receipt` | `..._export_that_writes_nothing...`, `..._failed_reimport...` |

Más la regla de sobrescritura: por defecto se rechaza
(`test_existing_artefacts_are_not_overwritten_by_default`), y con `--overwrite`
el recibo registra el sha256 de lo que había antes
(`test_overwriting_records_what_was_replaced`).

**40 tests verdes en 4,4 s**, sin saltos.

## 4. Reconstrucción de `wide-3x2`

No se reconstruyó desde el JSON sobrescrito, que es lo que el handoff prohíbe
expresamente. Se regeneró desde sus parámetros:

```bash
python3 -m echoai.metaverse1.declare \
    --seed 7001 --condition static --cols 3 --rows 2 \
    --out lab/metaverse1/worlds/wide-3x2.declaration.json
```

El recibo dañado había conservado tres números, y son los que permiten
auditar la reconstrucción:

| Campo | Recibo dañado | Reconstrucción |
|---|---:|---:|
| sólidos | 96 | 96 |
| regiones | 6 | 6 |
| tamaño | 63 × 42 m | 63 × 42 m |

Y entonces el resultado que convierte la reconstrucción en demostrada y no en
plausible: al reconstruir la malla con Blender headless desde esa declaración,
el GLB salió **byte a byte idéntico** al del corte.

```
89dd499e09baf5d852f12d9c05e944cdd2427c93e83fac960405ee4775b2ee85  wide-3x2.glb (reconstruido)
89dd499e09baf5d852f12d9c05e944cdd2427c93e83fac960405ee4775b2ee85  wide-3x2.glb (corte 20/09)
```

Sigue siendo, formalmente, **una reconstrucción y no el original**: el fichero
original se perdió y eso no se deshace. Pero produce el mismo artefacto bit a
bit, y el recibo lo dice en un bloque `reconstruction` con el motivo escrito.

Artefactos del corte preservados antes de tocar nada, con sus hashes del acta
verificados uno a uno:

```
lab/metaverse1/worlds/corte-20260920/wide-3x2.glb    89dd499e…  ✓ acta §6
lab/metaverse1/worlds/corte-20260920/wide-3x2.json   8d4cc756…  ✓ acta §6
```

`wide-3x2.json` —el recibo dañado— se deja donde estaba, sin tocar. Es la
evidencia del defecto.

## 5. El defecto ya no se puede repetir

Tres defensas, comprobadas ejecutándolas:

```
A) la invocación exacta que destruyó la fuente:
   unexpected declaration schema: None (expected 'echoai-metaverse1-world-v1';
   a build receipt is not a declaration)

B) forzar que el recibo caiga sobre la declaración:
   CustodyError: declaration, mesh and receipt must be three different paths

C) custody.verify(wide-3x2.build-receipt.json):
   ok = True | problemas = []
```

## 6. Lo que no demuestra

- **Nada sobre hardware ni vuelo.** `drone3_green` sigue en `false`, ECHO-3 en
  14/15. Esto son ficheros y hashes.
- **Nada sobre Gazebo.** El SDF ampliado sigue sin medirse dentro del
  simulador; ese hueco es la Etapa 1 (FLIGHT-2) y sigue abierto.
- **No prueba que el mundo sea correcto**, sólo que se puede regenerar y que
  se sabe de qué fuente salió.
- **`build_room.py` sigue mezclando declaración y recibo** en un solo fichero.
  No tiene el fallo de sobrescritura —genera su declaración, no la lee de
  ningún sitio, así que no hay fuente que pisar— pero tampoco separa las dos
  afirmaciones. Es sala de prueba, no mundo; queda anotado, no arreglado.
- La equivalencia visual entre el GLB y el SDF de colisión no se mide aquí.

## 7. Custodia

Cero ficheros nuevos bajo `nexus0/`. Cero ediciones a ficheros sellados. Todo
en `echoai/metaverse1/assets/`, `echoai/lab/metaverse1/` y
`echoai/tests/test_metaverse1.py`.

Certificado de META-WORLD-2 recalculado tras la reparación:
`f508b10858e2a762e079106dfcb2ea3e5c3d9ac579e190482e4b19345c05d4e0`, el mismo
del corte.

Fases selladas reproducidas después de tocar el árbol:

| Fase | Resultado |
|---|---|
| POWER-1 | `valid: true`, cert `6a05ad4c8be2d2cb…` |
| HOST-1 | `valid: true`, cert `18d4a4fa07f57c7a…` |
| SAFE-1 v2 | `valid: true`, cert `eecb77b8c0b9c214…` |
| PX4-1 | informe reproduce, mutante rechazado, cert `342ca3aa9380b8f4…` |
| FUSION-1 | auditoría sin hallazgos |
| COMPOSE-1 v4 | **no concluida**: la auditoría seguía corriendo al cerrar la jornada. Queda pendiente de rematar. |

### Hallazgo: el lock de CAUSE-1 lleva roto desde el 17 de septiembre

`python3 -m echoai.nexus0.cause1.bench audit` sale rojo con
`ValueError: frozen implementation changed`. **No lo ha causado esta etapa**, y
el diagnóstico lo demuestra sin ambigüedad:

```
NUEVOS  : 112 ficheros — todos de nexus0/{drone3, host1, power1, px41,
                          safe1, safe1_v2, transfer3}
FALTAN  : ninguno
CAMBIAN : ninguno
metaverse1 en el inventario: NINGUNO
```

Cero ficheros cambiados y cero desaparecidos: nada de lo que CAUSE-1 selló se
ha tocado. Lo que falla es que su inventario se siembra con
`rglob('*.py')` sobre **todo** `nexus0/`, y el lock se congeló el 17/09 a las
20:28 — antes de que existieran PX4-1 (21:30 del mismo día), HOST-1 (23:30),
TRANSFER-3 (19/09) y DRONE-3 (20/09). Cada fase posterior que escribió bajo
`nexus0/` amplió el inventario y dejó el candado de CAUSE-1 sin poder cerrar.

Es exactamente el peligro por el que METAVERSE-1 y GUI-4 tienen prohibido
escribir bajo `nexus0/`; aquí simplemente ya había saltado. No se arregla
desde esta etapa: re-congelar el lock de una fase cerrada es una decisión de
custodia de ECHO-3, no un efecto colateral de reparar un script de Blender.
Queda escrito y sin tocar.

Nota menor: `px41.bench audit` aborta con `FileExistsError` sobre
`lab/px41/audit-receipt.json`. Es su propia protección contra sobrescribir un
recibo —no un fallo de reproducción—: la verificación del informe ya había
pasado antes de llegar a esa línea, y recalculada aparte da verde.

## 8. Siguiente

**Etapa 1 — FLIGHT-2 / paridad Gazebo-PX4.** Generar el SDF ampliado desde la
misma declaración canónica, empezar por el mundo mínimo y después 2 × 2 y
3 × 2, volar la misión en el backend congelado y comparar pose, contactos,
eventos, llegada y puntuación. Es el hueco que META-WORLD-2 dejó declarado en
su §6.

— R.N.
