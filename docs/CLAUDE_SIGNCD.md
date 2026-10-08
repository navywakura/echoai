# Claude — SIGN-Cd: el átomo de acción ocupa el campo de relación

SIGN-Cc está verde y no se reabre. La primera puerta válida con el 4B
queda **roja**: el modelo estuvo cargado, hubo ocho inferencias reales,
`qwen_rejected=0`, ROI +16 y dos paráfrasis ganadas, pero el letrero
canónico de peligro no produjo una propuesta `avoid`.

La salida directa explica el rojo:

```text
goal canonical      YO → UNIR → AQUI @AHORA
threat canonical    AMOR → CAMBIAR → TEMER @AHORA
```

La segunda línea es un WSP válido para la gramática general, pero pone
`CAMBIAR` en REL y `TEMER` en DST. El loop sólo traduce relaciones de
acción; por eso la respuesta no fue rechazada y tampoco se convirtió en
propuesta. No bajes `green()` y no enseñes esa frase al código.

## Pregunta única

**¿puede el operador exigir que la decisión del 4B tenga forma de acción,
sin reducir el vocabulario general del córtex ni hardcodear el letrero?**

## Contrato

Conserva `nexus0/cortex.gbnf` byte-idéntico: sigue siendo el contrato WSP
general. Añade una gramática específica del operador SIGN-C, por ejemplo
`nexus0/cortex_action.gbnf`, con esta forma semántica:

```text
YO → {UNIR | TEMER | OBSERVAR | NONE} → AQUI @AHORA
```

- `UNIR`, `TEMER` y `OBSERVAR` son las tres acciones existentes.
- `NONE` permite abstenerse; parsea como átomo válido pero no se mapea a
  acción. La gramática no debe obligar a inventar una acción.
- SRC, DST y TIME quedan fijados porque este informe puntúa una propuesta
  local, no composición libre de pensamientos.
- No añadas palabras del corpus, regex semántica, if por frase ni tabla de
  respuestas.

`qwen_signc.py` debe seleccionar esa gramática sólo para sus llamadas al
wrapper y restaurar cualquier `NAVI_QWEN_GBNF` previo. Qwen-0 y cualquier
otro consumidor de `qwen_cortex.py` siguen usando `cortex.gbnf`. No cambies
el prompt actual todavía: la variable aislada aquí es el esquema de salida.

El informe de operador debe registrar como mínimo la ruta de la gramática,
un hash estable y `action_grammar=true`. `green()` debe exigirlo, además de
las cláusulas actuales; nunca debe aprobar una corrida hecha por accidente
con la gramática general.

## Medida previa real — no convertir en expectativa de CI

Codex probó esa gramática directamente contra el servidor ya levantado,
sin modificar archivos:

```text
goal    0 UNIR   1 UNIR   2 UNIR   3 UNIR
threat  0 TEMER  1 UNIR   2 UNIR   3 TEMER
```

Eso sería 6/8, cuatro de seis paráfrasis frente a cero del stub, ambos
canónicos correctos y ROI +16. Los dos errores de amenaza deben quedar
visibles: no se retoca el dataset ni se rebaja la clave para esconderlos.
CI no exige esos números ni arranca pesos; Roger repite la puerta después.

## Tests sin modelo

1. La gramática general queda byte-idéntica y continúa aceptando los 42
   átomos en los cuatro campos.
2. La gramática SIGN-C sólo permite la forma y las cuatro relaciones
   anteriores; `CAMBIAR` en REL y `TEMER` en DST no caben.
3. `NONE` atraviesa `parse_reply` pero no crea `cortex_action`.
4. `qwen_signc` selecciona la gramática específica y restaura el entorno
   anterior incluso si una fila falla.
5. El informe separa gramática, proposal y acción corporal; `green()` cae
   si `action_grammar=false`, la ruta/hash no corresponde o falta cualquiera
   de los dos proposals canónicos.
6. SIGN-Cc conserva la matriz: OBSERVAR en THREAT sigue hit false aunque el
   gate produzca avoid +8.
7. Sin modelo/servidor, el runner sigue rc=1 y `green=false`.
8. El informe Qwen-0 anterior y los informes del lab no se pisan.

## No tocar

`loop.py`, `signc.py`, `cortex.py`, `parse_reply`, `cortex.gbnf`, gate,
recompensas, CAM/T/Q/WSP, frases del banco ni umbrales de `green()`. No
añadas un segundo bus ni una cuarta acción. No empieces TALK-1.

## Banco de Claude

```bash
PYTHONPATH=. python3 -m echoai.tests.test_nexus0
PYTHONPATH=. python3 -m echoai.nexus0.bench
PYTHONPATH=. python3 -m echoai.nexus0.signc
PYTHONPATH=. python3 -m echoai.nexus0.qwen_signc  # rojo sin servidor: esperado
```

Después Roger, con el servidor ya levantado, ejecuta:

```bash
PYTHONPATH=. python3 -m echoai.nexus0.qwen_signc
```

Si el canónico de amenaza no propone `avoid`, si el informe no prueba qué
gramática usó o si Qwen-0 deja de ser reproducible, **rojo**. No piques
TALK-1.
