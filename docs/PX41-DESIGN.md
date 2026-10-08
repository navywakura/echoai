# PX4-1 — contrato prospectivo v1

2026-09-17. Pregunta: ¿el enlace entrega exclusivamente objetivos acotados
y conserva la autoridad de los controladores y failsafes de PX4?

Se reutiliza PX4 v1.15.4/Gazebo y el driver congelado de PATTERN/COMPOSE.
No se modifica el controlador, motores, estimador ni los hitos anteriores.
Sin LLM, hardware, segundo bus cognitivo ni escrituras CAM. WSP sigue siendo
16 bytes. Los metadatos de secuencia/tiempo son del transporte, no pensamientos.

## Dominio y entradas

Subset explícito de CAUSE: WSP canónico norte/sur un metro o mantener,
altura 2.5 m, velocidad solicitada 1 m/s, recinto local ENU ±5 m.
Entradas: WSP, secuencia creciente por sesión, fecha de publicación y
odometría/estado PX4 recibidos por el adaptador. Nunca pose verdadera.
La sesión sólo se inicia tras comprobaciones del operador de laboratorio;
el agente no tiene órdenes de armado, motores, parámetros ni modos.
Un único objetivo en vuelo. ACK aceptado no equivale a llegada. Se exige
posición a ≤350 mm y velocidad ≤150 mm/s en tres muestras distintas,
posteriores al ACK. Caducidad 250 ms; ACK ≤2 s; ejecución ≤15 s.
Rechazo PX4, timeout o pérdida de autoridad enclavan el enlace hasta una
nueva sesión supervisada; no reintentos ni recuperación automática.
No se promete autenticación criptográfica: IDs MAVLink no son una firma.

## Manipulación y controles

Cada semilla ejecuta dos vuelos: `nominal` y `link_loss`. Ambos ejecutan
un objetivo legal y prueban antes entradas malformadas, caducadas, repetidas,
fuera de recinto, sin autoridad y durante una transacción. Ninguna debe
llegar al transmisor. El baseline funcional sin gate acepta esos intentos;
no se ejecuta ese baseline peligroso en vuelo.
En `nominal`, aterrizaje explícito normal. En `link_loss`, tras confirmar
el objetivo se interrumpen los heartbeats GCS: COM_DL_LOSS_T=5 y
NAV_DLL_ACT=3 (Land), verificados por lectura. Se conserva COM_FAIL_ACT_T.
PX4 debe aterrizar/desarmarse solo en ≤35 s: no NAV_LAND externo después
del corte y evidencia ULog de pérdida GCS, failsafe y AUTO_LAND.
No se simula una desconexión total de telemetría: corte de heartbeats de
supervisión, con observador pasivo. SAFE-1 cubrirá fallos integrados amplios.

## Banco fijado antes del código

Desarrollo: 20262801, 20262802. B: 20262901, 20262902.
C: 20263001, 20263002. Dos condiciones por semilla: 4 vuelos por etapa,
12 en total. Sentido norte en semillas impares, sur en pares; semilla
Gazebo = semilla*10 + índice de condición. Pilotos explícitos separados.
Se congela código, parámetros, diseño, tests y dependencias antes de B;
B rojo impide abrir C. Este C no es el C sellado de TRANSFER-3.

Verde: todos los vuelos auditables y correctos, todas las entradas ilegales
bloqueadas, cero órdenes de motor/actitud/control crudo o force-arm/disarm,
cero setpoints fuera de recinto, cero bypass de failsafe y ninguna llegada
certificada sólo por ACK. Se informa n/N y Wilson 95%; una muestra pequeña
no estima fiabilidad de producción. No se reclama superioridad de navegación.
Posición real privada sólo evalúa: desvío al objetivo ≤500 mm; altura
durante objetivo 1.8–3.2 m; velocidad ≤3 m/s.

Mutantes obligatorios: sin TTL, sin recinto, sin autoridad, ACK como llegada,
sin identidad ACK, sin exclusión de transacciones. Manipulaciones de evidencia:
WSP, objetivo, ACK, ULog y reporte deben invalidar la auditoría.
Artefactos: lab/px41/{development,validation,confirmation}, lock.json,
JSONL de decisiones/telemetría, ULog, hashes SHA256 y
lab/echo3_px41_report.json. Auditar desde fuentes en un proceso nuevo.
No marcar cerrado si falta ejecución física o reconstrucción de evidencia.
