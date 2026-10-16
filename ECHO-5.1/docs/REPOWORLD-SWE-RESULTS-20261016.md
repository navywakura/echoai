# ECHO-5.1 · SWE-bench Lite V8: resultados y límites

Informe final de la ejecución cerrada, 2026-10-16T09:17:29+00:00. Rama local
`research/echo-5.1-pcworld1`; sin push. Código experimental congelado en
`209285d`; `41320c5` documentó la preparación. Este informe describe una
**campaña incompleta con evaluación final completa de todas sus entregas**.

## 1. Veredicto

Sobre los mismos 17 issues ejecutados: **S=2/17**, **I2=1/17**, **F=1/17**, **E=1/17**. El panel registrado era de
24 issues por brazo; los siete no iniciados se conservan en el denominador
registrado y se identifican expresamente. **No se ha demostrado una ventaja
de resolución de ECHO ni procede cerrar ECHO-5.1 en verde científico.**

E consumió 34,14 % menos tokens que S, pero ese ahorro total no
equivale a una mejora de coste por solución. S resolvió Django-11179 y
Requests-2317; E resolvió Django-11179. El coste agregado por issue resuelto
es 266.562 tokens en E frente a
202.362 en S. Tampoco se demuestra una
superioridad general de S: son pocos pares, una semilla y una ejecución cortada
por tiempo. Se informa el resultado observado sin extrapolarlo a otros modelos,
presupuestos o protocolos.

No se calcula un porcentaje de «alucinaciones reducidas»: el ensayo no define
una medida independiente de alucinación. Errores de formato, código no observado,
agotamientos y tests fallidos se describen por sus eventos verificables, sin
convertirlos en una medida de procesos mentales del modelo.

La infraestructura conserva evidencia verificable, 18.546
registros/recibos contabilizados por la auditoría de episodios, 150 resultados
finales firmados y cero episodios con uso de tokens desconocido. Eso acredita
custodia y contabilidad en su alcance; no convierte un parche, un test público
verde o una firma HMAC en una solución del issue.

## 2. Diseño, exposición y coste

Modelo: Qwen2.5-Coder-32B-Instruct Q4_K_M; revisión y GGUF fijados por el lock,
llama.cpp `b11577`, dos T4 y 65/65 capas cargadas. Semilla 73, temperatura 0,2,
contexto 4.096, entrada máxima 3.200 y salida máxima 768 tokens por llamada.
Por episodio: 25.000 tokens entrada+salida, 24 llamadas LLM, 80 herramientas,
ocho intentos de parche y 1.800 s. I2 conserva dos propuestas independientes
de 11.000 tokens y un selector de 3.000; no es refutación iterativa.

S es el agente único; F usa la secuencia fija de especialistas; E añade
coordinación adaptativa y memoria de refutación. Las herramientas y el
guardarraíl público también están disponibles en S/I2/F. E_no_guard desactiva
la retención condicionada por regresiones públicas válidamente observadas,
pero conserva las comprobaciones comunes de validez y seguridad.

Los candidatos se ejecutaron localmente en Bubblewrap. Kaggle solo realizó
inferencia. Después de congelar todas las entregas, el curador independiente
SWE-bench 4.1.0 ejecutó los tests reservados mediante Podman rootless. No se
repararon ni seleccionaron de nuevo candidatos tras consultar el oráculo.

| Fase | Registrados | Ejecutados | No iniciados | Tokens | Diffs no vacíos |
|---|---|---|---|---|---|
| Principal | 96 | 68 | 28 | 1.281.561 | 17 |
| Calibración de campaña | 16 | 9 | 7 | 200.973 | 4 |
| Ablación E_no_guard | 24 | 24 | 0 | 360.066 | 9 |
| Donantes | 2 | 2 | 0 | 14.782 | 0 |
| Receptores | 12 | 12 | 0 | 150.106 | 0 |

Total: **115 episodios ejecutados, 35 no iniciados y 150 entregas congeladas**;
35 de las 36 instancias registradas tuvieron alguna ejecución. Los 35 no
iniciados son 28 celdas principales y siete de calibración. No son resultados
de inferencia ni se presentan como tests ejecutados y fallidos.

La fase principal cerró con 5,503846 h de ventana registrada y exigía reservar
otros 1.800 s antes de iniciar cada episodio. El siguiente episodio ya no cabía
en su límite de seis horas. Tener cuota física restante no autoriza ampliar
retroactivamente el presupuesto del contrato. No se reabrieron esas celdas.

El panel efectivamente ejecutado contiene diez repositorios; seis de los 17
issues son de Django. Quedaron sin ejecutar en la fase principal:
Scikit-learn-13241, Sphinx-7686/8713 y SymPy-13146/15011/20212/24066.
La paridad entre brazos se conserva en los 17 pares; la estratificación
completa original no. Las calibraciones de desarrollo V6/V7/V8 y su SymPy
reservado no se importan como aciertos de esta campaña.

Se contabilizaron **2.007.488 tokens**, 1.146
llamadas LLM, 1.437 herramientas y
152 intentos de parche. La cuota
observada pasó de 19,82 a **9,95 h**: aproximadamente 9,87 h cargadas, incluida
la recuperación y preparación. Los workers registran 9,843 h
de sesión; es una medida distinta, que tampoco equivale a energía ni a tiempo
de inferencia puro. La calibración V8 previa, unos 0,23 h, queda fuera de esos
totales de campaña. Kaggle, relay y túneles están apagados.

## 3. Resolución oficial y eficiencia

| Brazo | Resueltos / 24 registrados | Resueltos / 17 ejecutados | Diffs no vacíos | Tokens totales | Tokens / ejecutado | Tokens / resuelto |
|---|---|---|---|---|---|---|
| S | 2/24 (8,33 %) | 2/17 (11,76 %) | 4 | 404.724 | 23.807,29 | 202.362,00 |
| I2 | 1/24 (4,17 %) | 1/17 (5,88 %) | 2 | 343.469 | 20.204,06 | 343.469,00 |
| F | 1/24 (4,17 %) | 1/17 (5,88 %) | 6 | 266.806 | 15.694,47 | 266.806,00 |
| E | 1/24 (4,17 %) | 1/17 (5,88 %) | 5 | 266.562 | 15.680,12 | 266.562,00 |

Las tasas sobre 24 son el resultado conservador del panel registrado. Las tasas
sobre 17 describen solo el subconjunto ejecutado y no sustituyen a las primeras.
No se publica ninguna de ellas como puntuación sobre las 300 tareas completas
de SWE-bench Lite.

F gasta 34,08 % menos tokens que S. E gasta solo 0,091 %
menos que F. El descenso no prueba un mejor router ni mejor razonamiento:
hay abandonos tempranos. Los 8 `finished` de F y los
9 de E en el panel principal entregaron diff vacío.
S e I2 terminaron `budget_stopped` en 17/17. En S el consumo varió entre
22.147 y 25.000; no todos consumieron exactamente el tope. Quince casos
registran `ContextOverflow` porque la siguiente generación no cabía en el
presupuesto restante, no porque se emitiera un prompt superior a 3.200 tokens.

### Comparación pareada descriptiva

| E frente a | Pares ejecutados | Gana E | Pierde E | Empate |
|---|---|---|---|---|
| S | 17 | 0 | 1 | 16 |
| I2 | 17 | 0 | 0 | 17 |
| F | 17 | 0 | 0 | 17 |
| E_no_guard | 17 | 0 | 0 | 17 |

Una unidad pareada es un issue, no cada uno de sus cuatro brazos. N=17 no es
N=68 y no garantiza significancia estadística. No se presenta una prueba
confirmatoria de superioridad; los intervalos Wilson de las figuras originales
son descriptivos y no ajustan la dependencia por repositorio. Faltan
repeticiones, mayor cobertura y un análisis preregistrado con potencia adecuada.

### Resultado por issue

`Sí`: resuelto por el harness y con evidencia aceptada por ECHO.
`No`: ejecutado, no resuelto; incluye entrega vacía. `NI`: no iniciado.
E_no_guard ejecutó los 24, por lo que su columna completa no se compara
directamente con el subconjunto de 17 de E.

| Issue | S | I2 | F | E | E_no_guard |
|---|---|---|---|---|---|
| astropy__astropy-14365 | No | No | No | No | No |
| django__django-11179 | Sí | Sí | Sí | Sí | Sí |
| django__django-13925 | No | No | No | No | No |
| django__django-12747 | No | No | No | No | No |
| django__django-11797 | No | No | No | No | No |
| django__django-14016 | No | No | No | No | No |
| django__django-15400 | No | No | No | No | No |
| matplotlib__matplotlib-18869 | No | No | No | No | No |
| matplotlib__matplotlib-26011 | No | No | No | No | No |
| mwaskom__seaborn-3407 | No | No | No | No | No |
| pallets__flask-5063 | No | No | No | No | No |
| psf__requests-2317 | Sí | No | No | No | No |
| pydata__xarray-4248 | No | No | No | No | No |
| pylint-dev__pylint-7080 | No | No | No | No | No |
| pytest-dev__pytest-5495 | No | No | No | No | No |
| pytest-dev__pytest-5413 | No | No | No | No | No |
| scikit-learn__scikit-learn-25638 | No | No | No | No | No |
| scikit-learn__scikit-learn-13241 | NI | NI | NI | NI | No |
| sphinx-doc__sphinx-7686 | NI | NI | NI | NI | No |
| sphinx-doc__sphinx-8713 | NI | NI | NI | NI | No |
| sympy__sympy-20212 | NI | NI | NI | NI | No |
| sympy__sympy-24066 | NI | NI | NI | NI | No |
| sympy__sympy-13146 | NI | NI | NI | NI | No |
| sympy__sympy-15011 | NI | NI | NI | NI | No |

### Checks públicos y tests reservados

| Fase / brazo | Parches aplicados por harness | Con fallos FAIL_TO_PASS | Con fallos PASS_TO_PASS | Diff sin informe |
|---|---|---|---|---|
| calibration/E | 1 | 1 | 1 | 0 |
| calibration/S | 1 | 1 | 0 | 0 |
| calibration/I2 | 0 | 0 | 0 | 0 |
| calibration/F | 2 | 2 | 0 | 0 |
| primary/E | 5 | 4 | 1 | 0 |
| primary/S | 4 | 2 | 1 | 0 |
| primary/I2 | 2 | 1 | 1 | 0 |
| primary/F | 6 | 5 | 1 | 0 |
| guard_ablation/E_no_guard | 9 | 8 | 2 | 0 |
| memory_donor/E | 0 | 0 | 0 | 0 |
| memory/empty | 0 | 0 | 0 | 0 |
| memory/shared | 0 | 0 | 0 | 0 |

Los fallos PASS_TO_PASS de esta tabla son los observados en los tests con esa
etiqueta oficial; no se atribuye causalidad a cada test sin contrastar su
baseline individual. Los checks públicos seleccionados antes del ensayo no
cubrieron todos los fallos detectados por el oráculo. Por ejemplo, E en
Seaborn-3407 pasó su admisión pública, pero el informe oficial registra 14
fallos PASS_TO_PASS y no resuelve el issue. La calibración de campaña también
terminó sin soluciones oficiales; cuatro de sus nueve episodios ejecutados
entregaron un diff no vacío.

## 4. Ablación del guardarraíl y semántica de los contadores

E_no_guard resolvió **1/24**, con 9
diffs no vacíos y 360.066 tokens. Solo los 17 issues ejecutados
también por E permiten un contraste pareado, mostrado arriba. No se interpreta
el total de 24 frente al total de 17 como un efecto del guardarraíl.

En los 68 episodios principales hubo **cero** eventos de regresión pública y
cero rechazos por ese motivo. Por tanto, la diferencia entre seis diffs de F
y cinco de E no se debe a dos regresiones vetadas por E.

La revisión de las 78 decisiones públicas de toda la campaña encontró dos
eventos etiquetados `PUBLIC_REGRESSION`. Ambos tienen `check_valid=false`,
`states={}` y `retain=false`; los 22 identificadores faltaban porque el
import falló antes de ejecutar la suite:

- E_no_guard, SymPy-20212: `NameError: name 'oo' is not defined`. El primer
  candidato no se retuvo por falta de observación válida, aunque `guard=false`.
  El segundo sí pasó el check público y se retuvo. E no ejecutó este issue.
- Receptor con memoria vacía, SymPy-20590: `TypeError: __dict__ slot disallowed`.
  La transacción no se retuvo y la entrega final fue vacía.

El contador original `regressions_blocked` cuenta una no-retención junto a
`PUBLIC_REGRESSION`; no distingue estos fallos de colección del efecto del
guard. Se conservan los contadores firmados sin modificarlos y se añade una
desagregación posterior: **cero regresiones con observación válida, cero
bloqueos atribuibles al guard entre ellas y dos rechazos por observación
inválida**. No son 44 tests efectivamente ejecutados y fallidos. La protección
común impidió retener candidatos que rompían el import, pero este contraste
no demuestra una ventaja causal del guardarraíl de E.

## 5. Memoria compartida y transferencia

| Condición | Resueltos | Tokens receptores | Tokens con adquisición | Lecciones recuperadas |
|---|---|---|---|---|
| Vacía | 0/6 | 84.941 | 84.941 | 0 |
| Compartida | 0/6 | 65.165 | 79.947 | 0 |

Los donantes pytest-5103 y SymPy-11400 terminaron con diff vacío y consumieron
7.520 y 7.262 tokens. **Cero lecciones publicadas y cero recuperadas** en los
doce receptores; todos entregaron diff vacío. El experimento ejecutó ambas
condiciones, pero no llegó a producir la intervención de transferencia que
se quería medir. La diferencia de coste no se atribuye a SharedCAM.

H2 y T20 siguen abiertos en repositorios reales. Para medir transferencia hace
falta una regla de adquisición predeclarada, donantes que produzcan evidencia
admisible, controles con/sin la misma lección y coste de adquisición completo.
No se seleccionará retrospectivamente solo a los donantes que favorezcan E.

## 6. Diagnóstico posterior: Requests-2317

S inspeccionó `Session.request`, incluida la línea 428 de `requests/sessions.py`.
Propuso decodificar `method` cuando es `bytes`, corrigió la indentación en el
segundo intento, retuvo el parche y obtuvo resolución oficial.

E pasó de localizador a editor tras leer el principio del archivo. Propuso el
mismo cambio esencial sin indentación; el diagnóstico señaló la línea 428.
Al corregir la indentación recibió `UNOBSERVED_SEARCH`, que solicitaba leer
esa línea. Sus siguientes lecturas empezaron en 156, 89, 166 y finalmente 400.
Terminó por presupuesto antes de aplicar un parche válido.

La traza sostiene un fallo de localización y uso del feedback en esta ejecución,
no una incapacidad demostrada del modelo para sintetizar ese cambio. Tampoco
prueba que eliminar la comprobación de fuente observada mejore el sistema:
eso requeriría otro contraste. Prioridad de desarrollo: traspaso ligado al
objetivo relevante y recuperación que use las coordenadas explícitas del error,
con pruebas offline y sin reabrir este examen.

## 7. Incidencias y custodia

1. El primer verify V8 tuvo un fallo intermitente de cancelación systemd. Se
   conserva; la ejecución secuencial posterior pasó 466 tests y omitió tres.
   No se afirma haber corregido esa intermitencia.
2. Hubo una caída de Wi-Fi durante el lote principal 004 y el worker original
   terminó con `relay poll failed` a los 840,005 s. La petición pendiente de
   Matplotlib-26011/E era de plantilla, con cero generaciones/tokens. Se
   recuperó con el mismo diario, request ID, reloj y presupuesto. El error
   original y los dos costes de worker se conservan.
3. Antes de la evaluación local faltaba el socket configurado de Podman. Se
   inició un servicio rootless dedicado, sin tocar candidatos ni oráculos.
4. El primer intento de evaluación falló por ausencia de las variables del
   manifiesto fijado de servicios Requests. Se restauraron apuntando a los
   mismos bytes y hash del lock. El intento fallido no produjo resultados
   oficiales; la reanudación solo evaluó entregas ya congeladas, sin GPU.

El preflight 36/36 y los controles vacío/referencia 36/36 se reatestaron para
V8 sobre evidencia previa intacta; no se presentan como 72 controles nuevos
ejecutados en esta entrega. Requests-2674 había sido excluido por control
negativo no discriminante y reemplazado por Requests-2317 antes de inferir.

La auditoría final es `valid=true`, `official_evaluation=true`, 150 registros,
35 no iniciados y `unknown_usage_episodes=0`. Comprueba las cadenas HMAC,
hashes de entregas, snapshots retenidos, contabilidad por rama, ausencia de
reservas pendientes/excesos y correspondencia con el lock. La comprobación
complementaria enlaza los hashes de los informes y logs oficiales a sus recibos.
Los archivos sin parche no tienen una ejecución de tests oficiales: su estado
`no_patch` se conserva, sin fabricar un informe de éxito o fallo del runner.

SHA-256 del manifiesto de código canónico: `6cfaebbce0ead91e112ce1ed4e0a6bddfc33f9034e0c47b740a79d2f039a8f7a`.

| Artefacto | SHA-256 de sus bytes |
|---|---|
| Contrato operativo | `df5d00abfa05516734add52c6e31a769d3342acde8d003eb28f4b7721a7c1e40` |
| SWE-RUN-LOCK | `91e0aab5dd5bc1da80f6a457af753b3efdf126c5227d0592faa6e9b70718869e` |
| Muestra | `e29a514c797a9ac79ecd23a10bfca5030c2a062291cab835d57d58f30d8f3c4b` |
| Freeze global | `7869feec11f4ee114176dddb69f4770419a93c2474dfed07af81325ab1c2bba1` |
| Auditoría final | `17e52bd1ccca02233cb59f400d84ed7bef9387188232bbe0bff13b58c54bc58d` |
| Export oficial | `9e6dc22661f3c1c96e685d2176bfb56d26fab592d50c9df972464e4ce18e6f25` |
| Resultados completos | `ab51f267d523607fdbc2b43da79a7277cec8d1faffcda337c5ea3db155197928` |

Las claves privadas no se incluyen en el paquete de resultados. La auditoría
HMAC completa se ejecuta en el almacén local de custodia; hashes y exportaciones
permiten comprobar consistencia del paquete, no sustituyen una repetición
independiente en otra máquina.

## 8. Gráficas, datos y reproducción

Las figuras son mediciones de esta campaña, no proyecciones. Las tres primeras
conservan el aviso del plotter congelado de panel incompleto. Sus 28 no iniciados son
los de la fase principal; los siete restantes corresponden a calibración.
La figura 4 se vuelve a dibujar con los mismos datos y una anotación explícita
de cero lecciones. Muestra costes de condiciones con biblioteca vacía en la
práctica y **no debe interpretarse como una curva de aprendizaje**. Las figuras
4–7 proceden del helper complementario, cuyo hash figura en el JSON completo.
La regeneración independiente local produjo los 14 PNG/PDF idénticos byte a
byte tras fijar explícitamente el DPI del renderer complementario;
[comprobación y hashes](swebench/results-v8-20261016/figure-reproduction-check.json).

| Figura | PNG | PDF | Alcance |
|---|---|---|---|
| 1. Resolución registrada | [Imagen](swebench/results-v8-20261016/figures/01_resolution.png) | [PDF](swebench/results-v8-20261016/figures/01_resolution.pdf) | Denominador 24 por brazo |
| 2. Regresiones públicas | [Imagen](swebench/results-v8-20261016/figures/02_regressions.png) | [PDF](swebench/results-v8-20261016/figures/02_regressions.pdf) | Solo principal; cero eventos |
| 3. Coste y resolución | [Imagen](swebench/results-v8-20261016/figures/03_cost_resolution.png) | [PDF](swebench/results-v8-20261016/figures/03_cost_resolution.pdf) | Promedios sobre los 24 registrados |
| 4. Condiciones de memoria | [Imagen](swebench/results-v8-20261016/figures/04_memory.png) | [PDF](swebench/results-v8-20261016/figures/04_memory.pdf) | Cero lecciones; adquisición incluida |
| 5. Cobertura por issue | [Imagen](swebench/results-v8-20261016/figures/05_coverage.png) | [PDF](swebench/results-v8-20261016/figures/05_coverage.pdf) | No iniciados visibles; incluye ablación |
| 6. Subconjunto pareado | [Imagen](swebench/results-v8-20261016/figures/06_executed_subset.png) | [PDF](swebench/results-v8-20261016/figures/06_executed_subset.pdf) | Mismos 17 issues; media por ejecutado |
| 7. Tiempo de workers | [Imagen](swebench/results-v8-20261016/figures/07_worker_time.png) | [PDF](swebench/results-v8-20261016/figures/07_worker_time.pdf) | Incluye preparación y recuperación |

Datos: [150 filas CSV](swebench/results-v8-20261016/full-results.csv),
[JSON completo](swebench/results-v8-20261016/full-results.json),
[export oficial](swebench/results-v8-20261016/analysis.json),
[auditoría](swebench/results-v8-20261016/analysis.audit.json),
[decisiones públicas desagregadas](swebench/results-v8-20261016/public-decision-audit-20261016.json) y
[diagnóstico Requests](swebench/results-v8-20261016/requests-2317-posthoc-diagnosis-20261016.json).

Desde el worktree, con los almacenes originales de custodia presentes:

```bash
RUN=ECHO-5.1/artifacts/repoworld-gates-v8-20261015
python3 ECHO-5.1/scripts/run_repoworld.py audit \
  --directory "$RUN/campaign" --sealed "$RUN/remote/sealed" \
  --sample ECHO-5.1/docs/swebench/SWE-SAMPLE.json --export "$RUN/analysis.json"
python3 scripts/plot_swebench_results.py --results "$RUN/analysis.json" \
  --contract "$RUN/remote/sealed/SWE-CONTRACT.json" \
  --sample ECHO-5.1/docs/swebench/SWE-SAMPLE.json --output "$RUN/figures"
python3 "$RUN/summarize_final.py"
python3 "$RUN/build_report.py"
```

Estos comandos auditan y representan resultados existentes; no reabren Kaggle
ni generan parches. Las filas `not_started` siguen registradas como tales.

## 9. Checklist para ECHO-5.1

- [x] Interfaz V2/V8: navegación estructural, lectura atómica, edición exacta,
  trazabilidad de fuente y límites de contexto verificados offline.
- [x] Verify V8: 466 pasadas, tres omitidas; smoke con 137 recibos,
  rollback y replay; preflight/controles 36/36 reatestados.
- [x] Calibración funcional V8, cinco gates y contrato operativo sellado.
- [x] Ejecución terminada dentro de los límites por fase; 115 episodios
  ejecutados y 35 no iniciados preservados; recuperación sin borrar el error.
- [x] Congelación global anterior al oráculo; evaluación oficial de todas las
  entregas y auditoría final válida, sin reservas huérfanas ni coste desconocido.
- [x] Ablación 24/24, dos donantes y doce receptores ejecutados; límites
  de interpretación y ausencia de transferencia efectiva documentados.
- [x] Siete gráficas PNG/PDF y exportación completa con ambos denominadores.
- [x] Regeneración local: 14/14 archivos de figuras idénticos byte a byte.
- [x] Kaggle y transporte apagados; sin push ni publicación de claves.
- [ ] Completar una campaña principal íntegra: esta ejecutó 68/96, no 96/96.
  Requiere un nuevo contrato/ensayo; no extender retroactivamente este.
- [ ] Corregir y verificar el traspaso/seguimiento de feedback sobre fixtures
  de desarrollo; mejorar cobertura pública común sin usar tests reservados.
- [ ] Aislar el efecto del guard con regresiones válidamente observadas y
  pares ejecutados; distinguir fallos de import/colección en las métricas.
- [ ] H1/H4 generales: ventaja de especialistas y del router E por confirmar.
  Este panel no demuestra superioridad de E frente a S, I2 o F.
- [ ] H2/T20: adquisición y transferencia efectiva en repositorios reales,
  con amortización y controles; aquí la biblioteca permaneció vacía.
- [ ] Cerrar las demás hipótesis/ablaciones preregistradas, repetir con
  semillas nuevas y muestras independientes, y dimensionar la potencia.
- [ ] Reproducibilidad en otra máquina y resolución de la intermitencia
  systemd; no confundir el pase posterior con una corrección de raíz.
- [ ] Release verde científico de ECHO-5.1 y transición a ECHO-5.5.
  No se crea esa etiqueta a partir de este resultado.
