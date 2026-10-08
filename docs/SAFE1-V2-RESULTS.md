# SAFE-1 v2 — contención de fallos con auditoría de reintentos normales

2026-09-17. **Verde en el dominio funcional y SITL declarado.**

| Evidencia reservada | B | C |
|---|---:|---:|
| Episodios funcionales válidos | 512/512 | 512/512 |
| Vuelos válidos, sin hallazgos | 6/6 | 6/6 |
| Fallos contenidos con aterrizaje nativo | 5/5 | 5/5 |
| Objetivos enviados en vuelos con fallo | 0 | 0 |
| Máximo tiempo hasta veto | 288 ms | 269 ms |
| Máximo veto → desarmado | 27.723 ms | 24.638 ms |
| Error verdadero de llegada nominal | 153 mm | 141 mm |

Los diez vuelos con fallo muestran pérdida GCS, failsafe y AUTO_LAND en
ULog, sin NAV_LAND externo ni recuperación de misión. Los dos nominales
completan su objetivo; ACK por sí solo no cuenta como llegada. C ejercita
también dos intentos normales de armado, con rechazo y aceptación posteriores
verificados por el auditor corregido. No se relajaron plazos ni envolventes.

Auditoría en proceso nuevo válida, exit 0; tres manipulaciones del informe
(numerador, hash de traza y lock, incluso recalculando su certificado)
rechazadas. Regresión final: **108 tests, todos pasan**.
Certificado: `eecb77b8c0b9c2146eafa996857c3d94189b3252ff418b6292523acaa0086c37`.
Informe: `lab/echo3_safe1_v2_report.json`; recibo:
`lab/safe1-v2/audit-receipt.json`.

Lock: `a34abbccae92af8d228c794fa49d95f38f6fdbae8a71efbf4e4884acb5a2f5c9`.
108 tests previos a B: 97 heredados y 11 del auditor de armado.
Seis mutantes del supervisor/lease y cuatro corrupciones detectados.

V2 conserva exactamente el núcleo, IPC, lease, worker, adaptador, PX4 y
parámetros de v1. Corrige sólo la confusión del auditor entre reintento
normal tras rechazo y armado forzado. Exige correspondencia de todos los
intentos con sus ACK y eventos, un único éxito final antes de supervisión,
y cero armado forzado/desarmado externo. Ningún otro hallazgo se descarta.
[Contrato prospectivo](SAFE1-V2-DESIGN.md).

Desarrollo reutilizado y reauditable: los seis vuelos y 128 episodios de A v1,
todos válidos. No son seis vuelos nuevos. B/C v2 usan semillas nuevas;
512 episodios funcionales y seis vuelos por etapa. El B rojo de v1 y su C
no abierto están vinculados al nuevo lock; no se reetiquetan como aprobación.
[V1 y su desarrollo anterior](SAFE1-RESULTS.md) se conservan íntegros.

El dominio sigue siendo una transacción de un metro desde hover, con fallos
inyectados antes del objetivo. Se congela el sello de captura/recepción
entregado al supervisor, no el flujo privado ni un cable físico. Se ensayan
salida/bloqueo real de proceso y WSP inválido por IPC. Sin recuperación
automática; PX4 debe aterrizar por pérdida GCS sin NAV_LAND externo.
No prueba seguridad general, fallos adversariales, hardware, navegación
integrada, batería física ni el cierre de DRONE-3. Energía `sim_u`, sin LLM.

## Reproducción

Desde `echoai/`:

```bash
PYTHONPATH=.. python3 -m unittest echoai.tests.test_safe1 echoai.tests.test_safe1_v2
PYTHONPATH=.. python3 -m echoai.nexus0.safe1_v2.bench audit
```

Auditoría reconstructiva en proceso nuevo, sin nuevos vuelos. Las fuentes y
artefactos de todos los intentos anteriores permanecen vinculados por hash.
