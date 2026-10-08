# Claude — TALK-1c: ningún mutante vivo, tampoco uno futuro

TALK-1b cerró correctamente los ocho contraejemplos de pose, tablas
compartidas y escritura. Los 24 tests TALK pasan. No reabras nada de eso.

Queda un único falso verde en `green()`:

```python
r = talk1.experiment()
r["mutants"].append({
    "mutant": "extra futuro vivo", "killed": False, "failures": []})
r["mutants_total"] = len(r["mutants"])
r["mutants_killed"] = r["mutants_total"]  # contador mentiroso
assert talk1.green(r) is True               # BUG
```

Esto contradice el comentario de `green()` que promete proteger «every
mutant in the battery, required or not» y la afirmación de que la puerta
recomputa desde `report["mutants"]`.

## Causa

`battery_state()["alive"]` sólo considera la intersección con
`REQUIRED_MUTANTS`. Después `green()` compara los dos contadores del
informe entre sí, pero no vuelve a contar los `killed` reales. Por eso un
mutante adicional vivo desaparece de ambos controles.

## Arreglo mínimo

Desde `report["mutants"]`, y sin confiar en resúmenes, recomputa:

- nombres presentes;
- nombres duplicados;
- requeridos ausentes;
- **todos** los mutantes vivos, requeridos o futuros;
- total real;
- muertos reales.

`green()` debe exigir simultáneamente:

```text
required missing             []
duplicated names             []
alive mutants                []
mutants_total                == len(mutants)
mutants_killed               == count(killed is true)
mutants_killed               == mutants_total
```

Un mutante adicional muerto puede aceptarse: permite ampliar la batería.
Uno adicional vivo debe ponerla roja aunque los campos resumen digan que
murió. Un elemento sin nombre o sin booleano `killed` debe producir rojo,
no una excepción que tumbe al operador.

## Tests obligatorios

1. Reproduce literalmente el falso verde anterior y exige false.
2. Añade un mutante futuro muerto, actualiza contadores reales y conserva
   green true.
3. Miente sólo en `mutants_total`: rojo.
4. Miente sólo en `mutants_killed`: rojo.
5. Añade un mutante sin `mutant`, sin `killed` o con `killed=1`: rojo limpio,
   sin excepción.
6. Conserva los 42 requeridos presentes, únicos y muertos.

No basta añadir el nombre futuro a `REQUIRED_MUTANTS`: el punto es que la
puerta proteja automáticamente las ampliaciones posteriores.

## No tocar

`talk.py`, `render`, `validate`, `parse`, `audit`, `want_pose`, el escáner,
la matriz, el animal, SIGN-C y los informes anteriores. Éste es sólo un
candado del informe.

Ejecuta:

```bash
PYTHONPATH=. python3 -m echoai.nexus0.talk1
PYTHONPATH=. python3 -m echoai.tests.test_nexus0
PYTHONPATH=. python3 -m echoai.nexus0.bench
PYTHONPATH=. python3 -m echoai.nexus0.signc
```

Reporta el contraejemplo antes/después, tests y archivos tocados. No
empieces PATTERN-0.

Si cualquier elemento vivo de `report["mutants"]` puede coexistir con
`green=true`, TALK-1 sigue rojo.
