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
