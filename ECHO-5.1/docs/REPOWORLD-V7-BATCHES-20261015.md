# RepoWorld V7 — sesiones acotadas y reanudación

La campaña V6 se detuvo antes del panel principal por incompatibilidad entre
la duración de una fase y los topes del worker. Quedan preservadas sus 11
entregas de calibración, cinco celdas no iniciadas y los recibos originales.
No se consultaron resultados finales ni se cambió la selección de instancias.

`run_repoworld.py run` admite `--batch-seconds` (1801–6600, defecto 6000) y
`--max-episodes`. La pausa ocurre antes de preparar el siguiente episodio,
reservando 1800 segundos para un episodio acotado. Se firma `batch-paused`,
se apaga el proveedor y se conserva el calendario pendiente. Una pausa no
crea `not_started`, no modifica denominadores y no reinicia presupuesto.
Los topes globales y por fase siguen produciendo `not_started` cuando se
agotan. La reanudación autentica entregas anteriores y no vuelve a ejecutarlas.

Cuatro pruebas nuevas verifican pausa/reanudación sin duplicados, tiempo
acumulado, prioridad de los topes registrados y rechazo de parámetros antes
de acceder al proveedor. Fallaron antes de la implementación y pasan después.
Suite completa: **459 pasadas, tres omitidas**, cero fallos. Smoke hermético:
rollback observado, replay idéntico, sin reservas pendientes. Preflight 36/36
y controles oficiales 36/36 reatestados, sin reejecutar sus pruebas originales.

Artefactos: `ECHO-5.1/artifacts/repoworld-gates-v7-20261015/`. Los operadores
usan sesiones de relay de 8400 s, límite de proceso de 9000 s y lotes de
6000 s. El empaquetado se comprobó offline con un broker ficticio, sin red ni
GPU. Cada sesión tiene directorio, claves y diario propios; solo se permite
una sesión nueva después de una pausa limpia, sin inferencias pendientes,
y con apagado confirmado. Una interrupción exige recuperar su diario original.
La cuota física incluye cargas del modelo entre sesiones; el operador la
comprueba además del presupuesto registrado por el supervisor.

No cambia el protocolo de los brazos, las cuotas por episodio, el modelo,
los prompts ni el evaluador. Se mantienen 24 issues principales × cuatro
brazos, más ablación y memoria, 150 celdas en total. El sello V6 deja de ser
ejecutable con este código. La nueva calibración, el nuevo sello y los
resultados oficiales se documentarán aquí al obtener evidencia.

## Calibración observada y sello V7

Código: `d1759ef`. Calibración reservada SymPy-19007, brazo E, semilla 73:
assessment funcional válido, vista completa del método antes del traspaso,
**17.955 tokens disponibles al entrar el editor**, dos parches retenidos y
checks públicos pasados. Finaliza `budget_stopped`: 16.516 tokens, 11 llamadas,
tres intentos de parche, cuatro ejecuciones de checks, 188 recibos válidos,
`destroyed=0` y cero reservas pendientes. El diff retenido es el mismo que
en V6; no se ha comprobado la resolución oficial del issue. Los checks
públicos de `test_basic.py` no equivalen a cobertura del fallo de BlockMatrix.

Kernel privado `rogeernavarro/echo51-repoworld-batch-v7-20261015`, versión 1:
COMPLETE, 65/65 capas en dos T4, preparación 391,191 s y total 689,437 s.
Worker detenido sin errores; relay y túnel apagados. Cuota 20,78 → **20,59 h**.

Las cinco compuertas quedan vinculadas al contrato operativo sellado en
`remote/sealed/SWE-CONTRACT.json` (`launch_enabled=true`). Lock
`remote/sealed/SWE-RUN-LOCK.json`, SHA-256:
`6415ca83691507e71dc0b627c2e2634ed788b77e97f6caab5875e8ecc3a01a65`.
El archivo de diseño en `docs/` sigue siendo la entrada, no el contrato operativo.

El comando `python3 ECHO-5.1/artifacts/repoworld-gates-v7-20261015/campaign_driver.py`
ejecuta el calendario sellado por sesiones, confirma cada apagado y conserva
la cuota inicial entre reanudaciones. Antes de una sesión nueva autentica las
entregas ya completadas. Solo después de congelar las 150 celdas permite
evaluar con el curador y exportar las figuras. Una pausa de lote deja pendiente
el siguiente episodio; no garantiza que alcance el presupuesto para todo el panel.
