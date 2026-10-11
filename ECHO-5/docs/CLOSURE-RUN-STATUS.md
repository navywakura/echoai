# Estado de la validación de ECHO-5

2026-10-11T04:38:10+02:00

Cadena detenida; ECHO-5 continúa pendiente de cierre.

- Coordinador: `stopped`, PID `122734`.
- Calibración: `audited`, 6/6 episodios terminados.
- Episodio de desarrollo indicado por el estado: `{}`.
- Cadena completa: `pending_calibration`.
- Comprobaciones requeridas: `valid=True`.
- Fuentes congeladas: `4e49d35ebe03cb742f00ffb52e321067f67b43e9fd59faf8907fdb8c5b04191f`.

La confirmación anterior terminó con dos fallos: llegada del modo ECHO en
un cambio de mundo y observación inicial del control de horizonte uno con
batería baja. Se conservan sus resultados negativos. La [autopsia y corrección](SITL-CONFIRMATION-R1-DIAGNOSIS.md)
explica el error de estimación vertical y la recuperación tras excepción.

Nueva calibración: `artifacts/velocity-calibration-20261011-r1/`.
Coordinador: `artifacts/velocity-calibration-20261011-r1/coordinator-status.json`.
Continuación condicionada: `artifacts/closure-pipeline-20261011-r2/status.json`.
Checks: `artifacts/closure-checks-20261011-r4/result.json`.
Regresiones privadas Kaggle: `artifacts/kaggle-sitl-20261011-r1/`.

La auditoría independiente debe coincidir y la calibración debe pasar antes
de abrir la batería completa. Después siguen regresión CPU, desarrollo SITL,
confirmación física nueva y finalización. Una prueba negativa detiene las
fases dependientes. Las repeticiones cognitivas son regresiones sobre casos
ya evaluados, no nuevas muestras independientes. S6 queda fuera hasta 5.5.

El observador sólo lee estados de control. No abre los resultados parciales
de la confirmación reservada ni modifica su instrumentación.

Motivo de parada: `RuntimeError('calibration or independent audit did not pass')`.
