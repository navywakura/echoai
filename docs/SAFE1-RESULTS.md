# SAFE-1 — contención de fallos

2026-09-17. **V1 rojo en B; C no abierto.** Véase el
[contrato v2](SAFE1-V2-DESIGN.md) para la corrección limitada del auditor.

Desarrollo definitivo: 128/128 episodios funcionales y 6/6 vuelos válidos.
97 tests, seis mutantes y cuatro corrupciones detectados antes de congelar.
Lock: `63fe14b6449e93b698196e13f576f120fc1f5f2faf0ca1b1e74c2a78d6230c2f`.

B v1: 512/512 episodios funcionales y 5/6 vuelos válidos según su auditor
congelado. En `sensor_stale`, dos solicitudes normales de armado (sin
forzado) recibieron ACK 1 y después ACK 0. El auditor exigía exactamente
una solicitud y marcó `forced_arm_or_disarm`. La contención de ese caso
dio veto en 165 ms y desarmado nativo en 20.927 ms, pero **no se cambia el
resultado rojo de v1** ni se abre su C. V2 usa doce vuelos reservados nuevos.

## Implementación

`nexus0/safe1/` importa sin modificar Gateway de PX4-1 y Guard de POWER-1.
Supervisa salud, frescura, autoridad, proceso y propuesta; un veto enclava
la sesión y retira los heartbeats. No hay reinicio ni reanudación automática.
El permiso de heartbeat caduca a los 500 ms si el hilo supervisor deja de
renovarlo. IPC tiene deadline absoluto de 200 ms y máximo de 4096 bytes.

Las esperas de ACK del operador durante arranque y aterrizaje normal no
bloquean ese hilo: una operación auxiliar espera el ACK con plazo propio,
pero sólo el hilo principal puede renovar el permiso. El emisor de heartbeats
no se autorrenueva. PX4 conserva controladores, armado y failsafes.

## Desarrollo conservado

- `pilot/nominal-1`: el sandbox impidió iniciar Podman; no hubo vuelo.
- `pilot/nominal-2`: piloto nominal, llegada con error verdadero de 160 mm.
- `pilot/hang-1`: piloto con hijo detenido, veto en 200 ms y desarmado por
  failsafe PX4 en 19.793 ms, sin reposicionamiento ni NAV_LAND externo.
- `development-attempt-1`: 128/128 episodios funcionales y 5/6 sesiones
  SITL válidas. Rojo conservado: la espera síncrona de armado agotó el lease
  de heartbeat antes de activar el supervisor en `sensor_stale`.
  Se corrigió la espera, no el umbral, ni los failsafes ni los criterios.
  Los seis vuelos de desarrollo se repiten; ninguno sustituye selectivamente
  una observación roja de B/C. Las fuentes del intento anterior se conservan
  dentro de cada sesión; corresponden al adaptador anterior a la corrección.

## Alcance

Fallos inyectados antes del primer objetivo, desde hover estable; una única
transacción norte/sur de un metro. Sensor/red se congelan en la vista del
adaptador; la observación privada sigue viva. No es un cable físico retirado.
Los procesos terminan o quedan detenidos realmente, y las propuestas pasan
por el IPC real. El ensayo no cubre un proceso hostil con privilegios, sensores
erróneos pero plausibles, rotura de motores, caída de PX4/host ni obstáculos.

POWER usa un presupuesto explícito `sim_u`. No mide batería ni julios.
El banco funcional repite una matriz finita con posiciones/acciones distintas;
sus intervalos descriptivos no prueban fiabilidad frente a fallos desconocidos.
Sin LLM, hardware, nuevas CAM/Q/T ni consumo del C sellado de TRANSFER-3.
No constituye el cierre de DRONE-3 ni certificación de seguridad física.

## Reproducción

Desde `echoai/`, con las dependencias y la imagen local fijadas:

```bash
PYTHONPATH=.. python3 -m unittest echoai.tests.test_safe1
PYTHONPATH=.. python3 -m echoai.nexus0.safe1.evaluate lab/safe1/validation/sensor_stale
```

El segundo comando reproduce el rojo v1; no hay certificado v1 ni C consumido.
La auditoría del certificado sucesor usa `echoai.nexus0.safe1_v2.bench audit`.
Ninguno de estos comandos vuelve a volar ni modifica certificados anteriores.
