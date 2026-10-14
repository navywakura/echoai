# ECHO-5.1 · checklist de desarrollo

Actualización: 13 de octubre de 2026. El verde se aplica al alcance comprobado
de cada fila; no equivale a una ventaja científica ni al cierre de ECHO-5.1.

| Estado | Entrega | Evidencia y límite |
|---|---|---|
| Verde | Frontera de ejecución Linux compartida | Bubblewrap/cgroup v2; sin fallback. NEXUS-0 y sus invariantes conservados. |
| Verde acotado | T08: entorno del piloto independiente | Rootfs Python íntegro y exportable; sin montar `/usr` host. No empaqueta kernel ni hardware. Las rutas legacy conservan su etiqueta no hermética. |
| Verde acotado | T10: caché persistente de propiedades puras | Identidad de candidato, resultado, dominio, política, runtime y checker; reinicio, invalidación y testigos comprobados. Todo código candidato vuelve a ejecutarse. |
| Verde | Proveedor local real | Qwen2.5-Coder-7B-Instruct Q4_K_M, revisión/hash fijados, llama.cpp CPU. Preflight exacto y esquemas públicos. El 4B no interviene. |
| Verde | Contabilidad | 25k tokens por tarea/brazo; reservas antes de llamadas; errores e inconsistencias no son gratis. CPU del LLM separada de la del candidato. |
| Verde acotado | Crítico → contraejemplo → memoria → reparación → verificación | Un diagnóstico real sobre `sum_positive`: 1/1, 1.704 tokens, 51 recibos auditados. El defecto inicial es sembrado. |
| Verde | Corpus nuevo de reparación | Seis familias distintas de las cuatro fixtures: intervalos, registros, rutas, CSV, paginación y dependencias. Bugs inducidos comprobados; no benchmark externo. |
| Verde de ejecución; ventaja no demostrada | Comparación S/I2/F/E `repair-v2` | 48/48 episodios, auditoría válida de 2.049 recibos. S=4/12, I2=4/12, F=2/12, E=2/12. E no supera a F (10 empates, 2 pérdidas frente a S); produjo más contraejemplos que F, pero no más reparaciones aceptadas. 250.444 tokens totales. |
| Verde | Software y revisión | 255 tests PCWorld tras memoria persistente, transferencia A→B y orquestación del ensayo 32B con comprobación de identidad/carga; 59 regresiones seleccionadas en una tanda anterior. Revisión completada antes de lanzar. |
| Verde de ejecución; empate | Piloto 14B con dos puertas | 12/12 episodios y 580 recibos auditados. Todos 2/3. E=20.372 tokens; F=22.378; S=5.212; I2=2.352. Cuota de críticas agotada en Registros E/F; evaluación final no ejecutada allí. |
| Verde de ejecución; ventaja limitada al piloto | Piloto 14B con evaluación común | 12/12 episodios, 619 recibos auditados y auditoría repetida válida. E=F=3/3 frente a S=I2=2/3. Registros pasa tras crítica y reparación en E/F; ambos completan dos categorías. E=16.174 tokens, F=16.049; no hay ventaja de E frente a F. Tres tareas conocidas, no confirmación independiente. |
| Verde de implementación | Cobertura informativa y graduación del candidato | Criterio final común a los cuatro brazos, sin cambiar oráculos; agotamiento de críticas no implica corrección. Pruebas positivas y negativas del candidato graduado; no se reserva una séptima crítica. En 0.6 no se necesitó; en 0.7 F Rutas01 se graduó con una categoría y pasó 4/4. F CSV01 se graduó pero fue rechazado. |
| Verde de ejecución; resultado parcial | Cinco categorías y seis familias, protocolo 0.7 | 48/48 episodios, 2.362 recibos auditados. E=F=8/12 frente a S=I2=6/12. Ambos ganan en Registros; CSV y Dependencias siguen fallando. E gasta 54.310 tokens frente a 66.993 de F; un error de presupuesto de herramientas en CSV01 F. Sin timeouts. |
| Verde de implementación | Memoria de críticas rechazadas y auditoría del catálogo | E recupera observaciones y fallos en una sola consulta cobrada; avanza de categoría tras tres rechazos. La auditoría comprueba orden, reintentos, etiquetas, novedad y vínculo con propuesta o replay. El orden F se fija por semilla, sin colocarlo deliberadamente en desventaja. |
| Pendiente | Superioridad o ahorro atribuibles a ECHO | En 0.10 con 32B, S=F=E=E_shared=12/12 e I2=10/12. E usa 4,09% menos tokens que F, pero 6,74% más herramientas; S resuelve lo mismo con 53,09% menos tokens que E. La memoria ahorra 5,94% en receptores, pero cuesta 46,22% más incluyendo adquisición. No se cierran H1/H2/H4 generales. |
| Verde de implementación | Reparación con testigos y rechazo de regresiones | Feedback explícito con esquema de I/O y stderr observado, dos intentos, restauración transaccional del candidato retenido; E congela el crítico durante la reparación y lo reabre tras un parche comprobado para completar dos categorías. Pruebas de software; no implica ventaja del modelo. |
| Negativo en desarrollo | Microensayo local de reparación r1 | Registros y Rutas: 0/2 reparaciones, 0/2 pases finales, sin timeout; 140 recibos auditados. r2 también 0/2, con 154 recibos válidos. |
| Parcial; cerrado el diagnóstico | Microensayo 14B en Kaggle | GPU 49/49 capas, 1/2 tareas completas. Registros 5/5 a la primera; Rutas 4/5 tras el segundo intento, rechazada por un caso final. Auditorías locales válidas. No demuestra ventaja S/I2/F/E. |
| Verde acotado | Reparación desde contrato y error observado | Registros pasa tras dos propuestas del 7B; Rutas falla. 1/2, 108 recibos auditados. Testigos suministrados, sin mérito de descubrimiento del crítico. |
| Parcial | Crítica adversarial y reparación | E retuvo 6 contraejemplos válidos frente a 2 de F, pero la aceptación fue 2/12 para ambos; siete episodios agotaron el plazo del proveedor (F=5, E=2). Hubo respuestas de categoría incorrecta y duplicados (F=11/6; E=1/3), sin entradas fuera de dominio. Hace falta mejorar la conversión de refutaciones en reparación y repetir en una muestra nueva. |
| Verde acotado con 32B | Sondeos y resolución de CSV | En 0.10, 2/2 en los cinco brazos. El candidato E de CSV00 usa csv.reader. El fracaso 0.8 con 14B se conserva: E/F/S 0/2 pese a sondeos refutatorios. No se demuestra ventaja específica de E. |
| Verde acotado con 32B | Sondeos y resolución de grafos | En 0.10, 2/2 en los cinco brazos. E/F/S reparan; los dos receptores con receta pasan sin reparar. El resultado 0.8 E=F=0/2 con 14B sigue siendo histórico; no se modificaron los oráculos. |
| Pendiente | Semántica de categoría heredada | `disconnected-lex-order` exige un nodo aislado en su detector, pero la guía no lo explicita. Alinear definición y guía antes de atribuir ahorro al router; sin recalificar episodios ya congelados. |
| Pendiente | Ablaciones de memoria, crítico y control basal | Mismo modelo, herramientas y presupuesto; aislar qué mecanismo aporta una mejora. |
| Pendiente | Ampliación y confirmación independiente | Más tareas/familias y repeticiones, dimensionar muestra, fijar contrato y reservar casos nuevos. No reciclar este desarrollo como examen ciego. |
| Parcial; recetas transferidas | T20: conceptos reutilizables | En 0.10 se publican dos recetas con AST/procedencia y cuatro receptores compatibles pasan sin reparar. Código idéntico en Registros y mismo AST en Dependencias, dentro del mismo contrato. Faltan abstracción, adaptación, promoción/cuarentena integrada y transferencia a familias nuevas. |
| Parcial; ahorro marginal | H2: memoria compartida | 0.10: E_shared=E=12/12, reparaciones 0 frente a 4; 40.254 frente a 42.795 tokens. Incluyendo los seis donantes, 62.573 tokens y coste mayor. No hay ventaja de acierto ni amortización demostrada; faltan controles fuertes y confirmación independiente. |
| Verde de ejecución; empate con control único | Escalado 32B y memoria, protocolo 0.10 | 255 tests, 66 episodios, dos auditorías válidas y 32 fuentes intactas. 65/65 capas en ambas T4; S=F=E=E_shared=12/12, I2=10/12. Kaggle COMPLETE y servicios de cómputo apagados; 22,94 h GPU restantes. [Resultados y checklist](SCALING32-RESULTS-20261013.md). No cierra ECHO-5.1. |
| Pendiente | Release experimental reproducible en otra máquina | Probar instalación y restauración fuera de este host, publicar artefactos sin claves privadas y definir alcance de release. |
| Aplazado | S6 | No se reabre; queda para después de ECHO-5.5. |
| Verde de infraestructura local | RepoWorld: datos, entorno y herramientas | Proyección pública estricta, perfil Bubblewrap con scratch acotado, snapshots por streaming, navegación paginada y parches stage/retain/CAS. 35 tests RepoWorld + 255 PCWorld + 13 de diseño. [Entrega local](REPOWORLD-LOCAL-CALIBRATION-20261013.md). |
| Verde acotado | Calibración local RepoWorld | Cuatro commits reales (Flask/Requests/pytest/SymPy), 28 sondas, cuatro transacciones y 56 recibos auditados; cero LLM/GPU. Rootfs stdlib: no se ejecutaron suites completas ni se resolvieron los issues. |
| Pendiente | RepoWorld / campaña SWE-bench Lite | Dependencias, checks públicos y sondas del crítico, proveedor/brazos, memoria, presupuesto persistente, evaluador sellado y preflight/lock. Contrato `design`, lanzamiento deshabilitado; no cierra H1–H4. |

Detalles: [piloto local](LOCAL-PILOT-20261013.md),
[T01–T20](ACCEPTANCE.md), [verificación](PHASE2-VERIFICATION.json) y
[ejecución reproducible](RUNBOOK.md), [protocolo adversarial](ADVERSARIAL-ROUTING-20261013.md)
y [resultados adversariales](ADVERSARIAL-ROUTING-RESULTS-20261013.md).

El estimador `--dry-run` ya cuenta los brazos y familias seleccionados y el
plazo explícito de episodio. Detalle de la remediación: [brecha de reparación](REPAIR-GAP-20261013.md).

Resultados de remediación: [informe de reparación](REPAIR-GAP-RESULTS-20261013.md).

La reparación funciona en los casos de desarrollo descritos; su transferencia y ventaja específica siguen abiertas. Los diagnósticos locales y Kaggle terminaron; no se publicó ni se hizo push a GitHub.

Piloto anterior, protocolo 0.5: [dos puertas](TWO-GATE-RESULTS-20261013.md).
S=I2=F=E=2/3 y 580 recibos válidos. Se conserva esa puntuación histórica.

Piloto anterior, protocolo 0.6: [evaluación común](GRADUATION-RESULTS-20261013.md).
E=F=3/3, S=I2=2/3; 619 recibos válidos. Registros reparado y evaluado;
sin errores de episodio ni timeouts. 202 tests pasan. ECHO-5.1 sigue abierto
para confirmación independiente. Quedaron 25,33 h GPU al terminar ese piloto.

Piloto anterior, protocolo 0.7: [discriminación de categorías](CATEGORY-DISCRIMINATION-RESULTS-20261013.md).
E=F=8/12, S=I2=6/12; 214 tests y 2.362 recibos válidos. Duración del worker:
37 min 13 s; consumo de cuota aproximado 0,62 h. GPU, supervisor, broker y
túnel apagados; 24,71 h GPU restantes. ECHO-5.1 continúa abierto para las
hipótesis científicas. No se relanzó, publicó ni hizo push.

Piloto anterior, protocolo 0.8: [sondeos CSV/grafos y checklist completo](PROBE-CONTENT-RESULTS-20261013.md).
E=F=8/12, S=I2=6/12. 219 tests, 48 episodios y 2.445 recibos válidos; auditoría
repetida y 27 hashes conservados. 132.287 tokens; ningún error de episodio ni
timeout. Worker 33 min 09 s; cuota total aproximada 0,59 h incluyendo corrección
del empaquetado inicial. Kaggle COMPLETE, supervisor/broker/túnel apagados;
24,12 h GPU restantes. Sin push ni publicación. H1/H4 y T20 siguen abiertos.
El informe enlazado reúne qué está comprobado y cada obligación pendiente.

Piloto anterior, protocolo 0.9: [co-learning A→B y checklist](COLEARNING-RESULTS-20261013.md).
240 tests, siete episodios ejecutados, auditoría repetida válida sobre 347 recibos
de episodios y custodia del estudio/bibliotecas. Treinta fuentes congeladas intactas.
Receptores: compartido 3/3 sin reparación; aislado 1/3 con una reparación.
Dos controles fallan por copiar `format.content`; no se atribuye toda la diferencia
al aprendizaje de duplicados. 21.021 tokens totales y 0,14 h GPU aproximadas.
Kaggle COMPLETE y servicios de cómputo apagados; 23,98 h GPU restantes.
Recuperación persistente implementada, H2/T20 generales todavía parciales. Sin push.

Último piloto, protocolo 0.10: [32B y memoria compartida](SCALING32-RESULTS-20261013.md).
S=F=E=E_shared=12/12, I2=10/12; 66 episodios y 255 tests. Auditoría repetida
válida, 32 fuentes congeladas intactas, 179.731 tokens totales. La memoria evita
cuatro reparaciones y ahorra 5,94% de tokens en receptores; incluyendo adquisición
cuesta 46,22% más que E sin memoria. S alcanza el mismo acierto con menos coste.
Worker 61 min 51 s; consumo aproximado 1,04 h GPU, 22,94 h restantes. Kaggle COMPLETE,
servicios de cómputo apagados; sin push ni publicación. H1–H4 y T20 generales abiertos.

Siguiente ensayo diseñado: [RepoWorld / SWE-bench Lite](SWE-BENCH-LITE-DESIGN-20261013.md)
y [plan de implementación](SWE-BENCH-LITE-PLAN-20261013.md). El contrato está en
estado `design`, con lanzamiento deshabilitado. Los 24 issues y sus commits
están fijados. La [calibración local de infraestructura](REPOWORLD-LOCAL-CALIBRATION-20261013.md)
ya pasó en los cuatro casos de desarrollo. La continuación implementa checks,
roles, contabilidad persistente, relay con IDs duraderos, curador y CLI:
[ejecución y compuertas](REPOWORLD-EXECUTION-20261013.md).

| Estado RepoWorld | Obligación | Evidencia / pendiente |
|---|---|---|
| Verde local acotado | Parche → regresión → retención/rollback → auditoría | Smoke sobre tests reales de SymPy con proveedor simulado; recuperación sin nueva generación. No resuelve el issue. |
| Verde local acotado | S/I2/F/E/E_no_guard, contabilidad y recuperación | Pruebas de ramas, reservas, respuesta tardía, cambio de lock, entorno ajeno, agotamientos y firma de entregas. Calibración real pendiente. |
| Verde local acotado | Gate 1: entorno por instancia | 36/36 instancias, 12/12 repos, dos ejecuciones públicas coincidentes; dependencias y suplementos BASE fijados. Una omisión Python 2 declarada, no contada como pase. [Evidencia Opción B](REPOWORLD-ENVIRONMENTS-COMPLETE-20261013.md). |
| Verde local: 36/36 | Control del evaluador oficial | Repetición completa tras sustitución preregistrada de Requests-2674 por 2317. Vacío negativo y referencia positiva en las 36; firmas y hashes válidos. Gate 3 remoto todavía pendiente. |
| Pendiente | Gate 3 y lock científico | Sin calibración nueva de 32B, consulta nueva de cuota ni `SWE-RUN-LOCK` habilitado. |
| Pendiente | Campaña SWE, evaluación común y cuatro gráficas medidas | Conservar 24 issues por brazo; principal 96, más controles y memoria: 150 celdas registradas. |
| Abierto | H1/H2/H3/H4/T20 y cierre general de ECHO-5.1 | Infraestructura verificada no demuestra ventaja científica; faltan resultados y confirmación independiente. |

No hay puntuación SWE-bench ni gasto nuevo de GPU. Rama local, sin push.

### Actualización local de entornos · 14 de octubre de 2026

- [x] Gate 1: 36/36 instancias públicas, sin reducir el registro.
- [x] Gate 2: smoke con rollback y replay; 68 recibos auditados.
- [x] Cuatro controles oficiales de calibración, incluidos Requests y Pytest.
- [x] 415 pruebas de software pasadas y dos integraciones explícitas pasadas aparte.
- [x] Revisión independiente; corrección del reemplazo de alias nativos probada en sandbox.
- [x] Sin nuevas llamadas LLM/GPU; contrato en `design`; sin push.
- [x] Controles oficiales de las 36 instancias del registro enmendado (véase actualización final).
- [ ] Calibración remota, revisión de cuota real y sellado.
- [ ] Campaña científica, evaluación separada y confirmación de hipótesis.

La infraestructura local en verde no cierra científicamente ECHO-5.1.


### Curador · punto histórico previo a la sustitución (14 de octubre de 2026)

Este bloque conserva el estado 35/36 anterior; la actualización final de abajo lo supera.

- [x] Preflight repetido 36/36 y smoke autenticado bajo las fuentes actuales.
- [x] 419 pruebas de software pasadas; dos integraciones reales pasadas aparte.
- [x] Alias `calibrate-remote` y procedimiento de relay/parada preparados.
- [x] Evidencia archivada, hashes y autenticación comprobados tras la interrupción.
- [x] Las 36 instancias comprobadas; almacenamiento, Matplotlib y Seaborn recuperados.
- [x] Auditoría de firmas y logs válida; fuentes del ejecutor sin cambios.
- [x] Cuatro pruebas adicionales de recuperación administrativa pasadas.
- [x] Calibración remota rechazada antes del LLM por el gate inválido.
- [ ] `official-controls` 36/36: **35 válidos**, Requests-2674 sigue bloqueado;
  sus F2P pasan también con parche vacío. No se han cambiado el registro ni el oráculo.
- [ ] Gate 3: no ejecutar hasta resolver y verificar los controles completos.

[Informe y recuperación](REPOWORLD-CURATOR-ALL-20261014.md). Cero nuevas llamadas
LLM/GPU. No hay puntuación SWE-bench ni cierre científico de ECHO-5.1.

### Curador · cierre local tras sustitución preregistrada (14 de octubre de 2026)

- [x] Requests-2674 excluido por control negativo no discriminante, con evidencia conservada.
- [x] Política registrada antes de probar candidatos; 2317 fue el primero y resultó elegible.
- [x] Un cambio de fila primaria; otros 35 registros y todos los oráculos intactos.
- [x] Registro v2, muestra y hash del contrato actualizados; contrato sigue en `design`.
- [x] Preflight público repetido: **36/36** baselines válidos.
- [x] `official-controls` repetido: **36/36**, 72 logs vacío/referencia auditados.
- [x] **420 pruebas pasadas** y **tres integraciones reales pasadas aparte**.
- [x] Smoke, rollback, replay, autenticación y hashes verificados bajo las fuentes finales.
- [x] Revisión independiente sin hallazgos accionables.
- [x] Comprobación offline llega al proveedor de Gate 3, interceptado sin conexión.
- [x] 0 GPU y 0 llamadas reales al LLM; entrega local sin push.
- [ ] Gate 3 remoto, cuota actual y parada confirmada del worker.
- [ ] Lock científico sellado y campaña; evaluación oficial independiente.
- [ ] H1/H2/H3/H4/T20 generales y cierre científico de ECHO-5.1.

[Informe final](REPOWORLD-CURATOR-ALL-20261014.md) y
[enmienda de Requests](swebench/REQUESTS-REPLACEMENT-20261014.md).

## Calibración remota del 14 de octubre

- [x] Gate remoto técnico: 65/65 capas, 17 llamadas, 15.698 tokens,
  251 recibos auditados; Kaggle COMPLETE y parada confirmada.
- [x] Contrato y run-lock sellados en los artefactos del intento 2.
- [ ] Resultado útil en la calibración: el agente agotó ocho intentos de
  parche y entregó diff vacío. No hay resolución oficial demostrada.
- [ ] Campaña primaria (96), controles adicionales y evaluación oficial.
- [ ] Confirmación de H1–H4 y cierre científico de ECHO-5.1.

Cuota observada al terminar: 22,62 h. No quedan workers GPU activos de esta
entrega. [Informe y hashes](REPOWORLD-REMOTE-RESULTS-20261014.md).

## Remediación de usabilidad posterior a `12dec48`

- [x] Reinicio de cursores auténticos incompatibles, con recibo; firmas
  falsificadas y snapshots no autorizados siguen rechazados.
- [x] Feedback acotado de mismatch con línea real, línea propuesta y EOF.
- [x] Dos lecturas de rescate contabilizadas tras error de formato/contexto,
  sin renovar ilimitadamente búsquedas tras parches fallidos.
- [x] Mock de recuperación: feedback, lecturas, límite y parche corregido.
- [x] Suite local: 423 pasados, 3 integraciones opcionales omitidas, cero fallos.
- [ ] Renovar gates y sellado para estas fuentes antes de otra campaña.
- [ ] Medir con el modelo real si mejora la calibración; sin GPU en esta entrega.

Detalle: [usabilidad y alcance](REPOWORLD-USABILITY-20261014.md).

## Gates v2 renovados — 14 de octubre

- [x] Verify actualizado: 423 pasados, 3 opcionales omitidos, cero fallos.
- [x] Nuevo smoke con rescate, regresión bloqueada y replay; 173 recibos válidos.
- [x] Nuevo preflight de 36/36 instancias y 12 repositorios.
- [x] Enlace auditado de 36/36 controles oficiales históricos, sin reejecución;
  origen y 72 logs verificados, curador sin cambios.
- [x] Cuatro gates válidos para las fuentes actuales; recorrido de calibración
  comprobado offline hasta el constructor del proveedor.
- [x] Configuración/claves y comando remoto preparados; 0 GPU y 0 llamadas LLM.
- [ ] Calibración remota v2, nuevo sellado y campaña.

[Rutas, comandos y hashes](REPOWORLD-GATES-V2-20261014.md).

## Calibración v2 en T4: alcance medido

- [x] Gate técnico remoto válido: 65/65 capas, 21 llamadas, 21.980 tokens.
- [x] Auditoría válida: 304 recibos, cero reservas pendientes.
- [x] Un reinicio de cursor y ocho lecturas de rescate efectivas.
- [x] Kaggle COMPLETE y procesos propios detenidos; 22,37 h restantes.
- [ ] Resultado útil: ocho diffs rechazados por contexto; entrega vacía.
- [ ] Nuevo sellado/campaña y evaluación oficial: no realizados.

La calibración técnica no cierra ECHO-5.1. [Resultado y diagnóstico](REPOWORLD-REMOTE-V2-RESULTS-20261014.md).
