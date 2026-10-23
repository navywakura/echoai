# PERCIBE-X r1 Implementation Plan

> Ejecución inline, sin subagentes ni commits, autorizada el 23 de octubre.

**Goal:** aprender familias LiDAR en vivo y usarlas en MEMORIA-X para decidir
una inspección yaw ejecutada por PX4 y verificada en Gazebo.

**Architecture:** adaptadores nuevos en `echo58/percibex/`, fuentes antiguas
importadas y zipapps reproducibles. El socket existente transporta sensores y
WSP16 de control/acción; la jaula nunca ve mundo, pose ni etiquetas privadas.

**Tech Stack:** Python3 del sistema/stdlib, bubblewrap, imágenes Podman locales,
Gazebo Harmonic/PX4 1.15.4 ya disponibles.

**Spec:** `ECHO-5.8/docs/PERCIBEX-DESIGN-20261023.md`.

## Restricciones globales

Sin LLM/API/Akida; sin echo-discord; sin edición de nexus0 ni exámenes viejos;
sin publicaciones; sin segundo bus; máximo tres dev del candidato r1; seis
validaciones congeladas sin reemplazos. Un vuelo PX4 a la vez en esta tarea.

## Review focus

* Orden de freeze frente a frames ya en cola: inventariar orden real y reconstruirlo.
* Recibo forjado/tardío: sólo aceptarlo para la inspección pendiente correspondiente.
* L2 de MEMX: ambas claves deben derivar de familia, sin contaminación entre ellas.
* Identidad desconocida/ambigua: abstenerse, no fabricar una familia válida.
* Falla de yaw/retorno o bridge: conservar NOOP y cerrar el resultado rojo.

## Implementación previa a medida

- [x] Núcleo online y protocolo WSP16: pruebas que fallen para aprendizaje antes
  de EOF, freeze inmutable, claves por familia y rechazo de recibos sin pendiente;
  implementar `Online` y `control()` en `online.py` y `protocol.py`.
- [x] Empaquetado y adaptadores: `bundle.py`, `consumer.py`, `flight.py` y
  `session.py` importan originales. Igualdad de bytes y respuesta antes de EOF
  probadas en proceso nuevo con stream de protocolo; aún sin prueba de vuelo.
- [x] Campaña implementada: `campaign.py` guarda configuración e inventario,
  prepara recuperación sin sobrescribir parciales y limita intentos/recursos.
  El primer intento interrumpido y los dos pendientes suman el máximo de tres.
- [x] Evaluador implementado: `audit.py` reconstruye Ground/PATTERN/Memory y
  acciones desde muestras privadas y bridge; mapa del juez con escuela y
  medidas relativas de yaw. Su aplicación a un vuelo nuevo está pendiente.
- [x] Controles adversos y exportación implementados: mutaciones de copias en
  memoria, escritura/recarga .wsp y auditor en proceso nuevo. Las pruebas de
  interfaz y regresión pasan; la ejecución sobre nuevos vuelos está pendiente.
- [x] Recuperación operativa implementada y probada con mocks: límites,
  etiquetas y limpieza por propiedad; el coordinador hizo un no-op real sin
  operaciones en su recibo previo. Eso no acredita una intervención física.
- [x] Contrato, plan y recibos previos incluidos como fuentes obligatorias del
  inventario. Una prueba modifica sólo una fixture después de `prepare` y
  comprueba que `source_checks` la invalida.

## Medida y cierre pendientes al congelar este plan

- [ ] Comprobar stream real en jaula bajo los límites nuevos y preflight del
  vuelo cuando el coordinador asigne turno; no usarlo como prueba de vuelo.
- [ ] Ejecutar los dos desarrollos declarados de recuperación y evaluar sus
  resultados antes de abrir seis validaciones nuevas con las puertas fijadas.
- [ ] Ejecutar validación MEMX/EMPTY/VISITS condicionada a desarrollo válido,
  sin reemplazos ni ampliación oportunista de la muestra.
- [ ] Aplicar los controles adversos a los transcripts nuevos y comprobar las
  exportaciones .wsp generadas por esos vuelos.
- [ ] Ejecutar auditoría offline en proceso nuevo y conservar rojos/errores.
- [ ] Escribir RESULTS con cifras por vuelo/componente, comparación de controles,
  huellas y límites. No editar roadmap/handoff global.

Este checklist declara el estado anterior a medida. Después de que `prepare`
lo incluya en `source_inventory`, DESIGN y PLAN quedan sin ediciones. Los
resultados posteriores y el cierre del checklist se registran sólo en RESULTS.

Comandos previstos:

```sh
PYTHONPATH=.. python3 -m unittest tests.test_echo58_percibex -v
PYTHONPATH=.. python3 -m echoai.echo58.percibex.campaign recover-dev
PYTHONPATH=.. python3 -m echoai.echo58.percibex.campaign validate
PYTHONPATH=.. python3 -m echoai.echo58.percibex.audit
```

Artefactos exclusivos: `lab/echo58/percibex/20261023-r1/`.

Recuperación posterior a reinicio: la adenda del diseño conserva el primer
intento sin resultado. Dos vuelos de recuperación completan los tres intentos
de desarrollo permitidos. No lanzar hasta el turno asignado tras C y E; usar
unidad del supervisor con límites efectivos y wrappers por contenedor/jaula.
El actor se corrigió antes de medir para giro respecto al heading basal en
ambos marcos y límite superior 0,52 rad; fuentes del aprendiz conservadas.
Pruebas rápidas actuales: 23 nuevas; los mocks sólo verifican protocolo/logging
y limpieza por propiedad. `cleanup_owned_containers(reason)` comparte la
limpieza de etiqueta exacta con el watcher del coordinador. Un timeout se
limpia antes del collect heredado; una limpieza incierta aborta la etapa.
