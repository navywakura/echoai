# E · plan ejecutable del último intento · 23/10/2026

1. Verificar hashes de las tres trazas previas y cuantificar mecanismo, sin nuevos
   pasos. Guardar `prior-inspection.json` y observación en `live.jsonl`.
2. Contrato DESIGN anterior a medir. Pruebas con estados sintéticos que separen
   contorno, giro fuera del rumbo, controles intactos, progreso y coste por réplica,
   conjunto exacto, corrupción, inmutabilidad y fallos. Verificar rojo antes de implementar.
3. Implementar módulo nuevo: núcleo importa Gate/Controller, frontera importa
   sensado; registro compatible con auditoría heredada extendida para candidato.
4. Revisión estática y pruebas nuevas+heredadas. Congelar fuentes/dependencias,
   diseño/plan/pruebas, agenda, copias custodiadas y versiones. Revisor coordinador.
5. Aprender dos linajes nuevos de40 episodios secuenciales. Ambos completos antes
   de comprometer tablas; si falla cualquiera no lanzar validación.
6. Ejecutar300 episodios de validación (100 triples), máximo4 procesos, sin repetir.
   Registrar decisiones reales cada200 pasos y resumen por episodio en live.jsonl.
7. Auditoría offline de380 trazas, decisiones/actuadores, cadenas, fases/tablas,
   emparejamiento, totales, puertas y prueba de signos exacta. Sin nuevos env.step.
8. Publicar informe local RESULTS con todas las cifras y limitaciones, manifiesto
   SHA256 incluido informe. Si no verde: cierre definitivo «deuda residual,
   autopsiada». No editar roadmap/handoff globales, commits, GitHub o Hugging Face.

Comandos previstos desde echoai (PYTHONPATH al repo padre):

```sh
PYTHONPATH=.. python3 -m unittest tests.test_echo58_shieldrepair
PYTHONPATH=.. ~/.venvs/safe1/bin/python -m echoai.echo58.shieldrepair.bench prepare lab/echo58/shieldrepair/final-20261023-r1
PYTHONPATH=.. ~/.venvs/safe1/bin/python -m echoai.echo58.shieldrepair.bench run lab/echo58/shieldrepair/final-20261023-r1
PYTHONPATH=.. ~/.venvs/safe1/bin/python -m echoai.echo58.shieldrepair.audit lab/echo58/shieldrepair/final-20261023-r1
```

La carpeta existe solo por diagnóstico previo; prepare exige que no tenga freeze,
recibos o marcador de intento. Las escrituras científicas son exclusivas. El diario
live es append-only durante el trabajo. Las pruebas sintéticas no consumen mundos.
