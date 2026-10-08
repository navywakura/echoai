# PROBE2 · revisión de Codex y auditoría independiente

2026-10-01. La preparación de Claude es viable como control de capacidad
dirigido. Se mantiene el plan de 874 propuestas HOLD 0/1, 126 firmas, las
80 partidas A, V3 nativo y el tope de 14.544 partidas. S6 sigue pendiente.

## Revisión anterior a la congelación

El código de `agent.py` contiene una única lectura de `self.HOLD`, al asignar
`self.hold`. La regla de partidas tocadas depende de ese punto de lectura,
de partir del mismo programa y de una ejecución determinista. La comparación
de candidatos existentes y la muestra completa de solidez ponen a prueba
el argumento. Una firma compartida no se utiliza para omitir variantes.

Codex incorporó estas correcciones antes de crear el perfil PROBE2:

- El recibo independiente se vincula al SHA del perfil y resultado originales,
  la base reproducida y los hashes de los controles reejecutados. `valid: true`
  por sí solo no basta. Se requiere la muestra 2, 31, 77 y 178.
- La ruta de caché se resuelve canónicamente; se rechaza cualquier directorio
  dentro de PROBE1. El recibo exige solo desarrollo A, sin B ni examen.
- Las comprobaciones completas de solidez se intercalan al llegar a las
  posiciones fijadas, para detener pronto una contradicción. El orden de
  candidatos y el presupuesto se conservan. `estimate` sigue siendo pequeño.
- Los controles de PROBE1 se recomprueban al reanudar recibos guardados.
- La calibración prevé **190 partidas**: 160 de base y replay, 26 de cribado
  y 4 de replay del primer candidato. Los 26 corresponden solo al cribado.

Los tests incorporan rechazo de recibos con perfil antiguo, caché original,
resultados de muestra ausentes o datos B. El primer resultado de referencia
fue 11/11 antes de estos cambios. La batería revisada pasó **11/11** con
Python 3.12 en 381,241 segundos antes de congelar y medir PROBE2.

## Auditoría independiente de PROBE1

Ejecutor: `seed/s6probe1_audit.py`. La muestra está fijada en su perfil antes
de jugar: **2, 31, 77, 178**. El candidato 2 es un control sin ganancia;
31 gana +1 sin pérdidas; 77 y 178 son los dos controles objetivo.

Directorio exclusivo: `lab/seed/s6probe1-20260930-audit/`. Se reconstruyen E0,
el plan de individuales y la selección de pares. Se comprueban el archivo
de fuentes, claves, digests y origen A de los 22.160 registros y el presupuesto
original. Después se reejecutan la base con replay y las 80 partidas de cada
candidato de la muestra, con cuatro procesos y Python 3.12 congelado.

Presupuesto independiente: **480 partidas**. La comparación exige los
registros completos y efectos originales, además del veredicto V3. Las
fuentes y el resultado originales se comprueban de nuevo al terminar.
Un error queda como `BLOCKED`; solo al terminar todas las comprobaciones
se escribe `audit.json` con `valid: true`.

La auditoría terminó válida a las **14:51 del 1 de octubre, hora de Madrid**.
El recibo `lab/seed/s6probe1-20260930-audit/audit.json` acredita 480 partidas
independientes y 22.160 registros originales comprobados. La base y su
replay coinciden; los controles 2, 31, 77 y 178 reproducen todos sus registros,
efectos y V3. Sus niveles son respectivamente 378, 379, 383 y 382. Las
pérdidas originales se conservan: estos números no convierten 77/178 en V3.
PROBE1 conserva sus fuentes y resultados originales.

### Recuperación del instrumento de auditoría

La primera ejecución se detuvo después de 240 partidas independientes:
el comparador distinguía tuplas recién ejecutadas y listas leídas del JSON.
El candidato 2 tenía exactamente el digest, efectos y V3 originales; no
hubo una divergencia del agente. Se conserva el estado `BLOCKED` inicial.

`seed/s6probe1_audit_recovery1.py` declara una recuperación separada y
congelada: normaliza únicamente la representación mediante JSON canónico,
comprobando que conserva su SHA. No modifica ejecución, V3, muestra ni
fuentes de PROBE1. Reutiliza las 240 partidas independientes guardadas y
completa las restantes en la misma caché separada. El recibo terminal
incluye el hash y la ruta de esta recuperación; el fallo inicial y el
presupuesto se preservan en `instrument-recovery1/`.

## Calibración y continuación

Tras la auditoría válida, `prepare` archiva y congela las fuentes revisadas.
`estimate` comprobará paridad y el control 178, que está en la posición 3.
La posición 93 (control 77) se comprobará durante el recorrido completo.

El cálculo de duración debe contemplar las 8.386 partidas de cribado y la
apertura de un pool por candidato: los cinco primeros tocan menos partidas
que la media del plan. No extrapolar sin más su duración media multiplicada
por 874. Incluir replays, solidez y verificación de supervivientes, y dar un
intervalo condicionado al ritmo observado. Un éxito sigue siendo evidencia
de capacidad en A; el descubrimiento autónomo y B1–B5 permanecen pendientes.

### Calibración completada

`estimate.json` quedó listo a las **14:58 del 1 de octubre, hora de Madrid**.
La calibración reservó exactamente **190 partidas**. La base y su replay
reproducen 378 niveles y el digest `4458a4c2…`; el digest de comportamiento
es `4cf4148e…`. El replay del candidato 0 es idéntico y el control 178,
en la posición 3, reproduce sus registros originales.

Los cinco candidatos iniciales no sobreviven al cribado. Los tiempos fueron
53,195 s (incluido replay), 26,870 s, 37,584 s, 38,660 s y 37,899 s. El
máximo observado por worker fue 218,4 MiB, con 115,8 GiB libres en disco.
Estos cinco casos no permiten extrapolar el resultado de los otros 869.

La integridad se comprobó de nuevo tras medir. El recorrido completo **no
se ha lanzado**: se entrega el dato real de calibración para la revisión
acordada con Claude. No editar `seed/s6probe2.py`, sus tests ni el contrato:
las fuentes están congeladas. Tras revisar `estimate.json`, la continuación
usa `lab/arc3/ARC-AGI-3-Agents/.venv/bin/python -m seed.s6probe2 run` y
reutiliza los cinco cribados existentes. Mantener los cuatro workers, el
plan y los criterios de parada. No trasladar los candidatos del sondeo a
los prompts del futuro experimento autónomo.
