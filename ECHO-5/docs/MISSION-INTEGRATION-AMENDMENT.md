# Enmienda de desarrollo: razonamiento conectado y aterrizaje de referencia

10 de octubre de 2026. Enmienda implementada, con pruebas y desarrollo software
auditados. Se conserva abajo el diseño y su estado en el momento de la entrega.
La calibración posterior y la corrección del instrumento se documentan en
[SITL-INSTRUMENTATION-R3.md](SITL-INSTRUMENTATION-R3.md). La confirmación robótica
sigue pendiente.

## Motivo y alcance

La revisión 1 acepta un plan externo, pero `run_benchmark` y `agent-worker`
no lo pasan: `mission.py:243,255,262,418` y `scripts/run_sitl.py:55–57` de su
snapshot. Sus resultados acreditan el adaptador y el controlador heredado,
no una conexión activa con razonamiento nuevo. La versión 2 hace esa conexión
normal mediante una subclase local de MissionAgent y el planificador ECHO-5.

Los originales están conservados en `../base/` dentro del paquete de borrador,
y el manifiesto registra los hashes previos a la edición. Ninguna fuente
activa, dataset, runner histórico o artefacto r1 fue reescrito. Antes de aplicar
hay que cotejar hashes; si el padre cambió un archivo, integrar el diff sin
sobrescribir sus cambios. Los documentos y contratos v1 del run r1 conservan
su procedencia. R1 debe auditarse con su snapshot de fuentes, no con v2.

La revisión se limita a la conexión, sus recibos/auditoría, presupuesto,
regresiones y separación de semillas. No modifica la estabilización ni cambia
condiciones o denominadores para hacer pasar resultados negativos.

## Negativo real r1 y diagnóstico

`artifacts/sitl-development-20261010-r1/0000-one_step/process-receipt.json`:
exit=1, error del lanzador nulo, resultado del protocolo
`TimeoutError('disarm')`, mission_end=`agent_stop`, teardown=true,
OOMKilled=false. `out/result.json` registra LAND aceptado (result=0), seguido
por repetidos `Landing detected`/`Takeoff detected`. La traza registra
`land_request` a 188375000000 ns. El runner esperó 35 segundos simulados sin
observar desarmado. Findings: process_exit, ulog_armed_then_landed,
observed_disarm. No hubo colisión ni violación de reserva, pero eso no acredita
aterrizaje seguro conforme al contrato.

El padre observó verdad Gazebo estable sobre el suelo, mientras `landed` y la
estimación vertical oscilaban. No debe describirse como un rebote físico sin
evidencia. En la fuente local PX4, el detector usa velocidad/derivada vertical,
empuje y movimiento; Commander exige estado landed sostenido antes del
autodesarmado. `EKF2_BARO_NOISE` se eleva al cuadrado como varianza de medida.
Esto sostiene una hipótesis de estimación/detección, no identifica por sí solo
qué parámetro causó la oscilación. El checkout local tiene identidad `0fb3847`;
no está demostrado idéntico al binario de la imagen v1.15.4.

Fuentes locales examinadas:
- `src/modules/ekf2/params_barometer.yaml`: BARO_NOISE default 3.5 m, mínimo .01.
- `src/modules/ekf2/module.yaml`: HGT_REF 0=baro, 1=GPS, default 1.
- `src/modules/ekf2/EKF/aid_sources/barometer/baro_height_control.cpp:62`:
  varianza = cuadrado del ruido configurado.
- `src/modules/land_detector/MulticopterLandDetector.cpp:178,184,271,314`:
  condiciones de movimiento/contacto/estado landed.
- `src/modules/commander/Commander.cpp:2477`: histéresis de autodesarmado.

La fuente oficial v1.15 aportada por el padre coincide para los parámetros:
https://docs.px4.io/v1.15/en/advanced_config/parameter_reference#EKF2_HGT_REF
https://docs.px4.io/v1.15/en/advanced_config/parameter_reference#EKF2_BARO_NOISE
El `.01` del ruido de presión SDF no tiene las mismas unidades que `.01` m del
EKF; la igualdad numérica no demuestra calibración correcta o incorrecta.

## Decisión de calibración

No incluir una corrección causal no demostrada en el cambio de razonamiento.
Conservar `EKF2_HGT_REF=0`, `EKF2_BARO_NOISE=.01` en este paquete. Conservar el
negativo de r1; ningún gate, timeout de aterrizaje, reserva o criterio ULog se
relaja. No usar force_disarm, ni verdad privada como entrada del actor.

Ensayo de calibración propuesto, separado y anterior a confirmación: cambiar
sólo `EKF2_BARO_NOISE` a 3.5, con nuevo contrato/manifest y lectura de retorno
antes de armar; mismo valor para los tres modos, misma imagen, generación y
resto de parámetros. Mantener HGT_REF=0 para aislar una variable. Para atribuir
el efecto al parámetro, conservar también la revisión del actor y del runner
al comparar; no mezclar simultáneamente la revisión del razonador y afirmar
causalidad barométrica. Elegir el orden de esta fase antes de medirla.

Criterios: LAND aceptado, landed/desarmado observado dentro del plazo existente,
ULog real, verdad y estimación registradas por el juez, cero colisiones y
violaciones de reserva. Si falla, conservar la fila negativa y diagnosticar;
no buscar valores sobre semillas de confirmación. Un único éxito no demuestra
robustez: hacen falta repeticiones predeclaradas en desarrollo y cobertura
completa antes de confirmación.

## Validación de este paquete

Sólo análisis estático: parseo/compilación sin ejecutar, JSON y manifiestos,
revisión de enlaces de actor/worker/auditor, diff y hashes. No se han importado
los módulos del borrador para ejecutar decisiones, ni corrido unittest,
benchmarks, SITL o confirmación. La lista exacta de archivos y resultados
estáticos está en `manifest.json` en la raíz del paquete.
