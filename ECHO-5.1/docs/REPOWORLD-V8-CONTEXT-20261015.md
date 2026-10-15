# RepoWorld V8 — contexto acotado por el tokenizador real

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
