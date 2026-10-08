# PX4-1 — implementación y evidencia

2026-09-17. **Verde en su alcance SITL**, con auditoría repetida en proceso
nuevo, exit 0. [Contrato prospectivo](PX41-DESIGN.md).

## Resultado reservado

| Etapa | Vuelos válidos | Entradas inválidas bloqueadas | Failsafes autónomos | Error físico máximo |
|---|---:|---:|---:|---:|
| B | 4/4 | 24/24 | 2/2 | 172 mm |
| C | 4/4 | 24/24 | 2/2 | 354 mm |

Los ocho objetivos legales llegaron con evidencia posterior al ACK. Cero
setpoints ilegales enviados, bypass de gate o de failsafe observados.
Desarme tras corte GCS: B 23.221/20.118 s; C 19.822/20.128 s, todos dentro
del límite preregistrado de 35 s. No hubo NAV_LAND externo en esos vuelos.
Wilson 95% para 4/4 por etapa: **[0.5101, 1]**; muestra deliberadamente
pequeña, sin pretensión de certificar fiabilidad general.

El control funcional sin gate (`accept_all`) acepta 48/48 intentos inválidos
de las trazas reservadas; el enlace completo, 0/48. Ese control peligroso
no se ejecuta en el vehículo. Además de las cuatro corrupciones de traza,
la auditoría rechaza un informe con numerador alterado y hash recalculado.

Certificado:
`342ca3aa9380b8f4e03201c24df3b67a4a2b36593d9c8a27bf375d8747ce79b9`.
Informe: `lab/echo3_px41_report.json`; recibo independiente:
`lab/px41/audit-receipt.json`. Total de campaña: 12 vuelos, más dos pilotos
fuera del denominador. B y C se ejecutaron sin cambios tras congelar.

## Implementación

`nexus0/px41/core.py` implementa un gate entero de transporte para los WSP
canónicos de CAUSE: norte/sur un metro o mantener. Comprueba formato,
antigüedad, secuencia, odometría, recinto y autoridad; admite una transacción
por sesión supervisada. No expone armado, modos, motores ni parámetros.
`assets/runner.py` traduce el objetivo aprobado a `MAV_CMD_DO_REPOSITION`,
sin modificar PX4, y espera ACK identificado y tres observaciones distintas
de llegada. Rechazo, timeout, pérdida de autoridad o salida de recinto
enclavan la sesión. No hay reintentos automáticos.

El arnés de laboratorio configura el despegue y el failsafe antes del vuelo;
no son privilegios del agente. La configuración `COM_DL_LOSS_T=5`,
`NAV_DLL_ACT=3` se verifica mediante lectura y ULog. El corte de heartbeats
se observa pasivamente: PX4 debe decidir aterrizar, sin NAV_LAND externo.
La semántica se comprobó en el código del contenedor PX4 v1.15.4 y en su
[documentación de failsafes](https://docs.px4.io/v1.15/en/config/safety#data-link-loss-failsafe).

## Desarrollo y controles

Desarrollo: 4/4 vuelos válidos. Errores físicos de llegada 96, 178, 133 y
139 mm. Desarme tras corte de heartbeats: 20.078 y 20.642 s.
48 tests seleccionados aprobados (20 nuevos, CAUSE y gate/banco NEXUS).
Regresión ampliada: 521 tests, exit 0, con un fallo esperado preexistente.
El primer intento de esa regresión encontró ocho errores de sockets locales
prohibidos por el sandbox; la repetición autorizada los resolvió sin cambios
de código. Recibo: `lab/px41/regression-receipt.json`.
Seis mutantes de código detectados: TTL, recinto, autoridad, ACK como
llegada, identidad ACK y exclusión de transacciones. Cuatro manipulaciones
de evidencia rechazadas: WSP, objetivo, ACK y ULog.

Lock: `8bcdc1981d454843afc9ea56a176fa478f87602cae4e81bd4f68636a3449c395`.
Conservados aparte dos vuelos piloto y el intento inicial impedido por los
permisos del contenedor. No entran en los denominadores reservados.

## Alcance y límites

Es una prueba de enlace acotado en SITL, no un controlador nuevo ni una
misión integrada de navegación. Las intenciones del banco son experimentales;
la posición real no genera objetivos y sólo se utiliza para evaluación.
El recinto es local, vacío, plano y a altura fija; no sustituye una geocerca
certificada ni verifica evasión de obstáculos. Mantener está cubierto en
tests funcionales; los vuelos reservados ejercitan norte y sur.

El fallo físico ensayado es pérdida de heartbeats GCS, no pérdida total de
telemetría ni todos los fallos de SAFE-1. Una nueva sesión requiere supervisión;
los IDs MAVLink no son autenticación criptográfica. La integración permanente
con COMPOSE/CAUSE, hardware, HIL y jaula no quedan certificados aquí.
El banco pequeño informa evidencia observada, no fiabilidad de producción.
Sin LLM, segundo bus, nuevas escrituras CAM o hardware Akida.

Se preservan los 305 archivos del inventario congelado de CAUSE-1. Su
auditor antiguo expande dinámicamente el inventario a todo `nexus0`: añadir
otro hito cambia ese conjunto, aunque no cambie ninguno de sus archivos.
PX4-1 comprueba las entradas guardadas y sus hashes, sin reescribir aquel
lock ni certificado.

## Reproducción

Desde `echoai/`, con la imagen local congelada y permisos para Podman:

```bash
PYTHONPATH=.. python3 -m unittest echoai.tests.test_px41 -v
PYTHONPATH=.. python3 -m echoai.nexus0.px41.audit
```

La secuencia original fue `development`, `freeze`, `accept`, `audit`.
No se sobrescriben vuelos, lock ni informe existentes. B rojo impide abrir C;
el C usado aquí no consume el C sellado de TRANSFER-3.

El comando original `bench audit` crea el recibo con apertura exclusiva:
la primera auditoría pasó, pero repetirlo da `FileExistsError` al intentar
guardar el mismo recibo, después de verificar. La entrada `px41.audit`,
añadida después del certificado, es sólo lectura y llama a `verify_report`
del auditor congelado. No modifica criterios, código congelado ni evidencia.
