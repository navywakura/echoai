# DYNAMIC-1 v2 — resultados del 14 de septiembre de 2026

**Estado: VERDE en su alcance software/SITL.** `dynamic1_green=true`,
`evidence_valid=true`: 250 comprobaciones (89 A + 161 banco), 29 episodios
reconstruidos, cero hallazgos; 7/7 manipulaciones del informe detectadas.
Contrato vigente:
[DYNAMIC1-V2-DESIGN.md](DYNAMIC1-V2-DESIGN.md), enmiendas 1 y 3.
El rojo de [v1](DYNAMIC1-RESULTS.md), su código y todas sus trazas se conservan.

## Cadena ejecutada

Roger autorizó revisar DYNAMIC-1 y continuar con PATTERN-1R tras su cierre.
La revisión previa corrigió el constructor de tratamientos del auditor:
todavía usaba v1, que no reconoce el mutante `blind_place`. Ejecución y auditoría
usan ahora `scheduled_spec`; se verifican también `arm` y `faulted` contra el
calendario. No se cambiaron consumidor, métricas, límites ni muestra durante
esta revisión. El seguimiento de caras y la enmienda 3 ya estaban implementados.

Antes del lock pasaron once suites: **652 pruebas ejecutadas**, con un fallo
esperado declarado en NEXUS-0. No hubo fallos inesperados. Registro:
`lab/dynamic1-v2/regression.json` y sus once logs.

| Evidencia | Resultado |
|---|---|
| A | 8 vuelos principales + 2 controles estáticos; 28/28 grupos |
| Banco | 12 vuelos principales + 7 mutantes; 29/29 grupos |
| Ejecución | 29/29 vuelos completos; cero reinicios de arranque |
| Cable sensorial | 209.587 frames en A y 408.504 en banco, incluidos controles y mutantes |
| Tiempo por etapa | A: 518,59 s; banco: 1.033,82 s; excluye regresiones y auditorías posteriores |
| Auditoría de A que abrió el banco | 89 comprobaciones, 10 episodios, cero hallazgos |

## Qué midió

| Métrica | A | Banco | Límite congelado |
|---|---:|---:|---:|
| Detección agregada del movimiento | 914/956 = 95,61 % | 1.343/1.404 = 95,66 % | ≥85 % |
| Detección mínima por vuelo principal | 92,50 % | 92,55 % | ≥70 % |
| Máximas falsas alarmas sobre quietos, vuelos principales | 22,38 % | 27,95 % | ≤30 % |
| Máximas falsas alarmas en control estático | 7,53 % | No se programaron controles estáticos adicionales | ≤15 % |
| Mayor mediana de error del desplazamiento predicho | 38 mm | 33 mm | ≤60 mm |
| Mayor p95 de error del desplazamiento predicho | 98 mm | 103 mm | ≤350 mm |
| Mayor mediana de error de posición | 172 mm | 171 mm | ≤500 mm |

Las posiciones y desplazamientos son los observados por el backend, no sólo
los comandos del arnés. La predicción es a 500 ms y sobre la **componente normal
de una cara plana**. El cuerpo permanece en vuelo estacionario mientras el
arnés mueve una pared. Esto no mide identidad persistente desde un cuerpo que
navega, velocidad tangencial de una pared, maniobras evasivas ni autonomía.

Los siete mutantes volaron sanos, fallaron sus casos previstos y tuvieron un
gemelo honesto que pasó el grupo correspondiente: `no_motion`, `always_motion`,
`copy_current`, `replay`, `frozen_world`, `extra_channel` y `blind_place`.

## Límites del verde funcional

- Son mundos **rehearsal** ya declarados, compartidos con el desarrollo. Las
  semillas de etapa cambian condiciones y calendario de fallos; no generan
  geometrías reservadas nuevas. No se acredita transferencia A→B/C.
- El 27,95 % de falsas alarmas del peor vuelo no es seguimiento perfecto.
  Este contrato admite hasta 30 %. No se eliminó la deriva del propio cuerpo.
- v2 tiene criterios distintos de v1, publicados antes del lock: entre ellos,
  p95 ≤350 mm frente a 160 mm. La historia conserva predicciones espurias de
  hasta 1,37 m que pueden quedar fuera del p95. Esta cadena no demuestra su
  imposibilidad ni sustituye esa historia por un verde.
- La posición se juzga por mediana, no por una cota de cola. Hay 6 registros en
  A y 105 en los vuelos principales del banco sin correspondencia con una
  barrera evaluable; se publican, pero no puntúan como identidad de objeto.
  No hubo registros saltados por fallo de alineación en esos vuelos.
- Los fallos sensoriales programados ocurren antes de la ventana de movimiento;
  no se acredita seguimiento bajo apagón sensorial durante dicha ventana.
- `agent_in_gazebo=false`, `cortex_calls=0`, `wsp_writes=0`;
  `hardware_status=not_available`. Hay traducción instrumental de sensores a
  WSP, no un agente que decida pilotar. No hubo hardware ni Akida.

## Huellas y reproducción

| Artefacto | SHA-256 canónico |
|---|---|
| Lock | `7a30c4cf1aeb6c520fc376b233a6f78de3aa2499a0bbd2b4bed1715122aec2d0` |
| Certificado final | `c9cf56758a3ce9894b68f5361f7f4a86a025357d0b3cc76e1a36fba9944a87dd` |
| A | `0411b474909374ad9065a7d2999601cb1bf0377fce84b26ff9f2829f324b298b` |
| Banco | `ebe419256a8e4d613f2d9481c5df00256b52ac8f9b7bfeea1d83cf02f96da072` |

Desde `echoai/`, para auditar los vuelos guardados sin repetirlos:

```bash
PYTHONPATH=.. python3 -m echoai.nexus0.dynamic1_v2.campaign audit
```

La cadena iniciada con `campaign start` es inmutable. No volver a iniciarla ni
repetir sólo episodios fallidos. Los archivos de `lab/dynamic1-v2/`, incluidas
muestras privadas, transcripts, ULog, protocolo y lock, son parte de la evidencia.
El resultado final se publica en `lab/echo3_dynamic1_v2_report.json`.
