# WSP · uso en episodios completos · 23/10/2026

**Verde de integración de almacenamiento.** El Agent original cargó memoria
de `.wsp` y completó12 mundos nuevos de desarrollo; sus acciones, observaciones
y resultados fueron idénticos a cargar la memoria original en12/12 casos.
No cambia el resultado de W R2 ni es un nuevo examen de inteligencia.

Agenda previa en `WSPFILES-AGENT-PLAN-20261023.md`: LavaGapS7, DoorKey6 y
DynObs6; semillas202610230/202610231; regímenes A1/A2. Tres brazos (memoria
original, memoria del archivo, sin memoria) =36 episodios MiniGrid reales,
sin instalar dependencias ni tocar el Agent. Entorno existente MiniGrid3.0.0,
Gymnasium1.2.0. No se abrieron familias/semillas de examen histórico.

La memoria cargada recibió1.668 consultas y1.283 hits; conserva su head.
Las trayectorias difieren del control sin memoria en12/12 mundos. Estos
doce mundos de integración no estiman una tasa general de éxito ni aíslan
una ventaja nueva del algoritmo: verifican que usar el archivo afecta al
agente y conserva lo aprendido, sin cambios en la política.

Auditoría en proceso nuevo, sin simulador: vuelve a ejecutar la política
original sobre observaciones guardadas y exige cada acción registrada,
resultados, fin exacto de la secuencia y hashes de archivos y fuentes.
36 episodios auditados,12 parejas idénticas. No es replay de física ni
una segunda ejecución de MiniGrid. Una prueba dirigida del wrapper pasa.

La revisión independiente posterior reprodujo el resultado y señaló dos
lagunas del auditor: no cotejaba todo el resumen por mundo y permitía Python
con `-O`, que elimina los asserts. Dos pruebas reprodujeron ambos fallos;
la corrección pasó las dos y la prueba del wrapper. Se conserva el código
usado al jugar en `integration-at-run.py`, el manifiesto original intacto y
una enmienda `audit-amendment.json` con hashes antes/después. La política y
los mundos no cambian ni se vuelven a ejecutar: solo se refuerza la auditoría.

Herramientas nuevas, posteriores al benchmark de formato y fuera de su
manifiesto: `echo58/wspfiles/play.py` e `integration.py`. No se modifica
su corpus, medición ni código congelado. Artefactos de episodios, manifiesto
y resultados en `lab/echo58/wspfiles/agent-integration-20261023/`.

Ejemplo de uso desde la raíz echoai, con el entorno MiniGrid existente:

```bash
PYTHONPATH=.. ECHO-5/.venv-sandbox/bin/python -m echoai.echo58.wspfiles.play \
  lab/echo58/wspfiles/20261023-r1/artifacts/memory-training-m01.wsp \
  --family DynObs6 --seed 202610232 --regime A2 --output /tmp/echo-wsp-episode.json
```

No sobreescribe el destino. Para repetir solo la auditoría, sin volver a jugar:

```bash
PYTHONPATH=.. python3 -m echoai.echo58.wspfiles.integration audit \
  lab/echo58/wspfiles/agent-integration-20261023
```
