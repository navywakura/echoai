# Claude — XFER-1c: que `green()` lea la evidencia

XFER-1b corrigió la implementación y conserva el resultado causal:

```text
B                         208 vs 152 · gain +56
C                         224 vs 152 · gain +72
agregado                  +128
patrón transfer           96/96
PATTERN-0                 80/40/+40
```

Los 24 tests focales y la suite de 467 pruebas pasan. No cambies física,
rewards, turnos, posiciones, riff, CAM/Q/T/PatternMemory ni `loop.py`.

Pero `green()` todavía cree los resúmenes que el informe escribe sobre su
propia evidencia. Codex reprodujo estos falsos verdes:

```python
r = xfer1.experiment()

b = deepcopy(r); b["rows"] = {}
xfer1.green(b) is True

b = deepcopy(r)
b["rows"][PARK_B]["same_agent_object"] = False
xfer1.green(b) is True

b = deepcopy(r)
b["rows"][PARK_B]["protocol_signatures"]["scratch"]["ask_enabled"] = True
xfer1.green(b) is True

b = deepcopy(r)
b["arm_metrics"][PARK_B]["scratch"]["cortex_calls"] = 1
xfer1.green(b) is True

b = deepcopy(r); b["channel"]["projection_matches"] = False
xfer1.green(b) is True

b = deepcopy(r)
b["rows"][PARK_B]["ablation"]["mapping_matched"] = False
xfer1.green(b) is True
```

La causa es única: los datos crudos viven en `rows`, `arm_metrics`,
`channel` y `ablation`, pero la puerta sólo consulta copias resumen de nivel
superior. La corrida nominal es buena; el certificado aún puede contradecirse
y seguir verde.

---

## 1. Una autoridad por afirmación

Haz que `green()` valide la forma del informe y derive desde la evidencia:

- deben existir exactamente las filas B y C necesarias;
- cada fila debe decir `same_agent_object=true`;
- cada fila debe contener `transfer`, `scratch` y `age` en
  `protocol_signatures`, y `signatures_match(...)` debe dar `true` sobre esas
  firmas reales;
- `protocol_signatures_match` de nivel superior, si se conserva, debe ser
  igual a la conjunción recomputada; `matched_flags` no puede ser otra
  autoridad independiente;
- `arm_metrics` debe contener los tres brazos de B y C; recalcula desde ahí
  `all_arms_false_facts`, `all_arms_destroyed`, `all_arms_cortex_calls` y
  `all_arms_cortex_rejected`, y exige los cuatro a cero;
- `llm_calls` debe coincidir con la suma recomputada de llamadas al córtex;
- las claves superiores de ablación deben coincidir con
  `rows[B/C]["ablation"]`; valida `mapping_matched`, puntos, slots conocidos,
  hits, unknown y writes desde esas filas;
- `pattern_channel_matches_t` debe derivarse dentro de `green()` desde
  `report["channel"]`: `counts_match`, `projection_matches`, silencio ante
  rechazo y `pattern_observations == t_observations - cuts`.

Puedes eliminar resúmenes redundantes o conservarlos atados por igualdad.
No vale arreglarlo añadiendo otro booleano resumen.

Un informe ausente o malformado debe devolver `False`, no lanzar una traza.

---

## 2. Auditar de verdad el rechazo del `self_model`

`channel_audit()` prueba hoy el silencio de Pattern con su contador, pero
para T sólo compara `quiet.t.pred[0]`. Esa fila arbitraria puede quedarse
igual aunque T haya aprendido en otro slot.

En el brazo `_Refuses`, instrumenta las llamadas reales a ambos métodos:

```text
refused_t_observations          0
refused_pattern_observations    0
```

El veredicto `refused_step_silences_both` debe derivarse de esos dos
contadores. Añade un contraejemplo donde T recibe una observación después del
rechazo en un slot distinto de cero: la auditoría debe caer.

No toques el hook de `loop.py`: la implementación actual coloca T y Pattern
en la misma rama y está bien; el defecto está en cómo se prueba.

---

## 3. Mutantes obligatorios

Añade mutantes independientes, con los resúmenes superiores deliberadamente
dejados en verde:

1. `rows` borradas o malformadas;
2. una fila dice `same_agent_object=false`;
3. la firma del scratch difiere;
4. un scratch registra `cortex_calls=1`;
5. un brazo registra `cortex_rejected=1`;
6. la ablación cruda dice `mapping_matched=false`;
7. el canal crudo dice `projection_matches=false`;
8. tras rechazo, T recibe una observación fuera de la fila cero.

La batería conserva la disciplina TALK-1c: requeridos completos, nombres
únicos, entradas válidas, ningún vivo presente o futuro, contadores
recalculados desde la lista.

---

## Cierre

Reproduce literalmente los seis falsos verdes del inicio: todos deben dar
`False`. Después demuestra que la corrida honesta sigue dando exactamente:

```text
B 208 / 152 / +56
C 224 / 152 / +72
agregado +128
trained 96 / empty 0 / writes 0
channel 64 / 62 / cuts 2
PATTERN-0 80 / 40 / +40
```

Banco:

```bash
PYTHONPATH=. python3 -m echoai.nexus0.xfer1
PYTHONPATH=. python3 -m echoai.tests.test_nexus0
PYTHONPATH=. python3 -m echoai.nexus0.pattern0
PYTHONPATH=. python3 -m echoai.nexus0.talk1
PYTHONPATH=. python3 -m echoai.nexus0.signc
PYTHONPATH=. python3 -m echoai.nexus0.graph
PYTHONPATH=. python3 -m echoai.nexus0.room1
PYTHONPATH=. python3 -m echoai.nexus0.bench
```

Reporta contraejemplos antes/después, tests focales, suite, batería,
determinismo y archivos tocados. Hasta que los datos crudos y el veredicto no
puedan contradecirse: **XFER-1 sigue rojo y ECHO-1 sigue abierto**.
