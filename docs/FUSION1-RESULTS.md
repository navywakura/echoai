# FUSION-1 — resultado funcional y replay SITL

2026-09-14. **VERDE en el alcance de FUSION1-DESIGN.md**, con auditoría
repetida en un proceso nuevo: `fusion1_green=true`, `evidence_valid=true`,
cero hallazgos. No fueron vuelos nuevos ni navegación integrada.

| Etapa | Episodios/ventanas | Consultas | Permisos sin soporte | Acuerdos libres admitidos |
|---|---:|---:|---:|---:|
| Desarrollo (no aceptación) | 72 | 100 | 0 | 16 |
| Validación funcional | 288 | 400 | 0 | 64 |
| Confirmación funcional | 576 | 800 | 0 | 128 |
| Replay reducido de doce vuelos SITL | 240 ventanas | 2.160 | 0 | 600 |

En confirmación, «la última fuente gana» autorizó 384 consultas sin soporte;
abstenerse siempre no autorizó ninguna de las 128 válidas. El completo coincide
con el adjudicador independiente en todas las condiciones. Cada condición de
confirmación contiene 32 episodios; intervalo Wilson 95 % para 32/32:
[0,893; 1]. Es cobertura de reglas y tiempos generados, no fiabilidad universal.

Ocho mutantes: 32/32 casos detectados por mutante y gemelos honestos correctos.
Siete alteraciones del informe rechazadas, partiendo de un informe verde.
Quince pruebas unitarias/de integración correctas antes del lock. El gate
histórico coincide con todos los permisos emitidos. Sin cambios al núcleo
congelado, sin nuevas neuronas y sin LLM.

P99 del reductor en el host: 22.908 ns en validación, 20.603 ns en confirmación
y 18.229 ns en replay. Excluye sensores, comunicación, codificación y vuelo;
no es una promesa de tiempo real. Capacidad: 512 registros por episodio,
historia conservada, rechazo de nueva autoridad al llenarse. E.C no es una
probabilidad calibrada.

## Qué funciona y qué no demuestra

El módulo conserva procedencia, captura y llegada, rechaza extractos inválidos,
descuenta duplicados/fuentes correlacionadas, separa predicados y marcos, hace
caducar evidencia aunque cese el stream y exige acuerdo nuevo para recuperar
certeza alta. Sus salidas son WSP de 16 bytes. ATTEND es una solicitud registrada;
esta fase no despierta un córtex ni manda un setpoint.

Las muestras físicas se reducen a un píxel de la fila central de profundidad y
un haz frontal de LiDAR conservados por SENSOR-1S. Región/época locales se
reinician por ventana. No hay compensación general de movimiento, estimación
de volumen libre, RGB semántico, SLAM, hardware ni prueba de cristal real. Los
conflictos sistemáticos del contrato son intervenciones analíticas; no se
presentan como fallos de materiales generados físicamente en Gazebo.

El bus del consumidor en la jaula lleva WSP y su registro externo de procedencia;
no contiene pose privada, nombre de mundo ni plan. Se comprobó la jaula SIM-3
(montajes, PID, red y entorno aislados). El cierre es un componente opt-in;
la unión conductual con memoria espacial y objetivos pertenece a las fases
siguientes. No convierte una barrera ausente en permiso de vuelo real.

## Evidencia

- Lock: `9d260f2d4c7b667bafa19378105e89addf03f95dbe8648f833a93785cc7d56fd`.
- Certificado: `bfa7c57845864d7ec93c20b6bd4ce635a4118cd8ed9cb819b76c7b747d2f95a4`.
- Informe: `lab/echo3_fusion1_report.json`; protocolo, muestras y etapas: `lab/fusion1/`.
- Los archivos heredados de PATTERN-1R v4 no se modificaron; el lock pina los
  hashes de los logs originales utilizados y del adaptador que los reduce.

Desde `echoai/`:

```bash
PYTHONPATH=.. python3 -m echoai.tests.test_fusion1 -q
PYTHONPATH=.. python3 -m echoai.nexus0.fusion1.bench audit
```

La auditoría lee y reconstruye; no vuelve a volar ni sobrescribe resultados.
El siguiente trabajo autorizado es COMPOSE-1.
