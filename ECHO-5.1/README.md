# ECHO-5.1 · investigación cerrada

Publicación del 16 de octubre de 2026. **Sin ventaja de resolución demostrada
en SWE-bench Lite; no es un release verde científico.**

- [Conclusiones científicas, de ingeniería y estratégicas](docs/PUBLICATION-20261016.md).
- [Informe final SWE-bench y límites](docs/REPOWORLD-SWE-RESULTS-20261016.md).
- [Datos, contratos, auditoría e imágenes reproducibles](docs/swebench/results-v8-20261016/README.md).
- [Cierre y pendientes](docs/CLOSURE-20261016.md).
- [Verificación de publicación: fallos actuales conservados](docs/PUBLICATION-VERIFICATION-20261016.json).

La verificación actual no obtuvo un gate completo verde: se documentan
incidentes de cancelación, metadatos y longitud de ruta de socket.

![Resolución y denominadores](docs/swebench/results-v8-20261016/figures/01_resolution.png)

![Coste y resolución](docs/swebench/results-v8-20261016/figures/03_cost_resolution.png)

## Inicio de PCWORLD-1 · contexto histórico

Prototipo de investigación iniciado a partir del plan del 12 de octubre. Su
primer contrato comprueba aislamiento, custodia y presupuesto. El verde de
ECHO-5 no certifica este prototipo ni una ventaja multiagente.

**Infraestructura ampliada:** 162 tests PCWorld y 59 regresiones seleccionadas.
Runtime Python congelado, caché de propiedades puras, conector local Qwen 7B y
seis familias nuevas de reparación. El primer piloto real terminó: **24/24
episodios auditados, 2/6 tareas resueltas en cada brazo S/I2/F/E**. No se observó
ventaja multiagente. Un diagnóstico separado sí completó el ciclo de
contraejemplo, memoria, reparación y verificación con Qwen.
**Estado en aquel piloto:** la investigación seguía abierta; el cierre final
se documenta en los enlaces anteriores.
La entrega anterior validó 16/16 episodios programados y 576 recibos;
[ese informe histórico](docs/RESULTS.md) no mide la capacidad de un LLM.

El código está en `../pcworld/`; importa CAM, WSP16, ATTEND y gate existentes.
No enciende un LLM en NEXUS-0. El router PCWorld inicial es una política entera
fija condicionada por evidencia. No es una Q aprendida ni automejora.

```sh
python3 -I -B ECHO-5.1/scripts/run.py test
python3 -I -B ECHO-5.1/scripts/run.py pilot --dry-run --tasks 60 --repetitions 2
python3 -I -B ECHO-5.1/scripts/run.py pilot --provider fixture --tasks 4 --output ECHO-5.1/artifacts/dev-01
python3 -I -B ECHO-5.1/scripts/run.py audit ECHO-5.1/artifacts/dev-01
```

Requiere Linux, Bubblewrap, cgroup v2 y un gestor systemd de usuario con límites
de memoria y procesos. Si no están disponibles se niega la ejecución. No se
instalan dependencias, cambian reglas de red del host ni montan credenciales.
La salida de cada operación se registra en `thought.jsonl` y recibos del
supervisor, fuera del workspace del candidato. Puede seguirse con `tail -f`.

`fixture` contiene soluciones programadas para comprobar el recorrido completo.
No son propuestas LLM ni resultados científicos. El dry-run calcula el techo
de 480 episodios/12 millones de tokens para el diseño de 60 tareas, cuatro
brazos y dos repeticiones. No lo ejecuta. La campaña real requiere fijar modelo,
tokenizer, revisión, costes y tareas independientes. La confirmación queda
cerrada desde esta interfaz de desarrollo.

- [Investigación recibida, conservada íntegra](docs/RESEARCH.md).
- [Contrato preliminar](docs/PCWORLD-1.json).
- [Aceptación T01–T20 y obligaciones parciales](docs/ACCEPTANCE.md).
- [Arquitectura y significado de los recibos](docs/ARCHITECTURE.md).
- [Comandos, requisitos y conector opcional](docs/RUNBOOK.md).
- [Costes y resultados por episodio](docs/DEVELOPMENT-SUMMARY.json).
- [Plan y decisiones de implementación](docs/IMPLEMENTATION-PLAN.md).
- [Continuación: runtime, modelo local y piloto](docs/PILOT-IMPLEMENTATION.md).
- [Piloto real: resultados, costes y autopsia](docs/LOCAL-PILOT-20261013.md).
- [Resumen por episodio y hashes de evidencia](docs/LOCAL-PILOT-SUMMARY.json).
- [Checklist actualizado: verde y pendiente](docs/CLOSURE-CHECKLIST.md).
- [Verificación de software de esta entrega](docs/PHASE2-VERIFICATION.json).
- [Diferencias del checkout](docs/RECONCILIATION.json).
