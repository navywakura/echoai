# ECHO-5.1 · PCWORLD-1

Prototipo de investigación iniciado a partir del plan del 12 de octubre. Su
primer contrato comprueba aislamiento, custodia y presupuesto. El verde de
ECHO-5 no certifica este prototipo ni una ventaja multiagente.

**Entrega de desarrollo validada:** 138 tests PCWorld y 59 regresiones
seleccionadas pasaron; 16/16 episodios con respuestas programadas y una auditoría
válida de 576 recibos. **ECHO-5.1 sigue en investigación:** no hay un ensayo de
calidad con LLM ni un cierre científico. [Resultados y límites](docs/RESULTS.md).

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
- [Diferencias del checkout](docs/RECONCILIATION.json).
