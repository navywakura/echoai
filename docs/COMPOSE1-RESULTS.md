# COMPOSE-1 — resultado funcional; cierre completo pendiente

2026-09-14. **`functional_green=true`, `compose1_green=false`.** El módulo
compone movimientos aprendidos, consulta evidencia FUSION-1, publica la
predicción antes de actuar y conserva reserva en un banco cinemático 3D.
Todavía no ejecuta esos movimientos mediante Gazebo/PX4. No se contabiliza
como hito cerrado de ECHO-3.

## Resultado medido

Aprendizaje en A: 2.048 transiciones, 16 semillas, 550 intentos bloqueados
registrados sin penetrar paredes. Se reutilizan CAM, World/T y Q existentes;
el modelo serializado no contiene el mapa. Desarrollo: 96 misiones.
Validación B y confirmación C funcional: 192 misiones por etapa, **384 en total**,
con seis brazos y cuatro condiciones. Son misiones cinemáticas, no vuelos.

| Brazo | Llegadas B, casos accesibles | Llegadas C, casos accesibles | Pasos B / C, todas las condiciones |
|---|---:|---:|---:|
| Completo, presupuesto 8 | 16/16 | 14/16 | 828 / 880 |
| Completo, presupuesto 32 | 16/16 | 14/16 | 828 / 880 |
| Mismo agente, horizonte uno | 16/16 | 14/16 | 828 / 880 |
| Sin caducidad | 16/16 | 14/16 | 828 / 880 |
| Q reactiva | 0/16 | 0/16 | 1.232 / 1.238 |
| Búsqueda convencional sin prioridad Q | 15/16 | 13/16 | 784 / 786 |

Cada etapa incluye también ocho accesos cerrados y ocho casos de energía
insuficiente por brazo. El completo termina en casa en los 16/16 de ambas
etapas. Sus dos metas accesibles fallidas de C también acaban en casa:
`202618205` (estática) y `202618214` (dinámica), 52 pasos y 32 unidades de
energía restantes. Se conserva el fracaso; no se repiten sólo esos casos.

Cero colisiones, hechos de llegada sin observación, violaciones de reserva o
escrituras de rollouts en los seis brazos del banco. Estas cifras describen
este simulador y protocolo. Los pasos agregados incluyen abandonos: menos
pasos no implica por sí solo mayor eficiencia de misión.

La diferencia emparejada frente a Q es +16/16 en B y +14/16 en C.
El bootstrap registrado da [0,6875; 1] para la diferencia media en C.
El intervalo degenerado [1; 1] de B reproduce una muestra sin variación:
no demuestra certeza poblacional. Las variantes comparten un generador
geométrico pequeño; no equivalen a transferencia abierta a salas reales.

## Qué demuestra y qué sigue sin demostrar

Hay navegación hacia una coordenada propuesta, búsqueda de una abertura,
verificación del siguiente movimiento, memoria perceptiva actualizada y
abandono con reserva. La llegada sólo se confirma por observación local de
la estación. La política y T/Q quedan congeladas en B/C; las creencias
espaciales empiezan vacías y sí se actualizan al percibir.

**El horizonte uno empata al completo tanto en llegadas como en pasos.**
La ventaja frente a Q no puede atribuirse específicamente a componer cuatro
pasos: memoria espacial, exploración y búsqueda de un paso bastan en este banco.
La ablación sin caducidad también empata. No se ha demostrado que esos dos
mecanismos sean necesarios para esta tarea. El control convencional comparte
la búsqueda, sin prioridad Q; no representa al mejor planificador industrial.

El cuerpo sólo aprende seis desplazamientos axiales y espera. No aprende a
abrir puertas, manipular herramientas ni descubrir affordances de objetos.
La odometría es exacta y los rayos geométricos son ideales; dos canales
analíticos de ocupación no son una cámara y un LiDAR físicos. El cambio de
abertura conserva una exposición visual antigua, sin simular óptica real.
La reserva usa costes enteros de movimiento; no son julios ni POWER-1 cerrado.

Falta la puerta Gazebo/PX4 del [diseño congelado](COMPOSE1-DESIGN.md), además
de un banco que discrimine composición de medios frente a reacción con memoria.
La continuación está descrita en [COMPOSE1-SITL-HANDOFF.md](COMPOSE1-SITL-HANDOFF.md).
No hace falta AKD1500 ni otro hardware para desarrollar esa continuación SITL.

## Verificación y coste

Nueve tests antes del lock; cinco mutantes detectados con gemelos honestos:
escribir rollouts, ignorar evidencia, ignorar reserva, convertir la hipótesis
de meta en hecho y admitir identidad privada del mundo. Seis alteraciones
de informe rechazadas por etapa: omisión, éxito falso, predicción alterada,
acción alterada, escritura indebida y resultado falso.

La aceptación ejecuta cada consumidor en la jaula SIM-3, sin generador,
plano, semilla, repositorio ni red. Una lista explícita monta las dependencias
originales CAM/T/Q y FUSION; no se reimplementan para el banco. El auditor
reconstruye las 384 misiones y compara decisiones, resultados y JSONL con
predicciones anteriores a la acción. Es replay con la implementación fijada,
no una segunda implementación independiente del planificador.

Auditoría repetida en un proceso nuevo: exit 0, `evidence_valid=true`,
`functional_green=true`, `compose1_green=false`, cero hallazgos. Inventarios
congelados de FUSION (19 archivos) y COMPOSE (23) comprobados sin diferencias.

Para `echo32`, profundidad observada máxima cuatro y candidatos máximos 30.
P99 por misión del intercambio completo con el consumidor, incluyendo hashes
de auditoría: mediana 7,23 ms en B y 7,33 ms en C; máximos 9,58 y 9,88 ms.
No incluye PX4 ni sensores físicos y no certifica tiempo real. CAM usa 130
ranuras del modelo; el mapa tiene un límite de 256 referencias locales.
El cálculo auxiliar de retorno puede recorrer esas 256 celdas; su coste no
se confunde con el presupuesto 8/32 de búsqueda de movimientos.

## Evidencia y reproducción

- Lock, sello canónico: `3db502133368332060ff9cd110e0c7830a24754321ee96faba7871124b7aea5e`.
- Certificado, sello canónico: `fd74e244fcad55de153adeacafe87c71a3b4c854e0d5687e7889eb6c64eeee02`.
- Informe: `lab/echo3_compose1_report.json`; artefactos: `lab/compose1/`.
- Se conserva el primer fallo de montaje de la jaula en
  `lab/compose1/review/preflight-1/`: no llegó a ejecutar misiones.
- A/B/C funcionales quedan consumidas; cualquier protocolo nuevo tendrá
  particiones nuevas y conservará este resultado.

Desde `echoai/`:

```bash
PYTHONPATH=.. python3 -m echoai.tests.test_compose1 -q
PYTHONPATH=.. python3 -m echoai.nexus0.compose1.bench audit
```

`audit` verifica evidencia sin sobrescribirla. Un exit 0 de auditoría no
convierte `compose1_green=false` en un cierre de fase.
