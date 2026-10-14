# RepoWorld: cursores, diagnóstico de diff y lectura de rescate

Base: `12dec48`, rama local `research/echo-5.1-pcworld1`.
Esta entrega es local: cero llamadas LLM y cero GPU.

## Cambios

1. Los cursores con HMAC válido pero asociados a otra herramienta, consulta o
   snapshot reinician la paginación con los argumentos explícitos actuales.
   Un recibo `repoworld.cursor-reset` registra el reinicio. Se siguen validando
   esquema, capacidad del snapshot, ruta y firma; un cursor falsificado no se
   convierte en una autorización. La continuación de una consulta idéntica se
   conserva.
2. Un mismatch informa de línea, texto real y texto del hunk. Al final del
   archivo muestra `<EOF>`. Cada fragmento se acota a 240 bytes UTF-8 antes de
   formatear y el feedback pasa por el sanitizador existente. El parche sigue
   rechazado sin fuzz ni mutación parcial.
3. `PatchFormatError` identifica errores de sintaxis/contexto y se serializa
   como `ValueError` con `code=PATCH_FORMAT_ERROR`. No se infiere la categoría
   desde texto del archivo ni del modelo. El siguiente turno recibe el detalle.
4. Tras ese rechazo se habilitan dos `file_view` adicionales una vez agotadas
   las cuatro llamadas de localización. La tercera lectura se rechaza; búsquedas
   e `issue_page` no reciben cuota adicional. Intentos fallidos de lectura de
   rescate también consumen su cupo. El contador forma parte del checkpoint y
   el prompt muestra `rescue_reads_left`. Cada nuevo intento de parche sustituye
   el cupo previo; nunca lo acumula.
5. Se elimina el reinicio indiscriminado de localización tras un parche fallido.
   Un parche retenido sí conserva el reinicio para la siguiente fase. Las mismas
   herramientas y reglas presupuestarias se aplican a todos los brazos, incluida
   la autorreparación del control S; no se concede una ventaja de interfaz solo a E.

No cambian la protección de tests, el aislamiento, los límites globales de
herramientas/LLM/parches ni el criterio de retención por checks públicos. Una
lectura de rescate no convierte un candidato en solución verificada.

## Verificación

Se reprodujeron primero fallos en las pruebas de cursores y feedback. El mock
consume cuatro lecturas, propone contexto erróneo, recibe la línea real, utiliza
dos lecturas de rescate, comprueba el rechazo de la tercera y aplica el diff
corregido. El resultado contiene el cambio esperado, dos intentos de parche
facturados y cero reservas pendientes. Es una prueba de protocolo con checks
públicos sintéticos, no una nueva ejecución del modelo ni resolución SWE-bench.

Se comprueban además cursores entre herramientas y snapshots, firma falsificada,
continuación UTF-8, EOF, tamaño del diagnóstico y ausencia de mutación del árbol.
La suite completa y su recibo se guardan en
`artifacts/repoworld-usability-20261014/software/`.

## Consecuencia para el sellado

Las fuentes cambiaron. El lock y las cinco compuertas anteriores siguen siendo
la evidencia histórica de la calibración anterior; no autorizan una campaña con
este código. Antes de otra campaña deben renovarse las compuertas aplicables,
repetir la calibración remota y generar un nuevo sellado. No se editan ni se
recalifican los artefactos anteriores. La mejora del 32B queda por medir.

## Resultado final de la suite

`run_repoworld.py verify` terminó con `valid=true` y
`source_unchanged=true`: RepoWorld 156 casos (153 pasados y 3 integraciones
opcionales omitidas), PCWorld 257/257 y diseño 13/13. Total: **423 pasados,
3 omitidos, cero fallos**. Las integraciones opcionales del curador no se
reejecutaron; esta entrega no regenera los controles oficiales de 36 instancias.
`git diff --check` también pasó. No se hizo push ni se inició Kaggle.
