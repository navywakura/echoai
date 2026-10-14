# RepoWorld · controles oficiales · 14 de octubre de 2026

## Resultado final de infraestructura

**36/36 controles oficiales válidos y 36/36 baselines públicos válidos**, tras
sustituir únicamente `psf__requests-2674` por `psf__requests-2317` mediante una
regla registrada antes de comprobar candidatos. Los otros 35 registros no cambian.
Se repitió el catálogo completo con las fuentes finales; el agregado no reutiliza
los 35 pases de la versión anterior como si pertenecieran al código nuevo.

**420 pruebas de software pasadas y tres integraciones reales pasadas aparte.**
El smoke verifica regresión, rollback y replay con proveedor simulado. Las firmas
y los hashes de los 72 logs vacío/referencia se comprobaron de nuevo.
**0 horas nuevas de GPU y 0 llamadas reales al LLM del experimento.** Las llamadas
contabilizadas en el smoke corresponden a un proveedor simulado (`is_llm: false`).

El contrato sigue en `design`, `launch_enabled: false`. Está preparada la
calibración remota de una instancia reservada, pero **no se ha ejecutado Gate 3,
no existe un lock científico habilitado y ECHO-5.1 no queda científicamente cerrado**.

## Sustitución y procedencia

El resultado previo fue 35/36: tras recuperar Seaborn de un contenedor residual,
2674 seguía sin control negativo discriminante. En el diagnóstico con el entorno
corregido, tanto vacío como referencia obtuvieron `raw_resolved: true`, con los
12 F2P y 142 P2P pasando. En la revisión fijada del Parquet, esos 12 F2P ya estaban
en BASE y ninguna de las dos funciones añadidas por `test_patch` figuraba entre ellos.
Se conserva ese resultado, sin modificar el oráculo para convertirlo en pase.

La autorización del usuario permite una enmienda antes de inferencia. La
[política preregistrada](swebench/REQUESTS-REPLACEMENT-POLICY-20261014.json) aplica
el orden original de metadatos SHA256 a los candidatos no utilizados:
2317 → 863 → 3362 → 1963. **2317, el primero, resultó elegible**; no se probaron
los otros tres. La [justificación y reproducción](swebench/REQUESTS-REPLACEMENT-20261014.md)
conserva intentos, correcciones ambientales, hashes originales y alcance.

| Nueva instancia | Vacío | Referencia | Evidencia |
|---|---|---|---|
| `psf__requests-2317` | `raw_resolved: false` | `raw_resolved: true` | Ambos controles válidos |

La muestra continúa con 24 primarias, cuatro de calibración y ocho de memoria,
36 identidades distintas. `replace_failed_instances: false` permanece vigente
para la campaña. Esta es una cohorte exploratoria enmendada, no un resultado sobre
las 300 tareas originales ni una selección por aciertos de los agentes.

## Recuperación y entorno reproducible

El balance autorizado de Btrfs reubicó dos grupos y amplió metadatos de 7 a
7,5 GiB. Se comprobaron escrituras y creación de contenedores antes de continuar.
No se necesitaron nuevas operaciones sudo. El API propio de Podman rootless usa
`--storage-opt overlay.ignore_chown_errors=true` para los UID/GID de qhull fuera
del rango subordinado. Se conservan contenidos y digest, pero se declara esta
adaptación de propietarios; no equivale a reproducir UID rootful. No se cambia
la configuración global de Podman ni se poda el almacén del usuario.

Las imágenes se adquieren secuencialmente; solo se descartan automáticamente las
que el propio curador acaba de adquirir. El perfil de Pytest-7168 conserva fallos
explícitos evitando un crash de presentación del traceback.

Requests usa httpbin real por loopback con HTTP/TLS. Para 2317 se fija además
pytest 4.6.11, su entrypoint y dependencias de solo lectura, sin plugins automáticos,
con `--assert=plain`. El BASE requiere esa API histórica. Una única ruta dummy
`10.255.255.1/32`, dentro del namespace aislado, reproduce el timeout esperado.
No hay ruta por defecto, internet ni capacidades administrativas para los tests.
El código no modifica tests, F2P/P2P ni parches de referencia. El perfil completo
queda fijado por hash y debe ser el mismo en la evaluación final.

## Verificación final

| Comprobación | Resultado |
|---|---|
| Suite RepoWorld | 150 pasadas; tres integraciones omitidas en esta invocación |
| Suite PCWorld | 257 pasadas |
| Herramientas de diseño | 13 pasadas |
| Integraciones reales separadas | 3/3: HTTP/TLS, perfil histórico y presentación de Pytest |
| Preflight público | 36/36 baselines válidos, dos ejecuciones por instancia |
| Curador oficial | 36/36, vacío negativo y referencia positiva, 72 logs verificados |
| Smoke y auditoría | Regresión bloqueada, rollback y replay idéntico, recibos válidos |
| Revisión independiente del cambio | Sin hallazgos accionables |
| Preparación local de Gate 3 | Supera las comprobaciones hasta la construcción del proveedor, interceptada sin red |

Los skips de tests públicos, cuando existen, permanecen declarados en los recibos;
no se contabilizan como pases. El ensayo offline de Gate 3 **no constituye una
calibración remota**: intercepta el proveedor antes de construirlo y no genera
un recibo `remote-calibration`.

Evidencia privada: `ECHO-5.1/artifacts/repoworld-requests-replacement-20261014/`:
`software/`, `preflight/`, `smoke/`, `official-controls/`, `final-evidence-audit.json`,
`registry.json`, perfiles y tres intentos del candidato. Los gates están en rutas
persistentes del worktree; sus autoridades HMAC siguen vinculadas a esas rutas.
No moverlas ni editar autoridades. No publicar claves, tests reservados, parches
de referencia ni contenido privado de los contenedores.

El [manifiesto público final](swebench/REPOWORLD-CURATOR-COMPLETE-20261014.json)
solo exporta identidades, cantidades, resultados y hashes. El
[manifiesto anterior 35/36](swebench/REPOWORLD-CURATOR-PROGRESS-20261014.json)
sigue disponible como registro histórico de las fuentes anteriores. Sus gates
no habilitan la calibración bajo las fuentes actuales.

## Checklist de esta entrega

- [x] Conservar el diagnóstico de 2674 y predeclarar una sustitución única.
- [x] Validar 2317 sin cambiar tests ni oráculos; conservar los intentos fallidos.
- [x] Actualizar muestra, hash del contrato y registro v2; otros 35 registros intactos.
- [x] Repetir software, integraciones, preflight 36/36, smoke y controles oficiales 36/36.
- [x] Verificar firmas, hashes y correspondencia con las fuentes finales.
- [x] Dejar preparado el comando y la parada de calibración remota.
- [x] Mantener 0 GPU / 0 LLM reales; entrega local sin push.
- [ ] Ejecutar Gate 3 en una instancia reservada, comprobar cuota y parada del worker.
- [ ] Revisar y sellar el lock antes de la campaña.
- [ ] Campaña, evaluación independiente, gráficas medidas y cierre científico de ECHO-5.1.

[Procedimiento de Gate 3](REPOWORLD-REMOTE-CALIBRATION.md). Diez minutos es un
objetivo de inferencia; descargar y cargar el modelo también consume cuota GPU.
