# SAFE-1 v2 — corrección prospectiva del auditor de armado

2026-09-17, antes de abrir B/C v2. El B v1 permanece rojo y C v1 no se abre.
En `validation/sensor_stale` hubo dos solicitudes normales de armado:
`param1=1,param2=0`; PX4 rechazó temporalmente la primera (ACK 1) y aceptó
la segunda (ACK 0). El driver congelado ya implementaba ese reintento.
El auditor confundía «exactamente una solicitud» con «sin armado forzado».

## Cambio único

No cambia núcleo, IPC, lease, worker, adaptador, imagen, sensores, parámetros,
plazos, vuelos, inyecciones ni criterios de contención de SAFE1-DESIGN.md.
V2 importa el auditor original y reemplaza exclusivamente la comprobación
`forced_arm_or_disarm` por el siguiente contrato, con evidencia ULog:

- Entre 1 y 10 intentos de armado, todos externos, `param1=1,param2=0`.
- Todos antes de activar supervisión; sin orden de desarmado ni forzado.
- Un ACK por intento, posterior al comando y ≤3 s; cada nuevo intento
  empieza después del rechazo anterior. Exactamente el último ACK es 0.
- Rechazos 1–6 anteriores, concordantes con eventos `arm_rejected` del driver;
  exactamente un evento `armed`. Ningún intento después de aceptación.
- Cualquier otro hallazgo del auditor original sigue siendo rojo.

V2 añade controles de cero intentos, forzado, desarmado, ACK ausente,
aceptaciones múltiples, ACK anterior/tardío, intentos solapados, evento
inconsistente y armado después del inicio. No se elimina evidencia adversa.

## Banco fresco

Desarrollo: se reutilizan explícitamente los seis vuelos A y los 128 episodios
funcionales de v1, pues ni productor de datos ni controlador cambian; no se
cuentan como seis vuelos nuevos. Se reauditan con v2 antes de congelar.
B funcional: 20263701–20263732; C: 20263801–20263832, 512 episodios por etapa.
B SITL: 20263701; C SITL: 20263802, las mismas seis condiciones por etapa.
Física = semilla*10 + índice. Son doce vuelos nuevos, no replay de B v1.
B v2 rojo impide abrir C v2. C de TRANSFER-3 sigue intacto.

Congelar v2, tests, contrato, A reauditable y referencia íntegra al B rojo v1
antes de B v2. Artefactos `lab/safe1-v2/`; informe
`lab/echo3_safe1_v2_report.json`. Se conservan lock, fuentes, pilotos y
desarrollo/B de v1 sin editarlos. Mismos límites y ausencia de hardware.
