# RepoWorld V8 — contexto acotado por el tokenizador real

**Cierre del 16 de octubre:** [resultados completos, imágenes y checklist](REPOWORLD-SWE-RESULTS-20261016.md).
115 episodios ejecutados y 35 no iniciados; 150 veredictos oficiales y auditoría
válida. Principal: S=2/17, I2=F=E=1/17. No se confirma la ventaja de E.
Los apartados siguientes conservan la preparación y los cortes intermedios.

V7 se detuvo durante la calibración y antes de iniciar el panel principal.
Requests-2148/E había consumido 8.763 tokens de episodio, pero el siguiente
prompt contenía 3.410 tokens, por encima del límite de entrada de 3.200.
No fue falta de presupuesto total ni un veredicto del oráculo: el ensamblador
no reducía el contexto antes de rechazar la llamada. El mismo mecanismo afectó
a prompts de Requests/S y SymPy/crítico (3.428 y 3.459 tokens).

## Corrección y límites

El proveedor prueba proyecciones deterministas progresivamente menores y
las mide mediante el template y el tokenizador fijados del worker. Solo genera
cuando el prompt cabe. Cada proyección tiene su propio ID de petición estable;
el recibo conserva los hashes de los mensajes originales y proyectados, el
nivel usado y los conteos observados. No se cobra una generación adicional
por preparar el contexto; sí se mide el tiempo que ocupa esa preparación.

Las líneas fuente se seleccionan completas, conservando sus bytes, números,
hash y procedencia. Se prioriza la última ventana leída. El texto omitido se
señala explícitamente; no se inventan resúmenes ni se modifican los archivos.
Los dos candidatos de I2 reciben el mismo límite de presentación. La política
del sistema permanece íntegra. Un contexto que aún no cabe falla cerrado,
sin reservar ni generar. El total de entrada sigue siendo 3.200, salida 768
y presupuesto de episodio 25.000: no se han ampliado para favorecer ningún brazo.

El resultado ahora distingue `ContextOverflow` y `BudgetExceeded` al detener
la generación y marca el agotamiento de llamadas como `llm_call_limit`, evitando
congelar una rama con estado `active`. Esto no convierte un parche retenido en
una solución ni sustituye el veredicto reservado.

Siete pruebas nuevas cubren bytes/indentación/Unicode de fuente, procedencia,
replay de IDs, cobro único, fallo cerrado sin generación, paridad del selector,
agotamiento de llamadas y motivo de desbordamiento. Las 18 pruebas focalizadas
pasaron. El primer verify completo detectó de nuevo la sensibilidad temporal
ya documentada en V3 de la prueba de cancelación de arranque systemd; se conserva
en `software-first-failure/`. Un pase posterior no debe interpretarse como una
corrección de esa intermitencia.

## Custodia y procedimiento

Raíz de trabajo: `ECHO-5.1/artifacts/repoworld-gates-v8-20261015/`.
`software/`, `smoke/`, `preflight/` y `official-controls/` son las compuertas
del nuevo manifiesto. Los 36 entornos y 36 pares de controles oficiales se
reatestan desde evidencia previa: no se presentan como ejecuciones nuevas.

`context-replay-input.json` conserva tres prompts de desarrollo cuyo HMAC
de origen se verificó. `remote/replay_contexts.py` debe medirlos con el tokenizador
real antes de la generación de calibración. Tanto el watcher como el helper de
sellado exigen este resultado válido. No se utiliza ningún issue primario ni
resultado oculto para ajustar el código.

V7 queda separado e inmutable: diez entregas completas, 1.498 recibos auditados,
sin reservas pendientes en esas entregas. Una undécima celda se interrumpió en
el baseline público antes de inferir; su reserva de CPU se liquidó al techo,
pero no tiene entrega final. Se conserva esa distinción en
`../repoworld-gates-v7-20261015/partial-custody-audit.json`. No se reintegran
estas celdas en una campaña bajo otro manifiesto.

El worker V7 terminó (`stopped=true`, sin errores), relay y túnel se apagaron.
Cuota consultada tras detenerlo: **20,05 h**. No se consultó el oráculo final.

## Secuencia operativa

1. Verificar suite, smoke/rollback/replay, preflight y controles; comprobar
   `check_ready.py`, `remote/operate.py check` y empaquetado offline.
2. Ejecutar `remote/run_calibration.py`: worker acotado, replay de tokenización,
   un episodio reservado SymPy-19007/E/73, apagado y auditoría funcional.
3. Solo con todas las comprobaciones válidas, `remote/seal_observed.py` crea
   el contrato operativo y lock. El contrato de diseño de `docs/` no se altera.
4. `campaign_driver.py` ejecuta lotes con reanudación y apagado entre sesiones.
   Mantiene el registro: 96 celdas principales, 24 de ablación, 16 de calibración
   y 14 de memoria. I2 sigue siendo dos propuestas independientes y selector.
5. Tras congelar las 150 celdas, evaluar con el harness, auditar y exportar
   las figuras. Hasta entonces no hay tasa de resolución ni ventaja demostrada.

## Cierre pendiente

- [x] Verify secuencial: 466 pruebas pasadas, 3 omitidas, 0 fallos. Smoke válido
  con rollback, replay idéntico y 137 recibos; preflight 36/36, controles 36/36,
  `check_ready.py`, `operate.py check` y empaquetado offline válidos.
- [x] Replay real: 3.428→3.031, 3.410→3.016 y 3.459→3.030 tokens,
  política y bytes fuente preservados, cero generaciones.
- [x] Calibración funcional y apagado auditados: las 11 comprobaciones pasan.
- [ ] Sello vigente y campaña completa congelada.
- [ ] Evaluación oficial, métricas, figuras y comparación por pares.
- [ ] Decisión de release sustentada en resultados; ECHO-5.5 sigue condicionado.

Los resultados observados de esta secuencia se incorporarán aquí. No se declara
ECHO-5.1 en verde por el mero funcionamiento de su infraestructura.

## Resultado remoto V8 y sello

SymPy-19007/E/73: `_entry` (235–247) observado completo antes del traspaso,
17.916 tokens disponibles al entrar el editor, dos modificaciones aplicadas
entre seis intentos, cinco ejecuciones de checks, 16 llamadas y 24.830 tokens.
El episodio termina `budget_stopped` con diff no vacío retenido y checks
públicos pasados. Auditoría válida: 263 recibos, `destroyed=0`, sin reservas
pendientes. Diff SHA-256:
`0e0066fd907a2484ffc01f395acbac33d81d5e953459ad03526104afe3e49256`.
Es el mismo diff retenido en V6/V7; **no es una demostración de mejora en
resolución**. Los tests públicos de `test_basic.py` no acreditan cobertura
funcional de BlockMatrix. No se ha consultado el oráculo oficial.

Kernel `rogeernavarro/echo51-repoworld-context-v8-20261015`: COMPLETE,
65/65 capas, preparación 401,740 s, tiempo total 812,218 s. Worker detenido,
sin errores, relay/túnel apagados. Cuota observada: 20,05→**19,82 h**.

Contrato operativo: `remote/sealed/SWE-CONTRACT.json`, `status=sealed`,
`launch_enabled=true`. Lock `remote/sealed/SWE-RUN-LOCK.json`, SHA-256:
`91e0aab5dd5bc1da80f6a457af753b3efdf126c5227d0592faa6e9b70718869e`.
El sello liga los cinco gates y el manifiesto de código de `209285d`.
La campaña arranca mediante `python3
ECHO-5.1/artifacts/repoworld-gates-v8-20261015/campaign_driver.py`.
Sus lotes paran entre episodios, conservan presupuesto al reanudar y verifican
el apagado antes de iniciar otro worker. El resultado científico sigue pendiente
hasta completar congelación, evaluación oficial y auditoría.

## Avance de campaña · 16 de octubre de 2026

La fase principal terminó bajo el límite registrado con **68/96 entregas**:
17 issues completos en cada uno de S/I2/F/E. Las 28 celdas restantes (siete
issues por brazo) quedaron `not_started`. El contador de ventanas suma
5,503846 horas: antes de abrir otro episodio se exige reservar sus 1.800 s
máximos, por lo que no cabía otro dentro del tope de seis horas. No fue
agotamiento de la cuota de Kaggle: quedaban **12,73 h** tras detener el quinto
lote. No se amplió el contrato durante la medición. La selección restante por
orden de ejecución limita la representatividad; 17 issues ejecutados no son
el panel completo de 24 ni las 300 instancias de SWE-bench Lite.

La calibración de campaña produjo nueve entregas y siete `not_started` por su
propio límite. En este punto hay 77 entregas y 35 celdas no iniciadas; faltan
los 24 episodios de ablación y los 14 de memoria. Ningún score reservado se ha
consultado. Ablación, memoria, congelación global y evaluación siguen pendientes.

Durante el cuarto lote primario, NetworkManager registró una desconexión de
Wi-Fi y el túnel perdió conectividad. El worker terminó en `ERROR`, con
`RuntimeError: relay poll failed`; la petición pendiente era `/apply-template`
de Matplotlib-26011/E, todavía no entregada al worker. En esa celda había cero
generaciones y cero tokens. Se autenticó y reutilizó el mismo diario, credencial
e identificador, sin reiniciar el reloj ni el presupuesto del episodio. La
recuperación completó la celda y otras 19; terminó `COMPLETE`, `stopped=true`,
sin errores del nuevo worker. El fallo original no se sobrescribió ni se
reclasificó como una ejecución limpia.

Evidencia operativa dentro de la raíz V8:

- `campaign-remotes/primary/batch-004/kaggle-output/gpu-proposer-results.json`:
  error original y 840,005 s de ejecución.
- `campaign-remotes/primary/batch-004/recovery-001/recovery-plan.json`:
  identidad del request y hashes del diario antes de recuperar.
- `campaign-remotes/primary/batch-004/batch-complete.json`:
  recuperación y apagado, con ambas ejecuciones contabilizadas.
- `campaign-remotes/primary/batch-005/batch-complete.json`:
  cierre de la fase principal, conteos y cuota observada.

Las estimaciones iniciales de duración fueron optimistas. Preparación del
modelo, validación de recibos, pruebas locales y recuperación de red también
consumen tiempo. No hay todavía evidencia para declarar una ventaja ni el
cierre verde de ECHO-5.1.

### Lectura estructural del panel ejecutado, antes del oráculo

Se verificaron los recibos y el hash de cada entrega contra el diario de campaña
sin abrir el oráculo. El cálculo reproducible queda en
`primary-structural-review-20261016.json` dentro de la raíz V8. Este conteo no
sustituye la auditoría final de snapshots y resultados oficiales.

| Brazo | Issues ejecutados | Tokens totales | Media por issue | Entregas con diff no vacío | Candidatos staged distintos | Regresiones públicas / bloqueadas |
|---|---:|---:|---:|---:|---:|---:|
| S | 17 | 404.724 | 23.807,29 | 4 | 7 | 0 / 0 |
| I2 | 17 | 343.469 | 20.204,06 | 2 | 3 | 0 / 0 |
| F | 17 | 266.806 | 15.694,47 | 6 | 11 | 0 / 0 |
| E | 17 | 266.562 | 15.680,12 | 5 | 9 | 0 / 0 |

F consume 34,08 % menos tokens que S y E 34,14 % menos. No se debe traducir
esta diferencia directamente a ahorro de GPU, energía ni coste por issue
resuelto. Los ocho `finished` de F y los nueve de E entregaron **diff vacío**;
la etiqueta incluye abandono y no acredita trabajo resuelto ni consenso de
corrección. S terminó `budget_stopped` en 17/17, pero consumió entre 22.147 y
25.000 tokens: no todos agotaron exactamente el techo. En 15 el motivo registrado
es falta de espacio para la siguiente generación dentro de la asignación
restante (`ContextOverflow`); no debe confundirse con un prompt emitido por
encima de 3.200 tokens.

No hubo regresiones públicas observadas ni rollbacks por regresión en estos
68 episodios. El guardarraíl también está activo en S/I2/F; solo E_no_guard lo
desactiva. Por tanto, la diferencia entre seis diffs finales de F y cinco de E
no se puede atribuir a dos vetos del guardarraíl. Los tests de implementación
de ese mecanismo no son evidencia de que se haya activado en esta campaña.

Son 17 unidades pareadas de comparación, con varias procedentes del mismo
repositorio, no 68 problemas independientes. El tamaño no garantiza
significancia; hacen falta los resultados por pares y sus incertidumbres. El
corte de las últimas siete instancias reduce cobertura y representatividad.
El rango de resolución 15–25 % sugerido para otros sistemas no se adopta como
pronóstico de este modelo cuantizado con contexto 4.096 y estas herramientas.

Conclusión intermedia: menor consumo y más entregas con diff no vacío para
F/E frente a S en esta configuración. **No hay aún superioridad demostrada,
resolución certificada ni prevención de regresiones observada en el panel.**

### Corte intermedio: ablación terminada; transferencia en curso

E_no_guard completó 24/24 episodios: 360.066 tokens, nueve entregas con diff
no vacío; 13 `finished`, nueve `budget_stopped`, un `critic_exhausted` y un
`repair_exhausted`. Se autenticaron los recibos y hashes de entrega en
`guard-structural-review-20261016.json`. La auditoría completa y el oráculo
siguen siendo pasos posteriores.

El recibo de SymPy-20212 contiene `PUBLIC_REGRESSION` con `guard=false`.
La revisión posterior de su ejecución aclara que el parche causó un
`NameError` durante el import, sin completar los tests. `after.valid=false`
impidió retenerlo incluso con el guard desactivado; un segundo parche sí pasó
los checks públicos y fue retenido. No es un rollback atribuible al guard.
E no ejecutó ese issue por el límite de la fase principal. Tampoco constituye
una pareja experimental que demuestre un daño evitado por E.
Solo 17 de las 24 instancias de la ablación tienen contraparte E ejecutada;
las otras siete se informarán aparte. En esas 17 parejas no hubo regresiones
públicas observadas en ninguno de los dos brazos.

El panel principal ejecutado abarca diez repositorios y seis de sus 17 issues
son de Django. SymPy y Sphinx no llegaron a ejecutarse en esa fase. El corte
conserva la paridad entre brazos, pero no la cobertura íntegra del muestreo
estratificado original. El saldo registrado tras detener la ablación es
11,09 h de GPU. Quedan los dos donantes y doce receptores de memoria antes
de congelar globalmente y abrir el evaluador oficial.

## Cierre de ejecución y evaluación · 16 de octubre

La memoria terminó con dos donantes y doce receptores; todos entregaron diff
vacío. No se publicaron ni recuperaron lecciones. Después se congelaron las
150 celdas: 115 ejecutadas, 28 principales no iniciadas y siete de calibración
no iniciadas. El curador emitió los 150 veredictos y la auditoría pasó con
18.546 registros/recibos, 99 fuentes conservadas y cero costes desconocidos.

Resultado principal: S=2/17; I2=F=E=1/17. S resolvió Django-11179 y
Requests-2317; los otros tres, solo Django-11179. E_no_guard obtuvo 1/24 y
empató con E en las 17 parejas ejecutadas. Calibración y memoria no resolvieron
issues. No se declara ventaja causal del router, del guard ni de SharedCAM.

La revisión completa de las 78 decisiones públicas distingue dos fallos de
import/colección (`PUBLIC_REGRESSION` con observación inválida) de regresiones
observadas en tests completos: estas últimas fueron cero. Uno de esos rechazos
fue SymPy-20212/E_no_guard; el otro, SymPy-20590 con memoria vacía. La
comprobación común de validez impidió su retención. Los contadores originales
se conservan y la desagregación está en el informe final.

La evaluación local requirió iniciar el socket dedicado de Podman y restaurar
las variables del manifiesto Requests ya fijado por el lock. Se conserva el
intento fallido; no hubo cambios de candidatos, tests ni entorno declarado,
ni se reabrió inferencia. El informe final incluye siete imágenes PNG/PDF,
CSV/JSON de las 150 filas y un regenerador de figuras sin GPU.

Última consulta de Kaggle: 9,95 h restantes, workers terminales y relay cerrado.
ECHO-5.1 sigue abierto para confirmación científica y reproducibilidad externa;
no se etiqueta un release verde ni se inicia ECHO-5.5 a partir de estos datos.
