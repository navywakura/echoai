# Claude — SIGN-Cc: puntúa el átomo, no el cuerpo

SIGN-Cb está **verde Codex**. No reabras `loop.py`: una sola línea dice
`conflict`, el turno de consumo queda `off`, la propuesta conserva su
latencia y los 375 tests pasan.

La puerta Qwen aún no se puede operar porque su evaluador tiene un falso
positivo. `qwen_signc._row().hit()` dice que puntúa lo que produjo el reloj
lento, pero compara `action_at_landing`, que es la acción corporal **después
del gate**:

```python
return proposal_consumed_next_turn and action_at_landing == want
```

Mutante reproducido:

```text
world                    threat
respuesta del córtex     YO → OBSERVAR → AQUI @AHORA
propuesta consumida      wait                 # verbo equivocado
gate                     wait → avoid         # U >= U_SHORT
acción / recompensa      avoid / +8
qwen_hit actual          true                 # falso positivo
```

Silencio ya da `false` porque no consume propuesta, y `UNIR` también cae
porque el gate no rescata `approach` cuando hay extract. `OBSERVAR` es el
mutante que separa de verdad «habló» de «nombró el verbo correcto».

## Pregunta única

**¿el informe de operador puntúa el verbo que propuso el córtex, aunque el
gate convierta después la acción corporal en otra?**

## KPI — todo a la vez

```text
hit = proposal_consumed_next_turn
      and consume_line.cortex_action == want

THREAT + TEMER/avoid       hit true
THREAT + OBSERVAR/wait     hit false, aunque el cuerpo haga avoid +8
THREAT + UNIR/approach     hit false
THREAT + silencio          hit false
GOAL   + UNIR/approach     hit true
GOAL   + TEMER/avoid       hit false
```

El informe debe separar nombres sin ambigüedad:

```text
qwen_proposal              verbo del `consume_line.cortex_action`
qwen_action                acción corporal después del gate
stub_proposal              verbo del stub consumido
stub_action                acción corporal después del gate
canonical_threat_qwen_proposal == avoid
qwen_action_at_X / CortexROI pueden seguir describiendo el cuerpo
```

`green()` debe exigir el **proposal** correcto en las canónicas de GOAL y
THREAT. No basta con la acción final ni con recompensa positiva.

## Tests que deben fallar antes

1. Un córtex determinista que devuelve `OBSERVAR` ante THREAT habla y se
   consume, el gate obtiene `avoid +8`, pero `qwen_hit == false`.
2. `TEMER` ante THREAT da proposal `avoid` y hit true.
3. `UNIR` ante GOAL da proposal `approach` y hit true.
4. Doblar sólo `canonical_threat_qwen_proposal` hace caer `green()`.
5. El stub sigue 2 canónicas / 0 paráfrasis; silencio no puntúa.
6. El runner sin modelo sigue honestamente `model_configured=false` y
   `green=false`.

## Alcance

Toca sólo `nexus0/qwen_signc.py`, sus tests y el informe Qwen regenerado
sin modelo. No toques `loop.py`, `signc.py`, `qwen_cortex.py`, el prompt del
modelo, gate, recompensas, stub, CAM/T/Q, WSP ni informes anteriores. No
descargues ni arranques pesos. No empieces TALK-1.

## Banco de entrega

```bash
PYTHONPATH=. python3 -m echoai.tests.test_nexus0
PYTHONPATH=. python3 -m echoai.nexus0.bench
PYTHONPATH=. python3 -m echoai.nexus0.signc
PYTHONPATH=. python3 -m echoai.nexus0.qwen_signc   # rc=1 sin modelo: esperado
```

Entrega los cuatro mutantes de verbo con propuesta, acción corporal y hit;
los candados SIGN-Cb; y md5 de informes ajenos. Si `OBSERVAR` ante THREAT
cuenta como acierto porque el gate salvó al cuerpo, **rojo**.
