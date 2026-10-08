# Claude — TALK-1: subtítulos póstumos, nunca pensamiento causal

SIGN-C está cerrado. La puerta real en Fedora/Qwen3-4B dio `green=true`:

```text
qwen_hits / rows              6 / 8
paraphrase_qwen / stub        4 / 6  frente a 0 / 6
canonical goal proposal       approach
canonical threat proposal     avoid
CortexROI                     +16
qwen_calls / rejected         8 / 0
false_facts                   0
action/general grammar sha    distintos y correctos
```

No reabras SIGN-C. El siguiente y único tajo es **TALK-1**.

## Pregunta única

¿Puede una herramienta externa leer cada línea real de `thought.jsonl` y
contarla en español con fidelidad mecánicamente comprobable, **después** de
la acción y sin ninguna vía causal de vuelta al animal?

```text
input                         thought.jsonl, esquema exacto KEYS=22
output                        subtítulos póstumos en español
TranslationConsistency       100 % en matriz y mutantes
cardinalidad / orden          1 subtítulo por registro, mismo orden
causal writes                 0 a Agent/CAM/T/Q/gate/córtex/mundo
```

El subtítulo no es pensamiento. El pensamiento que existió ya está en el
jsonl. No escribas una explicación de cadena de pensamiento y no atribuyas
una acción a una razón que el registro no demuestra.

## Semántica temporal que debes respetar

`thought.py` registra el turno como el loop lo vio:

- `action` es lo que hizo el **cuerpo después del gate**;
- `cortex_action` es la propuesta lenta consumida en ese turno, o `null`;
- `attend_on/reason_name` dicen si ATTEND despertó en ese turno;
- en SIGN-C, la línea del conflicto tiene `attend_on=true`, razón
  `conflict` y `cortex_action=null`;
- la línea siguiente consume la propuesta con `attend_on=false`, razón
  `off` y `cortex_action=approach`;
- `gate_decision` puede hacer que propuesta y acción corporal difieran;
- `reward` es el resultado que devolvió el mundo para esa acción;
- `t_pred`, `n`, `s` y `delta` son evidencia, no motivos narrativos.

Por tanto, no uses «porque». Una línea puede decir por separado «ATTEND
despertó por conflicto» y «el cuerpo se acercó», pero no «se acercó porque
hubo conflicto» salvo que el propio registro contenga la propuesta
consumida en ese mismo turno. Incluso ahí, mantén propuesta y cuerpo como
dos hechos separados: el gate conserva la última palabra.

El caso mutante central es obligatorio:

```text
action=wait en EMPTY
```

jamás puede narrarse como «giró», «avanzó», «retrocedió», «se acercó», «se
alejó» o «abrió». Del mismo modo, `cortex_action=wait` con `action=avoid`
debe decir que el córtex propuso esperar y que el cuerpo evitó; no puede
acreditar al córtex el reflejo del gate. Es la misma separación que cerró
SIGN-Cc.

## Implementación mínima

Crea un traductor póstumo de biblioteca estándar, por ejemplo
`nexus0/talk.py`, con API pequeña y CLI:

```text
render(record) -> str
translate(path) -> lista/iterador de subtítulos
python3 -m echoai.nexus0.talk PATH
```

La salida debe ser español controlado y legible, no prosa libre. Una forma
válida es una línea por turno con cláusulas separadas:

```text
Turno 513 · cuerpo: se acercó · recompensa: +16 · atención: apagada ·
córtex: propuso acercarse · gate: aceptó · T predijo: 187 · ...
```

No fijes ese texto literal si encuentras una forma más clara, pero la
gramática de salida debe ser cerrada y auditable. Como mínimo distingue:

- las cuatro acciones: `approach`, `avoid`, `wait`, `open`;
- propuesta del córtex frente a acción del cuerpo;
- atención apagada frente a cada `reason_name`, incluido `conflict`;
- `gate_decision` OK/MODIFY/BLOCK;
- recompensa positiva, cero y negativa;
- predicción T conocida frente a `null`;
- flags `n/s/delta`;
- celda/kind y, cuando existen, pose/heading/frame;
- contadores de preguntas y llamadas;
- Q y WSP como evidencia literal, sin reinterpretarlos.

Valida las 22 claves y tipos antes de emitir. JSON roto, clave ausente,
acción fuera de rango o forma imposible debe ser error explícito y salida
no cero; no inventes defaults y no saltes líneas silenciosamente. Prevalida
el fichero completo para no producir media narración que parezca completa.

Puedes separar un `talk1.py` para el banco. El ejecutable de entrega debe
crear sólo su informe propio (`lab/nexus0_talk1_report.json`) y, si decides
guardar los subtítulos, un fichero nuevo con nombre TALK-1. Nunca modifica
el jsonl fuente ni pisa informes anteriores.

## Cómo medir TranslationConsistency sin circularidad

No puntúes «el renderer coincide consigo mismo». Construye un auditor
independiente de la función que redacta:

1. una matriz de registros deriva expectativas semánticas;
2. el auditor comprueba las cláusulas controladas emitidas;
3. los tests incluyen salidas mutadas escritas a mano;
4. cada mutante falso debe hacer caer consistencia y `green()`.

La matriz debe cubrir al menos:

- actions 0/1/2/3;
- reward positivo/cero/negativo;
- pose completa y cinco `null` del anillo;
- ATTEND off y las razones conocidas, especialmente conflict;
- `cortex_action=null` y las propuestas approach/avoid/wait;
- propuesta wait + cuerpo avoid + gate MODIFY;
- la pareja real conflict/consume de SIGN-Cb;
- un turno OPEN-1;
- predicción T conocida/desconocida y `n/s/delta` 0/1.

El informe debe exponer números, no sólo una bandera:

```text
source_records
narrated_records
same_order
source_sha256_before / after
consistency_hits / consistency_total
TranslationConsistency       100
mutants_killed / mutants_total
thought_keys                  22
causal_writes                 0
green
```

`green()` debe recomputar las condiciones desde esos campos. Añade tests
que doblen cada candado del informe; no basta pasarle sólo el informe bueno.

## Mutantes mínimos

Mata explícitamente, al menos:

1. `wait` narrado como movimiento o apertura;
2. approach y avoid intercambiados;
3. open narrado como approach;
4. signo de reward invertido;
5. ATTEND off narrado como conflict, o conflict omitido;
6. `cortex_action=null` narrado como propuesta;
7. propuesta wait acreditada como avoid porque el cuerpo fue salvado;
8. `t_pred=null` narrado como predicción conocida;
9. registro omitido, duplicado o reordenado;
10. una narración que usa «porque» para inventar causalidad;
11. traductor que altera el jsonl fuente;
12. `green()` que deja de exigir cualquiera de los candados anteriores.

No hardcodees el fixture para reconocerlo por turno/celda. Inunda valores o
genera la matriz; el significado sale de los campos.

## Aislamiento causal

El módulo traductor debe ser realmente externo:

- el loop no lo importa ni lo llama;
- no importa `Agent`, loop, CAM, T, Q, gate, cortex ni mundos;
- no usa `parse_reply`, `NAVI_CORTEX_*`, red, subprocess ni servidor;
- abre el jsonl sólo para lectura;
- no hay callback, pipe ni fichero que el animal vuelva a consumir;
- no añade `story`, `events`, texto ni otra clave a `thought.KEYS`;
- no añade otro WSP ni otro bus.

Usa sólo biblioteca estándar. Puedes duplicar las cuatro etiquetas de
acción dentro del traductor y fijarlas contra `thought.ACTION_NAME` desde
los tests; es preferible a importar el animal en tiempo de ejecución.

No hace falta Qwen para cerrar TALK-1. Si quieres dejar una nota sobre un
embellecedor Qwen futuro, será otro operador opcional que consuma los
subtítulos ya auditados; no lo implementes en este tajo y nunca lo hagas
parte de `green()`.

## Candados que no se mueven

```text
thought.KEYS                  22 exactas
thought.ACTION_NAME           approach, avoid, wait, open
N_ACTIONS default             3
WSP                           16 bytes, único bus
anillo default                [-12,+5,0], +80, 33/1/217, cortex_calls 0
anillo --cortex               36/256
SIGN-C                        informes y hashes intactos
false_facts / destroyed       0 / 0
```

No toques `loop.py`, `thought.py`, `gate.py`, `cortex.py`, las gramáticas,
SIGN-C ni los mundos para facilitar la narración. El consumidor se adapta
al contrato existente; el animal no se adapta al consumidor.

## Entrega

```bash
PYTHONPATH=. python3 -m echoai.nexus0.talk1
PYTHONPATH=. python3 -m echoai.tests.test_nexus0
PYTHONPATH=. python3 -m echoai.nexus0.bench
PYTHONPATH=. python3 -m echoai.nexus0.signc
```

Reporta archivos tocados, tests antes/después, matriz completa, mutantes y
md5/sha de los informes anteriores. No empieces PATTERN-0.

Si el narrador embellece, atribuye causa, confunde propuesta con cuerpo,
modifica el jsonl o necesita entrar en el loop, **TALK-1 es rojo**.
