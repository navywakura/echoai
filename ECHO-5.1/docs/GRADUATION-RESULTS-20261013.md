# Evaluación común con 14B · resultados de desarrollo

**E=3/3, F=3/3, S=2/3 e I2=2/3.** Registros distingue los flujos con
crítica y reparación de los controles en esta ejecución. E no supera a F.
Es una mejora observada en tres tareas conocidas, no una confirmación
independiente ni el cierre científico de ECHO-5.1.

Rama local `research/echo-5.1-pcworld1`, implementación `322d0ab`, contrato
`0.6.0-development`, [plan previo](GRADUATION-PILOT-20261013.md).
Sin publicación ni push. Los nueve archivos del manifiesto congelado conservan
sus hashes después de la ejecución. No se cambió el ensayo durante la medición.

## Matriz y coste

Mismas variantes conocidas `repair-v2`, semilla 47, doce episodios en orden
contrabalanceado y Qwen2.5-Coder-14B-Instruct Q4_K_M. Por episodio: 25.000 tokens,
50 herramientas, 12 llamadas LLM, seis críticas, 128 fuel, 300 s CPU y 900 s de
plazo. Modelo, runtime y oráculos conservados respecto al piloto anterior.

| Brazo | Registros | Rutas | Paginación | Aceptadas | Tokens observados | Herramientas | Tiempo de episodios |
|---|---:|---:|---:|---:|---:|---:|---:|
| S | 2/4 | 4/4 | 5/5 | 2/3 | 5.210 | 58 | 150,622 s |
| I2 | 2/4 | 4/4 | 5/5 | 2/3 | 2.352 | 59 | 71,762 s |
| F | 4/4 | 4/4 | 5/5 | 3/3 | 16.049 | 104 | 162,653 s |
| E | 4/4 | 4/4 | 5/5 | 3/3 | 16.174 | 107 | 163,579 s |

Las celdas de familia cuentan solo casos comunes públicos/finales; F y E
también pasan el contraejemplo adicional de Registros, obteniendo 5/5 en sus
recibos finales completos. No se comparan denominadores de distinta dificultad.
Total: 39.785 tokens observados y 43 llamadas LLM, sin uso desconocido cobrado.
E gasta 125 tokens más que F (aproximadamente 0,78 %) con la misma aceptación.
S e I2 son más baratos y fallan una tarea más. No hay dominancia de E en coste.

## Evidencia del mecanismo

**Registros:** S e I2 conservan el error de escoger el último valor de una clave
repetida y fallan dos casos comunes. S tiene revisión propia e I2 dos propuestas;
este resultado no prueba que sean incapaces de reparar en general.

E encuentra una refutación en `duplicate-keys`, repara en un intento, reproduce
el testigo sobre el parche y pasa `empty-singleton` con `[]`. F pasa primero
`empty-singleton`, encuentra la refutación en `first-occurrence-order`, repara
en un intento y reproduce ambos sondeos sobre el parche. Cada uno supera todos
sus casos finales. No hubo sondeos inválidos ni duplicados en estos episodios.
E consume 4.153 tokens; F, 2.952. El crítico sí descubre aquí un defecto real.

**Rutas:** ambos flujos con crítico reparan en un intento el fallo inicial del
ejemplo público, igual que en el piloto anterior. El descubrimiento de ese
defecto no corresponde al crítico. Después completan `dotdot-cancellation` y
`root-boundary`, con tres sondeos duplicados descartados en E y cuatro en F.
E consume 9.618 tokens y F 10.795. Los cuatro brazos pasan los casos finales.

**Paginación:** todos pasan sin reparación guardada. E consume 2.403 tokens y
F 2.302, frente a 1.089 de S y 762 de I2. La coordinación no añade aciertos aquí.

## Qué cambió y qué quedó comprobado

La aceptación final ahora usa el mismo criterio para los cuatro brazos:
completar todos los casos requeridos dentro del presupuesto. La cobertura del
crítico sigue en los recibos, pero no bloquea por sí sola la evaluación. Se
comprueba la cuota antes de cada reintento, sin reservar una séptima crítica.
El prompt exige explícitamente cero o un elemento en `empty-singleton`; el
ejemplo de Registros usa `value`, conforme al contrato, no `val`.

`GRADUADO_POR_SUPERVIVENCIA` únicamente significa candidato reparado listo para
evaluar, con `verified: false`. No encontrar otra refutación no prueba corrección.
Las pruebas de software comprueban tanto su paso a evaluación como el rechazo
posterior si falla un caso final, además de la parada por cuota de ambos brazos.

**Ningún episodio GPU de esta tanda necesitó esa graduación por cobertura
incompleta:** E y F consiguieron dos categorías en las tres tareas. Por tanto,
el resultado no demuestra que la regla de graduación causara la mejora. Cambian
conjuntamente prompt y protocolo; falta una ablación para atribuir el efecto.
La mejora tampoco aísla la contribución de CAM frente a retener los mismos
testigos mediante otra implementación.

El [piloto 0.5](TWO-GATE-RESULTS-20261013.md) permanece 2/3 en todos los brazos
bajo sus reglas originales. Sus candidatos de Registros no se reevaluaron para
subir retrospectivamente la puntuación. Esta es una ejecución nueva y distinta.

## Verificación e infraestructura

- 202 pruebas PCWorld pasan en 77,333 s. Incluyen regresiones, oráculos intactos,
  candidatos graduados pero incorrectos, aceptación común y cuotas del crítico.
- 12/12 episodios terminados; 619 recibos válidos en la auditoría automática y
  su repetición explícita. Sin discrepancias, errores de episodio, timeouts ni
  destrucción de memoria (`destroyed == 0`). Alcance finito, no prueba universal.
- Notebook privado `rogeernavarro/echo51-graduation14b-20261013`, versión 1,
  estado `COMPLETE`. Kaggle solo ejecuta inferencia; candidatos y oráculos se
  ejecutan localmente bajo Bubblewrap/cgroups con el rootfs fijado.
- 49/49 capas en GPU, 9.161 MiB en CUDA0 y 105 MiB en la segunda T4 al cargar.
  Preparación: 207,393 s; worker completo: 759,356 s, unos 12 min 39 s.
- 129 solicitudes de transporte, todas HTTP 200: plantilla, tokenización y
  generación para 43 llamadas. Worker detenido normalmente; supervisor,
  broker y túnel comprobados inactivos.
- Cuota observada: 25,54 → 25,33 horas GPU restantes, unos 0,21 h por la
  resolución del contador. No es una medición de consumo eléctrico.

## Artefactos y reproducción

- `ECHO-5.1/artifacts/graduation14b-pilot-20261013/`: recibos, snapshots,
  resultados, fuentes, tareas, contrato, auditoría y `summary-by-arm.json`.
- `ECHO-5.1/artifacts/graduation-control-20261013/`: manifiesto congelado,
  GPU lista y log de transporte. Contiene credenciales privadas; no publicar.
- `ECHO-5.1/artifacts/kaggle-graduation14b-output/`: informe y logs del worker.
  Su input contiene una credencial efímera del transporte ya apagado; no publicar.
- SHA-256 de `result.json`:
  `f3d108e2944906097ea2f0820b1f4d8931186edc535b0e15d4612f702f5e9aea`.
- SHA-256 de `audit.json`:
  `3d7ee4f44e31ed844c21b2033a506988d868ff68759b2e2aad6902504649819e`.

Auditoría sin volver a ejecutar candidatos:

```sh
python3 -I -B ECHO-5.1/scripts/run.py audit ECHO-5.1/artifacts/graduation14b-pilot-20261013
```

Se resuelve el bloqueo de protocolo y se observa reparación útil. Para cerrar
la hipótesis de ventaja de ECHO faltan nuevas familias reservadas, repeticiones
dimensionadas y ablaciones de crítico, memoria y router a presupuesto comparable.
No se lanzó otra campaña para buscar un marcador más favorable. S6 sigue aplazado.
