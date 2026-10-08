# SAFE-1 — contrato prospectivo v1

2026-09-17. Pregunta: ¿fallos de sensores, transporte, proceso y propuestas
quedan contenidos antes de producir nuevas órdenes, conservando PX4 autoridad?

## Arquitectura y dominio

Supervisor entero que importa Gateway de PX4-1 y Guard de POWER-1, sin
modificarlos. WSP 16 B sigue siendo el único pensamiento/acción. La salud,
secuencias y plazos son metadatos de transporte, no un bus cognitivo nuevo.
Sin LLM, nuevas CAM/Q/T, force-arm/disarm, motores directos ni hardware.
Una transacción de movimiento de 1 m norte/sur, altura 2.5 m, recinto ±5 m.
Intención experimental de un proceso auxiliar: no navegación autónoma nueva.

Salud: LiDAR entregado y fechado ≤250 ms; odometría y autoridad PX4 según
Gateway; proceso vivo. Propuesta canónica, fresca, secuenciada, compatible
con la decisión POWER. Rechazo implica enclavamiento, incluso si vuelven
sensores/proceso/datos buenos. No se reinicia el proceso ni la misión.
ACK no equivale a llegada; se hereda la confirmación de Gateway.
El presupuesto POWER de este banco es `sim_u`, no batería física estimada.

IPC limitado a 4096 bytes, una petición pendiente y deadline total 200 ms
para escritura y lectura, incluyendo líneas parciales, EOF y proceso detenido.
Permiso de heartbeat mediante lease de reloj monótono de 500 ms. Un emisor
separado no renueva ese permiso: si se bloquea el supervisor, el permiso
caduca. Ningún fallo permite que un heartbeat incondicional oculte la caída.
Las esperas de ACK de despegue/armado/aterrizaje del operador se ejecutan
fuera del hilo principal con plazos propios acotados. Sólo el hilo principal
renueva el lease; ni el emisor ni el hilo que espera ACK pueden renovarlo.
Esto no se usa para mantener permiso de misión sin salud válida.

## Banco prospectivo

Funcional: 16 condiciones — nominal, sensor ausente/caducado/futuro,
telemetría caducada, proceso muerto, timeout, WSP malformado, propuesta
caducada, recinto, failsafe PX4 activo, energía desconocida/insuficiente,
replay, ACK rechazado y ACK ausente. Desarrollo 20263401–20263408;
B 20263501–20263532; C 20263601–20263632. 128/512/512 episodios.
Control sin supervisor sólo funcional; nunca se envían sus órdenes inseguras.
Se prueban además procesos reales con respuesta sana, EOF, SIGSTOP, línea
parcial, respuesta demasiado larga y secuencia incorrecta.

SITL: seis condiciones por etapa: nominal, `sensor_stale`, `network_stale`,
`process_exit`, `process_hang`, `bad_proposal`. Desarrollo semilla 20263401;
B 20263501; C 20263602. Semilla Gazebo = semilla*10 + índice de condición.
18 vuelos, más pilotos explícitamente fuera del denominador si hacen falta.
Sensor/red: filtro en el adaptador congela el dato que llega al supervisor;
el observador privado sigue recibiendo para auditar. No se afirma desconexión
física del sensor o del cable. El proceso auxiliar realmente termina o se
detiene; las propuestas inválidas vienen del canal IPC. Fallo antes del
primer objetivo, tras hover estable y una observación sana.

## Criterios

Funcional: todas las condiciones correctas, cero permisos después de fallo,
cero recuperaciones automáticas; nominal puede completar. Cada prueba de
IPC debe terminar por su deadline y cerrar el hijo sin dejar procesos.
Lease no renovada se extingue a los 500 ms; no puede revivir tras caducar.

SITL nominal: un reposicionamiento aceptado, confirmación de llegada y
aterrizaje normal. Con fallo: detección y veto ≤750 ms desde la inyección
(reloj monótono y simulado), cero reposicionamientos, heartbeat retirado,
sin NAV_LAND externo; PX4 debe mostrar pérdida GCS, failsafe y AUTO_LAND en
ULog, y desarmarse ≤35 s desde el veto. COM_DL_LOSS_T=5, NAV_DLL_ACT=3,
lectura verificada; sin desactivar controladores ni otros failsafes.
En los vuelos: no fuerza sobre cuerpo ni escritura de pose; envolvente
horizontal ≤2 m desde origen verdadero y altura ≤3.2 m después de hover.
Todos los vuelos y episodios previstos son obligatorios: un rojo impide verde.
Wilson 95% descriptivo por proporción; no inferir fiabilidad de producción.

Congelar código, tests, parámetros, diseño, desarrollo y dependencias antes
de B. Si B falla, no abrir C. Este C no consume el sellado de TRANSFER-3.
Mutantes: sin caducidad sensorial, sin salud de enlace/proceso, sin veto
POWER, sin enclavamiento, heartbeat incondicional. Manipulaciones: salud,
WSP/permiso, ULog, resultado y numeradores/hashes del informe.
Auditor reconstruye decisiones, fuente de cada comando y evidencia nativa;
informe `lab/echo3_safe1_report.json`, trazas/lock en `lab/safe1/`.

## Lo que no demuestra

No cubre sensores erróneos pero plausibles, avería de motores, fallo del
kernel/host/controlador PX4, radio real, entorno con obstáculos o batería
instrumentada. No certifica seguridad universal ni integración DRONE-3.
Una retirada de permiso no confirma por sí sola un aterrizaje: se exige
la evidencia ULog indicada. Los certificados anteriores se preservan.
