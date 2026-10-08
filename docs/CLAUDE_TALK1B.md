# Claude — TALK-1b: que el auditor no pueda equivocarse con el narrador

TALK-1 tiene un buen narrador y aislamiento real en el código actual, pero
la puerta es roja: Codex encontró subtítulos falsos que `audit()` acepta sin
fallos. No reabras SIGN-C ni rediseñes la salida. Corrige sólo la prueba de
fidelidad y sus candados.

## Los contraejemplos reproducibles

Con la fila `pose_full`, cuyo valor real es
`(1, 2, 0) rumbo 3 marco 1`, hoy todos éstos dan `audit(...) == []`:

```text
(100, 200, 0) rumbo 3 marco 1
(2, 1, 0) rumbo 3 marco 1
(1, 2, 0) rumbo 3 marco 1 con obstáculo
```

Y una fila sin frame acepta:

```text
(0, 0, 2) rumbo 5 marco 99
```

La causa es que pose se audita buscando cada número como subcadena, no por
igualdad. Así, `1 in 100`, el orden no importa y se puede añadir información
inventada.

Hay dos falsos verdes más:

1. `audit()` comparte `talk.REASON_ES` con `render()`. Si ambos cambian
   `miss` por «despertó por celda nueva», la línea falsa pasa.
2. `causal_findings()` no ve ni `Path(p).open('w').write('x')` ni
   `open(p, mode).write('x')`. El escáner interpreta la posición del modo
   como si toda llamada fuese el builtin y no inspecciona `write()`.

Los 14 tests actuales pasan; ése es precisamente el defecto: la puerta no
mata equivalentes directos de los mutantes que dice cubrir.

## Arreglo 1 — pose exacta

El auditor debe construir por su cuenta la única cadena válida de pose y
compararla por igualdad exacta:

```text
x/y/z null                  sin pose
pose, sin heading/frame     (x, y, z)
pose + heading              (x, y, z) rumbo h
pose + heading + frame      (x, y, z) rumbo h marco f
```

No llames `talk._pose`. Usa una función/tabla propia en `talk1.py`. Mata los
cuatro ejemplos anteriores y además coordenadas reordenadas, valores con
prefijo/sufijo y heading/frame inventados u omitidos.

Endurece `talk.validate()` sólo donde expresa el contrato existente:

- si no hay pose, `heading` **y** `frame` deben ser null;
- `q_row` sólo puede tener 3 o 4 enteros;
- `action` debe caber en la fila Q que produjo la decisión.

No cambies las 22 claves ni el texto correcto que ya produce `render()`.

## Arreglo 2 — auditor independiente de verdad

El camino de auditoría no debe leer ninguna tabla semántica mutable del
redactor. Define en `talk1.py` sus propias constantes para:

- las 16 etiquetas y el separador;
- las siete traducciones de ATTEND;
- cuerpo, propuesta y gate (éstas ya son propias).

`parse()` y `audit()` no deben referenciar `talk.LABELS`, `talk.SEP`,
`talk.REASON_NAME`, `talk.REASON_ES`, `talk.BODY`, `talk.PROPOSAL`,
`talk.GATE`, `talk._pose` ni `talk.render`. Sólo reciben texto + registro.

Añade pruebas que tuerzan individualmente las siete razones del redactor y
demuestren que el auditor las rechaza, no sólo conflict/off. Fija también
las 16 etiquetas y su orden desde el lado del auditor.

## Arreglo 3 — aislamiento que mate escrituras equivalentes

El `talk.py` actual es seguro y debe seguir igual. Lo que falla es el
escáner. Hazlo conservador:

- cualquier llamada `.open(...)` en el traductor es hallazgo; hoy no la
  necesita porque usa `Path.read_text`;
- detecta `write`, `writelines`, `truncate` y las operaciones Path que ya
  prohíbe;
- permite únicamente `sys.stdout.write` y `sys.stderr.write`, que son la
  salida contractual de la CLI;
- un modo dinámico o no demostrablemente de lectura no cuenta como seguro;
- detecta `eval`, `exec` y `__import__` como escapes dinámicos.

Mutantes obligatorios:

```python
Path(p).open("w").write("x")
Path(p).open(mode).write("x")
open(p, mode).write("x")
fh.write("x")
__import__("echoai.nexus0.loop")
```

Todos deben producir hallazgos. No hace falta afirmar que un escáner AST es
un sandbox universal; sí debe cubrir todas las formas equivalentes que el
banco dice haber prohibido.

## Arreglo 4 — que no se puedan borrar mutantes del informe

Hoy `green()` exige `mutants_total >= 12`. Se pueden eliminar categorías
enteras y conservar verde. Define un conjunto explícito
`REQUIRED_MUTANTS` y haz que `green(report)` compruebe, desde la lista
`report["mutants"]`, que:

- están todos los nombres requeridos;
- no hay nombres duplicados;
- todos están muertos;
- están incluidos los cuatro de pose, los siete de razones y las cinco
  vías de escritura/escape anteriores.

Un test debe borrar cada mutante requerido, uno por uno, y comprobar que
`green()` cae. Otro duplica un nombre. No confíes sólo en los contadores.

## Conserva lo que ya está bien

- una línea póstuma por registro, mismo orden;
- prevalidación completa antes de stdout;
- action, proposal y gate en cláusulas distintas;
- `wait` nunca narrado como movimiento;
- no «porque» ni conjunciones causales;
- WSP y Q literales;
- fuente byte-idéntica antes/después;
- traductor con sólo biblioteca estándar y sin imports de echoAI;
- las filas reales SIGN-C conflict/consume y OPEN-1;
- `thought.KEYS=22`, `ACTION_NAME` con open;
- ningún cambio a loop, thought, gate, cortex, gramáticas, SIGN-C o mundos.

## Cierre

```text
TranslationConsistency       100%
pose false subtitles         0 aceptados
shared-table mutants         0 supervivientes
write/escape mutants         0 supervivientes
required mutants present     todos, sin duplicados
causal_writes                0 en talk.py real
```

Ejecuta:

```bash
PYTHONPATH=. python3 -m echoai.nexus0.talk1
PYTHONPATH=. python3 -m echoai.tests.test_nexus0
PYTHONPATH=. python3 -m echoai.nexus0.bench
PYTHONPATH=. python3 -m echoai.nexus0.signc
```

Reporta los contraejemplos antes/después, mutantes, tests y archivos
tocados. No empieces PATTERN-0.

Si una pose falsa, una razón compartida o una escritura equivalente vuelve
a pasar, TALK-1 sigue rojo.
