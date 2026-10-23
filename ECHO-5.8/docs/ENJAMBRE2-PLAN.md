# C v2 · plan de implementación y desarrollo

> Ejecutar con superpowers:executing-plans: implementación directa, TDD,
> una revisión independiente del conjunto antes de congelar el desarrollo.

**Objetivo:** ejecutar las 48 condiciones de desarrollo del contrato aprobado,
con recibos auditables y examen cerrado, sin LLM.
**Arquitectura:** importar mundos, agente físico y memoria originales de C v1;
extender solo transporte autenticado, lectura global y confianza. Nuevo harness
separado, sin monkeypatch del banco congelado ni nuevas mecánicas del mundo.
**Tecnología:** Python del sistema y stdlib; procesos independientes por trabajo.
**Spec:** `ENJAMBRE2-DESIGN.md`.

## Límites

No editar C v1/LINK-3, núcleo, W ni CRECE. WSP16, enteros, destroyed=0.
Solo semillas de desarrollo 12_101_000…12_103_007 e idiomas declarados.
No se implementa un comando de examen. No LLM, API, instalaciones o publicación.
La aprobación de Nav cubre implementar y medir el diseño, sin otro menú
de confirmación para decisiones rutinarias de implementación.

## Archivos e interfaces

- `echo58/enjambre2/transport.py`: `decode(raw,author=None)`, `Board.post`,
  `Attacker.transform(cards,round)`; validar antes de modificar el tablón,
  guardar original/enviado y último mensaje por autor/clave.
- `memory.py`: `Trust`, `Private` que aprende confianza de consecuencias,
  `Reader` con precedencia here/private/notes/global y resoluciones por brazo.
  El snapshot de testimonios dura una ronda y no ve publicaciones futuras.
- `bench.py`: `mission(m)`, `jobs()`, `run_team(arm,attack,m)`, congelación,
  ejecución de 48 trabajos, recepción exclusiva, observaciones por ronda.
- `verify.py`: comprobar hashes, agenda exacta, postales/ataques, exposición,
  contabilidad de episodios/rondas/confianza y agregados desde recibos.
- `report.py`: resumen descriptivo por ataque/brazo y límites; sin puerta
  estadística ni verde científico de examen sobre tres macros de desarrollo.
- `tests/test_echo58_enjambre2.py`: fixtures sintéticas de transporte,
  aprendizaje, prioridad, ataques y auditoría/alteración; sin jugar exámenes.

## Tareas

1. [ ] Escribir pruebas de validación/auth, reenvío, tres ataques y extracción
   de IDs. Verlas rojas; implementar transport; suite verde.
2. [ ] Pruebas de votos, cuatro riesgos, agrupación de autores nuevos,
   confianza local/una vez/snapshot, rehabilitación y precedencia privada.
   Verlas rojas; implementar memory; suite verde. No confianza para RM.
3. [ ] Pruebas de agenda48, semillas, equivalencia del lector honesto con C v1
   sobre fixtures, custodia exclusiva y auditor que rechaza alteraciones.
   Verlas rojas; harness/report/verificador; suite verde.
4. [ ] Revisión independiente del código completo y contrato. Resolver defectos
   con regresiones RED→GREEN. Integrar archivos nuevos byte a byte, sin sustituir
   código congelado; congelar fuentes/dependencias/contrato/agenda antes de jugar.
5. [ ] Ejecutar los48 trabajos una vez, máximo4 procesos; recibos JSON por trabajo
   y observaciones reales por ronda. Conservar errores, sin repetir condiciones
   automáticamente ni cambiar reglas según sus resultados.
6. [ ] Auditar sin volver a jugar. Informe de desarrollo con exposición real por
   ataque, comparación de cinco brazos con honesto por macro, daño/progreso y
   resultados por tipo. Congelar cierre sin continuación a examen; actualizar
   roadmap y entregarlo a Nav con la recomendación siguiente.

## Decisiones operativas anteriores a medir

- Se reutiliza el worktree aislado nativo de W, con fuentes C v1 importadas
  como dependencias byte-idénticas. Los archivos de W no se alteran.
- El harness conserva asignación, relevo,30rondas y300pasos del original.
  Solo observa el estado público y los testimonios, sin elegir por verdad oculta.
- Observación: receipts por ronda, publicaciones original/enviada, consultas
  globales realmente alcanzadas y contrastes de confianza. Se guardan conteos
  de consultas repetidas para acotar espacio; no se inventa monólogo ni se
  inyectan los recibos en la política.
- El registro de confianza se mantiene en todos los brazos como observación
  pasiva; solo `prudente` lo usa para decidir. Nunca cambia memoria vivida.
- La exposición cuenta únicamente consultas que alcanzan el nivel global
  después de fallar la precedencia privada/notas. Consultas respondidas localmente
  no se usan como prueba de exposición a un mensaje malicioso.

## Verificación

`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<RXos> python3 -m unittest
echoai.tests.test_echo58_enjambre2` y controles de regresión de las dependencias
importadas. No un discovery global que pueda lanzar campañas/exámenes ajenos.
Logs RED→GREEN y hashes se conservan antes de la medición real.
