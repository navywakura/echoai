**Evaluación offline de V3 por lotes · 9 de octubre de 2026**

El [script](../seed/arc_v3_batch.py) evalúa el candidato V3 ya existente sobre
rejillas ARC-1/2. Funciona con biblioteca estándar de Python, CPU y datos
locales. No realiza llamadas LLM, entrenamiento, descargas ni envíos a Kaggle.
La preparación y la calibración de desarrollo están autorizadas en paralelo
a B24. La evaluación pública completa espera un recibo válido de cierre B24;
no exige que S6 haya pasado.

Se conserva el candidato `relational-v3-20261003/primary/candidate.json` y sus
19 fuentes verificadas. Cada tarea usa un proceso nuevo, memoria y política
restauradas del mismo candidato, `learn=False`, multi-view y consistencia
activas, ventana de verificación 32 y beam 12. El límite por defecto es
500.000 unidades de trabajo, 120 segundos y cuatro trabajadores. El banco
opcional de guía de programas 500k no se añade a este primer perfil: se mide
V3 con su memoria relacional y política ya ajustadas, sin un tratamiento extra.

`prepare` acepta un directorio de tareas JSON, una tarea individual o un
archivo agregado de challenges. `--solutions` admite las respuestas en un
archivo separado; deben coincidir en cantidad y no contradecir etiquetas
incluidas en las tareas. `--ids` selecciona una lista JSON de IDs. Se rechazan
IDs inseguros, JSON con claves repetidas y rejillas fuera del formato ARC.
Se guardan por separado las demostraciones/entradas públicas y las soluciones.
Los procesos del solver reciben únicamente los datos públicos; el padre
califica después de que termine cada proceso. Es separación de datos en un
ejecutor de código conocido, no un sandbox para programas adversarios.

El manifiesto fija tareas, hashes de entradas/soluciones/candidato/código,
incluidos el observador y el verificador de cierre, intérprete y límites.
Al reanudar se verifican esos hashes y los recibos;
no se repiten tareas terminadas. Una reserva interrumpida sin recibo queda
identificada como `INTERRUPTED`, con coste desconocido, y no recibe un intento
gratis. Los timeouts y errores conservan su lugar en los denominadores.
El ejecutor requiere Linux: cada hijo tiene un plazo propio y señal de muerte
del padre. SIGINT/SIGTERM cancelan la cola y recogen los hijos; SIGKILL del
padre tampoco deja una búsqueda viva. La reanudación se niega a clasificar
como interrumpido un hijo anterior que siga activo con la misma identidad.
`COMPLETE` y el archivo exportable se publican después de comprobar la
integridad final. Una incidencia retira la exportación y deja el estado
explícito `INSTRUMENT_BLOCKED`, `INTERRUPTED` o `COMPLETE_WITH_ERRORS`.
El proceso de CLI devuelve código 2 si el lote termina con incidencias del
instrumento. La comparación científica necesita un lote completo y limpio.

Los resultados incluyen:

- `manifest.json`: condición fijada y procedencia.
- `inputs/` y `labels/`: entradas públicas y soluciones separadas.
- `requests/` y `results/`: bytes de entrada del worker y recibos de salida.
- `status.json`: progreso, resueltos y errores.
- `report.json` y `results.csv`: aciertos exactos por tarea y por salida de
  test, abstenciones, incidencias, trabajo, memoria y tiempos.
- `journals/`: observaciones y decisiones reales del solver durante desarrollo,
  usando `echo_arc.observe.Journal`. No se instrumenta la evaluación pública.
- `submission.json`: formato de dos intentos, sin enviarlo a competición.

El criterio principal exige que **todas las salidas de test de una tarea sean
exactas**, dimensiones incluidas. También se informa exactitud por salida.
Una tarea sin soluciones disponibles figura como no calificada; su exactitud
no se convierte en cero. Estos criterios y el formato de rejilla proceden del
[repositorio oficial ARC-AGI-2](https://github.com/arcprize/ARC-AGI-2).

V3 produce una predicción o se abstiene. El exportador duplica esa predicción
en `attempt_1/attempt_2`; no inventa una segunda búsqueda. Si se abstiene,
usa `[[0]]` únicamente como relleno del formato, registrado en
`submission-metadata.json`. El informe estricto conserva la abstención aunque
ese relleno coincidiera por azar con una solución. El archivo exportado y
el informe local no son una puntuación oficial de Kaggle.

Desde la raíz de `echoai`, la calibración preparada usa estos comandos:

```bash
ECHO_BATCH_PYTHON=lab/arc3/ARC-AGI-3-Agents/.venv/bin/python

"$ECHO_BATCH_PYTHON" -m seed.arc_v3_batch prepare \
  --tasks lab/seed/ARC-AGI/data/training \
  --ids lab/seed/arc-v3-calibration-20261009/arc1-ids.json \
  --root lab/seed/arc-v3-calibration-20261009/arc1 \
  --label ARC1-development-timing

"$ECHO_BATCH_PYTHON" -m seed.arc_v3_batch run \
  --root lab/seed/arc-v3-calibration-20261009/arc1

"$ECHO_BATCH_PYTHON" -m seed.arc_v3_batch estimate \
  --root lab/seed/arc-v3-calibration-20261009/arc1 --target-tasks 400
```

Para ARC-2 se cambia `--tasks` por `lab/arc2/ARC-AGI-2/data/training`,
los IDs y la raíz por `arc2`, y el destino de la estimación por 120 tareas.
`prepare` exige una raíz nueva; para continuar una ya preparada se usa `run`.
`python3 observe.py --launch` abre el visor habitual de desarrollo.

La muestra de tiempos consta de **16 tareas por corpus**, seleccionadas de
los 64 casos de desarrollo ya usados por V2. Se ordenan por tamaño de entrada,
se forman cuatro cuartiles y se toman cuatro IDs de cada cuartil mediante
hash y semilla fija. `selection.json` conserva el procedimiento, los IDs y
los hashes anteriores a esta medición. No se seleccionan por su acierto con V3.
La exactitud de esta muestra se registra como desarrollo conocido, sin usarla
para ajustar el solver ni presentarla como transferencia nueva.

La estimación extrapola tiempos observados al número de tareas solicitado
y al mismo número de trabajadores. Da un escenario basado en la media y
otro basado en el percentil 90 de tiempos individuales; **no son un intervalo
de confianza ni límites garantizados**. La mezcla de tareas, carga de CPU y
sobrecoste del lote pueden cambiar. Los límites de tiempo se registran aparte.

**Calibración terminada a las 01:52 de Madrid.** Las 32 tareas completaron
su ejecución con integridad válida, sin errores ni timeouts, en cuatro
procesos locales. Pasan 69 pruebas diferentes del evaluador, custodia de B24,
observador y módulos adyacentes. El
[recibo](../lab/seed/arc-v3-calibration-20261009/calibration-receipt.json)
enlaza selección, perfiles, logs, resultados y tiempos mediante hashes.

| Medición | ARC-1 | ARC-2 |
| --- | ---: | ---: |
| Tareas de desarrollo conocidas | 16 | 16 |
| Aciertos exactos | 0/16 | 0/16 |
| Tiempo del lote local | 2,10 s | 2,07 s |
| Tiempo medio por tarea, incluida creación de proceso | 0,483 s | 0,490 s |
| RSS máxima de un trabajador | 31,0 MiB | 29,0 MiB |
| Lote público previsto | 400 tareas | 120 tareas |
| Proyección por media | 48,3 s | 14,7 s |
| Escenario por percentil 90 | 62,4 s | 25,4 s |

Para ambos lotes reservaría **2–5 minutos**, con el mismo presupuesto y
máquina. Es margen operativo sobre una proyección conjunta de 63–88 segundos,
sin garantía para casos no medidos. Una ejecución que agotase todos los límites
de 120 s podría consumir 3 h 20 min y 1 h respectivamente; ese es el presupuesto
máximo nominal, no la previsión observada. Preparación y verificación añaden
sobrecoste fuera del tiempo de resolución por tarea.

Las 32 tareas terminaron como `NO_PROGRAM`, sin predicciones: 35 salidas de
test quedaron en abstención. Casi todas agotaron las 500.000 unidades de
trabajo lógico; unas pocas agotaron antes sus propuestas. La velocidad procede
de evaluar el solver CPU acotado, sin inferencia LLM. **La muestra no demuestra
mejora de capacidad ni anticipa un resultado oficial ARC**. No se ha ajustado el
candidato con estas observaciones ni abierto la evaluación pública completa.

Después del cierre de B24, el lote completo se preparará con una raíz nueva:

```bash
"$ECHO_BATCH_PYTHON" -m seed.arc_v3_batch prepare \
  --tasks lab/seed/ARC-AGI/data/evaluation \
  --root lab/seed/arc-v3-public-evaluation/arc1 \
  --label ARC1-public-evaluation --scope public-evaluation \
  --b24-closure /ruta/al/recibo/b24-closed.json
```

Ese comando todavía no se ha ejecutado. La guarda comprueba el cierre antes
de leer las tareas. El recibo debe conservar su colección de archivos B24,
auditoría aritmética y archivo de evidencias; no basta un JSON aislado con
`valid: true`. Se preserva la exposición previa de los corpus públicos:
una nueva ejecución no recupera la condición de examen ciego.
