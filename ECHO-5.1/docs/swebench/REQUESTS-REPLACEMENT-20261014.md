# Requests: enmienda previa a inferencia · 14 de octubre de 2026

Se sustituye **solo `psf__requests-2674` por `psf__requests-2317`** en el panel
primario. Los otros 35 registros, las cuotas, los brazos y las reglas de
verificación permanecen iguales. El contrato sigue en `design`, con lanzamiento
deshabilitado. Esta entrega no ejecuta modelos ni consume GPU.

## Motivo y alcance del diagnóstico

En el Parquet fijado por el contrato, los 12 identificadores F2P de 2674
corresponden a funciones presentes en BASE. Ninguna de las dos funciones de test
añadidas por su `test_patch` aparece en esa lista. El diagnóstico ambiental
independiente obtuvo **`raw_resolved: true` tanto con vacío como con referencia**,
con F2P 12/12 y P2P 142/142 pasando en ambos. Por ello el control negativo es
no discriminante. La conclusión se limita a esa revisión del dataset y al
entorno probado; no supone que cualquier cambio de nombres de tests sea un
defecto, ni que todo SWE-bench resulte inválido.

Se conserva el resultado previo 35/36 y el diagnóstico, sin alterar las listas
F2P/P2P, los tests oficiales ni el parche de referencia. Los nombres y contenidos
de tests reservados no se incorporan al actor ni a sus herramientas.

## Regla registrada antes de comprobar candidatos

La [política](REQUESTS-REPLACEMENT-POLICY-20261014.json) se guardó antes de
los resultados de candidatos, con SHA-256:

`ce5be5957eb30ef10fe8562a52e79c34f3b56c89f8b6dcb7ddff0b7b4b176b17`.

Se toman los IDs de `psf/requests` no presentes en ninguna fase del registro
y se ordenan por la clave original SHA256 `20261013:primary:instance_id`:
**2317, 863, 3362, 1963**. Se acepta el primero que supere el baseline público
y ambos controles oficiales. No se ordenan por acierto de modelos, tokens ni
contenido de soluciones. 2317 fue el primer candidato; no se ejecutaron los
otros tres.

Los errores de infraestructura de ese candidato se conservaron:

1. Primer intento: el digest configurado carecía del prefijo `sha256:`;
   rechazado antes de ejecutar los tests.
2. Segundo: incompatibilidades públicas de pytest y timeout de conexión;
   vacío y referencia fallaron. No se trató como evidencia para saltar al
   siguiente candidato.
3. Tercero, con el mismo entorno corregido para ambos: vacío no resuelve,
   referencia resuelve, evidencia válida en ambos.

El BASE público de 2317 supera 35 tests en las dos ejecuciones de baseline.
La imagen oficial queda fijada a
`sha256:3c49e39da2143fc51599f096a7c959ea5f3c9fd97d22899d977ac92d6dc360b6`.

## Entorno histórico declarado

El BASE público utiliza la API antigua `pytest.raises(..., "código")` y espera
un timeout de conexión contra `10.255.255.1`. Se monta pytest 4.6.11 con sus
bytes fijados, entrypoint compatible, plugins automáticos desactivados y
`--assert=plain`. Las aserciones siguen ejecutándose.

Un dispositivo dummy y una única ruta `10.255.255.1/32` en el namespace privado
producen un timeout real. No hay ruta por defecto ni acceso a internet.
El operador rootless configura el namespace mientras el contenedor está inactivo;
el proceso de tests conserva `cap_drop=ALL`. Se rechaza el namespace del host y
se comprueba la identidad del namespace antes de cada operación. httpbin real
sirve HTTP/TLS por loopback con su CA fijada. No se simulan respuestas de tests.

Dos integraciones reales comprobaron el servicio y el perfil histórico,
incluyendo timeout, API pytest, capacidades nulas y falta de conectividad externa.
El suplemento, su manifiesto y la adaptación rootless se deben conservar para
la evaluación final; no equivale a ejecutar la imagen upstream sin modificaciones.

## Reproducción de la selección

El selector original sigue generando el panel inicial. Sobre esos bytes,
identificados en la política, aplicar esta única enmienda: reemplazar la fila
primaria excluida por los metadatos del primer candidato elegible, adjuntar
`pre_inference_amendments` y recalcular el SHA-256 de `SWE-SAMPLE.json` en el
contrato. El registro v2 sustituye únicamente su entorno correspondiente.
Las copias originales, política, intentos y script de aplicación se conservan
bajo `artifacts/repoworld-requests-replacement-20261014/`.

`replace_failed_instances: false` sigue impidiendo sustituciones futuras durante
la campaña. El registro explícito de esta enmienda anterior a inferencia no es
una autorización para cambiar tareas después de observar rendimiento. Este panel
es una cohorte exploratoria adaptada, no una puntuación oficial sobre las 300
instancias de SWE-bench Lite.

Los resultados de la repetición completa figuran en el
[informe del curador](../REPOWORLD-CURATOR-ALL-20261014.md).
