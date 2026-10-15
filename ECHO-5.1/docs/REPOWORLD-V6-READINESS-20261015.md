# RepoWorld V6 — lectura completa y transiciones verificables

Continuación local tras V5 (`66c2bec`, informe `e7fa597`). V5 se conserva como
fallo funcional: búsqueda arreglada, dos parches aplicados, reversión a diff
vacío, crítico agotado; 208 recibos válidos y 21,62 h GPU restantes al apagar.

## Corrección derivada de V5

`source_evidence` añade una comprobación estructural a las vistas autenticadas.
Para Python con funciones, un locus está listo solo si las líneas de una
función que intersecta la vista están completamente observadas bajo el mismo
hash. Las vistas se unen por número de línea; un cambio de contenido invalida
la evidencia anterior. Los rangos AST solo orientan la lectura: no demuestran
que esa función cause el bug. Fuentes sin funciones conservan un locus de
líneas observadas; no se describe como función completa.

Una vista parcial obtiene `locus.next_view` con el rango que falta. `finish`
no entrega al editor ese locus parcial; `finish(abandon=true)` permite abandonar.
Tampoco se permite que el localizador eluda el bloqueo enviando directamente
una edición. Al alcanzar los límites sin un locus completo se abandona.

Un parche retenido pasa al crítico aunque el cambio de hash invalide las vistas
anteriores. Restaurar el código base devuelve el control al editor con
`base_restored=true`, sin afirmar que exista una solución. Los cursores inventados
siguen rechazándose; el feedback y el prompt indican `cursor=null` para lecturas
nuevas. No cambian cuotas, tests ocultos, selección de issues ni comparadores.
El umbral de 8.000 tokens del localizador se comprueba entre llamadas, como en
la revisión anterior; no se presenta como un techo estricto por generación.

## Evidencia offline y custodia

Raíz: `ECHO-5.1/artifacts/repoworld-gates-v6-20261015/`.
Cinco pruebas nuevas reproducen lectura parcial, edición prematura, traspaso
tras retención, reversión y cobertura ligada al hash. Una sexta cubre feedback
de cursores inválidos. Las seis fallan antes de las correcciones; 49 pruebas
focalizadas pasan después. El primer intento verde tuvo un error en el recibo
del fixture (no en el runner); se corrigió el fixture para usar la propiedad
pública que exige `Workspace.retain`.

Verify completo: **455 pruebas pasadas, 3 omitidas**, sin fallos en esta ejecución.
Smoke válido, rollback y replay idéntico; preflight 36/36 y controles oficiales
36/36 reatestados con la misma comprobación de hashes/procedencia que V5,
sin reejecutar sus suites originales. Frontera offline y `operate.py check`
válidos, cero GPU/LLM durante esta renovación. El smoke usa `smoke-actions.json`, con
un `finish` explícito tras observar la función; sigue siendo una transacción
sintética que provoca regresión y rollback sobre tests públicos reales, no una
solución de SymPy. V5 no se reutiliza como pase funcional de este código.

## Criterio para continuar

Una calibración nueva debe leer `_entry` completo, entregar presupuesto suficiente,
aplicar y retener una edición del método y superar los checks públicos registrados.
El assessment usa solo recibos y fuente pública; no consulta el oráculo reservado.
Los 22 checks de `test_basic.py` no constituyen cobertura de BlockMatrix ni prueban
la solución del issue. Cualquier resultado oficial requiere el harness separado.
Sin ese pase funcional no se sella el contrato ni se inicia la campaña.

## Calibración real y sello

V6 supera el assessment funcional: búsqueda, vista completa L235–247 antes de
traspasar, **17.939 tokens disponibles al entrar el editor**, edición del método
retenida y checks públicos pasados. Finaliza `budget_stopped` con 23.757 tokens,
15 llamadas LLM, seis intentos de parche (dos aplicados, cuatro rechazados),
cuatro ejecuciones de checks y 248 recibos válidos. Contabilidad completa,
`destroyed=0`, reservas pendientes=0. No hay resultado oficial del issue.

Kernel privado `rogeernavarro/echo51-repoworld-locus-v6-20261015`, versión 1:
COMPLETE, 65/65 capas en 2 T4, preparación 382,749 s y total 739,113 s.
Worker parado, cero errores; relay y túnel apagados al concluir V6.
Cuota observada: 21,62 → **21,41 h**. V5 y V6 consumieron aproximadamente
0,39 h conjuntamente, según el contador de Kaggle redondeado a centésimas.

El contrato **operativo** está en `remote/sealed/SWE-CONTRACT.json`, con
`status=sealed`, `launch_enabled=true`. El archivo de diseño en `docs/` se
conserva como entrada. Lock: `remote/sealed/SWE-RUN-LOCK.json`, SHA-256
`4d3e92b45067c6ce76a5408c7fd2524b37d6abf1a6e92af28c656ebd08517a49`.
Las cinco compuertas y el manifiesto del código quedan autenticados por el sello.

La campaña preparada conserva 150 celdas: 16 de calibración, 96 principales,
24 E_no_guard, dos donantes y 12 receptores de memoria. Son 36 IDs distintos;
solo los 24 IDs principales entran a la comparación S/I2/F/E. I2 mantiene dos
propuestas independientes y selector. No se reclasifican las calibraciones como
resultados primarios. `campaign_driver.py` ejecuta fases, apaga cada worker,
congela todas las entregas, llama al curador y genera export/gráficas. Sus topes
son límites de gasto, no garantías de completar todas las celdas; las no iniciadas
por falta de presupuesto permanecen en el denominador.

## Observaciones durante la campaña sellada

La celda de calibración `140446d796d7abc783327a445434f989` (Flask-4992,
brazo S) agotó 24 llamadas y entregó un diff vacío con 23.960 tokens y cero
reservas pendientes. El resultado conserva `status=active`: el bucle termina
por `max_calls` sin actualizar esa etiqueta, aunque el recibo `branch-frozen`
y la entrega final existen. Es un defecto de clasificación terminal que se
debe corregir en una revisión posterior; no se modifica el código sellado.
La auditoría/evaluación usa la entrega congelada y no considera `active` una
resolución. Los recibos muestran búsquedas repetidas de la ruta inexistente
`flask/config.py`; no hubo un fallo del relay en esa celda. No se relanza ni
se elimina ese resultado.

El lote V6 cerró 11 episodios de calibración y dejó cinco `not_started` por
el límite registrado de tiempo. Worker COMPLETE, 2.259,909 s, cuota
21,41 → 20,78 h. Antes de iniciar el panel primario, el empaquetador rechazó
un timeout de 22.500 s: admite hasta 9.000 s y el relay hasta 8.400 s.
El intento de arranque primario no encendió ninguna GPU. Relay y túnel locales
quedaron apagados. No hubo episodios primarios ni evaluación del oráculo final.
`partial-custody-audit.json` autentica las 11 entregas: 1.880 recibos,
180.976 tokens y cero reservas pendientes. Es una auditoría de custodia parcial,
no una evaluación SWE-bench ni una congelación completa del calendario.

Se conserva este estudio parcial y su lock original. La corrección de sesiones
acotadas cambia el manifiesto y requiere compuertas/sello nuevos; los resultados
V6 no se trasladan al panel primario ni se reescriben. Continuación:
[V7 por lotes](REPOWORLD-V7-BATCHES-20261015.md).
