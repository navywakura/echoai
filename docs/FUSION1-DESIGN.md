# FUSION-1 — evidencia por fuente, predicado y tiempo

Diseño previo a implementación y aceptación, 2026-09-14. Autorización de Roger:
implementar FUSION-1 y, sólo tras su verde, continuar COMPOSE-1.

## Pregunta y alcance

¿Puede una memoria acotada conservar fuentes discordantes, caducar su autoridad
y emitir DESCONOCIDO sobre el predicado discutido sin detener todos los casos
con evidencia concordante? Implementación entera opt-in; NEXUS-0 permanece
congelado. No se amplían neuronas. No LLM, hardware ni segundo bus.

Primera instancia física: profundidad de cámara y LiDAR, colocados en la misma
montura SENSOR-1S, sobre presencia de barrera en el sector frontal a 2 m.
No se llama espacio navegable a un rayo libre: no certifica la envolvente del
vehículo. RGB no constituye una segunda fuente independiente de su cámara.
`visible` y `barrera` son predicados distintos. Ausencia de retorno no es libre.

## Representación

El adaptador entrega WSP de 16 bytes y un extracto sensorial referenciado. Un
registro externo acotado conserva esos bytes, fuente, captura, llegada, región,
época del marco, validez y hash del extracto. Es memoria de procedencia, no un
canal de propuestas. No recibe mapas, nombres de sala, IDs privados ni planes.

WSP: dominio 8, generador 7, `style` identifica predicado, `slot` región,
`seq` época local del marco; src=YO, time=AHORA. Para barrera: OBSERVAR/ALLI
(presente), OBSERVAR/FUERA (ausente), DESCONOCIDO/DESCONOCIDO (sin concluir).
E.C expresa certeza entera, no probabilidad calibrada. La región y época se
proporcionan por el adaptador perceptivo, nunca desde el ID de mundo.

Memoria de 512 observaciones, append-only por episodio. Al llenarse se niega
nueva autoridad y falla cerrada, conservando historia. Duplicados no crean
evidencia nueva. Capturas antiguas no desplazan observaciones más recientes.
Cada fuente tiene una familia de dependencia declarada: depth/rgb comparten
cámara, lidar es otra, host nunca sirve para certificar barrera libre.

## Regla fijada

- TTL 250 ms desde captura; captura futura o posterior a llegada inválida.
  Una captura futura queda en historia, pero no desplaza la observación válida
  ni puede impedir que la fuente se recupere con datos nuevos.
- Sólo el último registro por fuente/predicado/región/época conserva autoridad.
  Una observación nueva inválida retira la autoridad de la anterior.
- Conflicto sólo entre valores conocidos de familias independientes, mismo
  predicado/región/época y separación de captura ≤100 ms.
- Conflicto fresco: DESCONOCIDO, C=0, ATTEND solicitado; registros conservados.
- Dos familias frescas concordantes y comparables: C=80. Una sola: C=40.
  Familias sin acuerdo interno no votan. Sin soporte: C=0.
- Autorizar una propuesta de avance abstracta exige barrera ausente C≥80;
  el gate existente recibe inhibit en los demás casos. No se mandan setpoints.
- La expiración de un conflicto no crea evidencia: una fuente restante tiene
  C=40. Recuperación C=80 exige nuevo acuerdo de dos familias.
- Los ticks de consulta hacen caducar evidencia aunque no llegue ningún frame.

## Banco y separación

Se reutilizan, sin modificar, los 12 vuelos principales de aceptación
PATTERN-1R v4. Su replay valida interfaces físicas, no constituye vuelos nuevos
ni una nueva confirmación geométrica. Se extraen ventanas de profundidad/LiDAR
conservadas en los logs privados, pero se eliminan pose, verdad e identidad antes
del consumidor. El evaluador conserva los hashes de archivo y de cada extracto.

El contrato causal usa secuencias sensoriales pequeñas generadas con reglas
analíticas: acuerdo libre/ocupado, conflicto en ambas direcciones, diferente
predicado, región y época, caducidad, duplicación, fuente correlacionada,
paquete atrasado, captura futura, corrupción, no retorno y recuperación.
Los valores, orden y tiempos varían. Reglas y límites preceden al banco.

Desarrollo semilla 20261701 (4 repeticiones por condición), validación 20261702
(16), confirmación funcional 20261703 (32). Estas particiones no son el C físico
sellado de TRANSFER-3. Consumidor separado mediante la jaula SIM-3; sin repo,
red, mundo ni entorno del supervisor. El banco añade tests de acceso denegado.

## Verde, rojo y controles

Todas las consultas deben coincidir con un oráculo de adjudicación independiente
(no invoca resolve), conservar los registros, respetar causalidad y WSP=16.
Cero avances autorizados en conflicto/sin dos fuentes. Acuerdos libres deben
permitir avance; callar siempre es rojo. Reportar denominadores por condición,
distribución de decisiones, intervalos Wilson por episodio y latencia P99 del
reductor (no se presenta como latencia de vuelo).

Controles: última observación gana y abstención siempre. El completo debe
reducir falsos acuerdos frente al primero y permitir más acuerdos que el segundo.
Mutantes: última fuente soberana, nunca caducar, contar duplicados como fuentes,
fusionar predicados, colapsar regiones, borrar conflicto, confianza constante,
permitir avance desconocido. Cada uno debe fallar un caso nombrado, con gemelo
honesto correcto. Auditoría recalcula entradas y salidas en proceso nuevo;
detecta borrar un episodio, falso verde, alterar WSP, fuente, tiempo, control
y hash. No basta con que un informe rojo siga rojo.

Se fijan código, diseño, pruebas, protocolo y hashes de evidencia heredada
antes de aceptación. Errores y rojos se conservan. Artefactos en `lab/fusion1/`,
certificado `lab/echo3_fusion1_report.json`. Sólo un certificado verde válido
abre COMPOSE-1. El cierre no acredita RGB semántico, SLAM, independencia física
absoluta entre simuladores, vuelo decidido por echoAI ni seguridad universal.
