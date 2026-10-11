# Estado de la validación de ECHO-5

**Actualización pública, 12 de octubre: ECHO-5 5.0.0 verde en su alcance.**
[Release](RELEASE-5.0.0.md) · [Veredicto publicado](../../research-archive/20261012/closure-verdict-20261011-r3/result.json).
El estado fechado que sigue describe el cierre r3, ya terminado; las fases
condicionadas de su protocolo no son trabajos pendientes del release.

2026-10-11T21:56:21+02:00

Cadena verificada; consultar el veredicto de alcance antes de publicar.

- Coordinador: `finished`, PID `235566`.
- Calibración: `audited`, 6/6 episodios terminados.
- Episodio de desarrollo indicado por el estado: `{}`.
- Cadena completa: `closure_verified`.
- Comprobaciones requeridas: `valid=True`.
- Fuentes congeladas: `3ffc0900d5670b95321f3c00ff55ef3ebe45c4978d894d44b1a368f809f1a77d`.

La calibración anterior se auditó correctamente y falló en 1/6 recibos:
el ULog del control convencional quedó truncado. La [autopsia del cierre](SITL-LOGGER-DIAGNOSIS-20261011.md)
explica la reparación de finalización. Los tres casos de batería baja pasaron:
POWER ordenó aterrizar en casa antes del razonador, según el contrato. No llegar
a la meta en esos casos adversos no es un error a corregir. La nueva calibración
repite casos conocidos; la transferencia se juzga en la confirmación reservada.

Nueva calibración: `artifacts/logger-calibration-20261011-r1/`.
Coordinador: `artifacts/logger-calibration-20261011-r1/coordinator-status.json`.
Continuación condicionada: `artifacts/closure-pipeline-20261011-r3/status.json`.
Checks: `artifacts/closure-checks-20261011-r6/result.json`.
Regresiones privadas Kaggle: `artifacts/kaggle-sitl-20261011-r1/`.

La auditoría independiente debe coincidir y la calibración debe pasar antes
de abrir la batería completa. Después siguen regresión CPU, desarrollo SITL,
confirmación física nueva y finalización. Una prueba negativa detiene las
fases dependientes. Las repeticiones cognitivas son regresiones sobre casos
ya evaluados, no nuevas muestras independientes. S6 queda fuera hasta 5.5.

El observador sólo lee estados de control. No abre los resultados parciales
de la confirmación reservada ni modifica su instrumentación.
