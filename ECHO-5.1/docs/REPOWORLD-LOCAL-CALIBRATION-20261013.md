# RepoWorld · entrega local de infraestructura (13 de octubre de 2026)

Alcance: tareas 1–3 del [plan](SWE-BENCH-LITE-PLAN-20261013.md) y calibración
local de los cuatro commits reservados para desarrollo. No ejecuta inferencia,
no abre el túnel de Kaggle y no utiliza los tests oficiales reservados.
El contrato científico sigue en `design`, con `launch_enabled: false`.

## Implementación

- `repoworld/types.py` y `dataset.py`: proyección por lista de cuatro campos;
  Parquet lee únicamente esas columnas. Se comprueban hashes, commits, IDs
  duplicados, roster y bloqueo de lanzamientos sin contrato/lock sellados.
- `environment.py`: exporta blobs del commit con `git ls-tree/cat-file`, sin
  ejecutar hooks, filtros, checkout ni código del repositorio en el supervisor.
  No exporta `.git`, archivos locales modificados ni archivos no versionados.
- `pcworld/runner.py`: perfil explícito RepoWorld. BASE y candidato se montan
  de solo lectura; copia ejecutable dentro de un único tmpfs. Conserva cgroup,
  watchdog y terminación de hijos. No monta `/usr` del host ni autoridades.
- `pcworld/snapshots.py`: perfil de streaming con spool privado, límites de
  repositorio propagados al runner y lecturas acotadas. Conserva las identidades
  y el comportamiento predeterminado de PCWorld.
- `workspace.py`: unified diff estricto, sin fuzz, escaladas de modo, binarios,
  traversal ni edición de tests protegidos; máximo 64 KiB, ocho archivos y
  800 líneas cambiadas por propuesta. La exportación acumulada admite 512 KiB,
  64 archivos y 6.400 líneas; se comprueba antes de admitir cada propuesta.
  Stage no mueve el candidato retenido. La retención usa
  CAS, recibos públicos y recuperación de intención/recibo/puntero.
- `tools.py`: búsqueda literal con rg, lectura hasta 100 líneas, paginación
  UTF-8 incluso dentro de líneas largas y cursores autenticados ligados al
  snapshot y la consulta. Respuestas ≤8 KiB/1.000 tokens. Sin tokenizer de modelo
  se usa una cota conservadora de bytes UTF-8, no una medición de tokens Qwen.
  `test_run` solo acepta identificadores de checks registrados por el supervisor;
  no acepta comandos proporcionados por el agente. Los errores también consumen presupuesto y dejan recibo;
  se contabilizan CPU del supervisor, hijos de herramientas y cgroup candidato.

Los artefactos del candidato y sus salidas siguen etiquetados como datos no
fiables. Un código de salida cero no equivale a resolver un issue. Retener un
candidato requiere un recibo de propiedad pública emitido por el supervisor;
la semántica completa del guardarraíl de regresión pertenece a la tarea 4.
La recuperación cubre snapshots y recibos; reabrir un workspace todavía crea
un presupuesto nuevo. No sirve para reanudar episodios científicos: la
contabilidad persistente y la orquestación de la tarea 8 siguen pendientes.

## Calibración y evidencia

Las sondas cubren aislamiento, timeout con hijos, CPU, memoria, PIDs, tmpfs y
salida acotada. También ejercitan lectura, búsqueda, staging, retención y el
roundtrip de un cambio de texto neutro. Ese cambio **no es un arreglo del bug**.
Se reutilizan `EpisodeMemory`, CAM/WSP16, recibos y `thought.jsonl` existentes.

**Resultado final: 4/4 calibraciones de infraestructura válidas, 28/28 sondas,
cuatro transacciones de parche y 56 recibos autenticados comprobados de nuevo.**
La auditoría local reproduce los predicados desde las observaciones, los hashes
base/candidato, la exportación del diff y `thought.jsonl`/CAM (`destroyed == 0`).
No es la auditoría científica independiente del futuro evaluador oficial.

| Commit de calibración | Archivos | Tamaño del árbol | Duración del episodio | Pico cgroup en sonda normal |
|---|---:|---:|---:|---:|
| `pallets__flask-4992` | 250 | 1.50 MiB | 9.86 s | 25.12 MiB |
| `psf__requests-2148` | 128 | 1.45 MiB | 9.15 s | 24.37 MiB |
| `pytest-dev__pytest-7168` | 484 | 3.37 MiB | 11.92 s | 27.70 MiB |
| `sympy__sympy-19007` | 1760 | 30.63 MiB | 26.48 s | 59.35 MiB |

Los episodios sumaron 57,41 segundos, incluyendo su preparación medida. El pico
del supervisor completo fue 243.700 KiB (incluye ingesta Parquet); no se confunde
con la memoria del proceso candidato. `MemoryPeak` es memoria del cgroup, no RSS.
Las sondas de memoria, CPU, salida y timeout provocan agotamientos deliberados;
el pase significa que el límite actuó y no quedaron hijos, no que resolvieran
el issue. El watchdog de CPU se muestrea cada 50 ms y puede registrar exceso
sobre el umbral antes de terminar el grupo.

**Pruebas:** 35 RepoWorld, 255 regresiones PCWorld y 13 de diseño/análisis:
303 aprobadas. La revisión independiente detectó y permitió corregir dos fallos:
expansión por escapes JSON en la paginación y límite acumulado de exportación.
Ambos tienen regresiones que fallaron antes de la corrección y pasan después.

[Manifiesto compacto de verificación](swebench/LOCAL-INFRA-VERIFICATION.json).
Recibos y autoridades permanecen locales en
`ECHO-5.1/artifacts/repoworld-local-calibration-20261013/run3/`.
No se publican claves ni se ha hecho push.

Trazabilidad de desarrollo: r1 falló antes de ejecutar issues porque `python -I`
no veía `pyarrow` instalado en el entorno del supervisor. r2 pasó las cuatro
calibraciones; después se añadieron el auditor y las correcciones de revisión.
r3 repitió los cuatro casos con las fuentes finales congeladas y pasó la auditoría.
Se conservan los intentos anteriores; no hubo selección de casos por resultado.


## Reproducción local

El lector Parquet necesita `pyarrow==24.0.0`, y la validación de herramientas
necesita `jsonschema==4.23.0` en el entorno del supervisor; véase
[el archivo de dependencias](swebench/requirements-repoworld-local.txt). No forman parte del rootfs del
candidato. La preparación del Python exporta bytes fijados; no se afirma que
reconstruirlo desde cualquier host produzca una imagen idéntica.

```sh
python3 ECHO-5.1/scripts/run_repoworld.py test
python3 -I -B ECHO-5.1/scripts/run.py test
python3 ECHO-5.1/scripts/run_repoworld.py calibrate-local \
  --dataset /tmp/echo51-swe-test.parquet \
  --runtime ECHO-5.1/artifacts/runtime-python314-20261013 \
  --sources ECHO-5.1/artifacts/repoworld-local-calibration-20261013/sources \
  --output ECHO-5.1/artifacts/repoworld-local-calibration-20261013/reproduction
python3 ECHO-5.1/scripts/run_repoworld.py audit-local \
  ECHO-5.1/artifacts/repoworld-local-calibration-20261013/reproduction
```

El directorio de salida debe ser nuevo. `sources/<instance_id>` contiene un
repositorio Git del commit exacto registrado; no se hacen descargas implícitas
ni ejecución de instaladores dentro del supervisor. La auditoría de campañas
PCWorld históricas usa su commit congelado, no las fuentes cambiadas aquí.

## Qué sigue pendiente

- Imágenes online con las dependencias propias de los cuatro repositorios y
  preflight de compatibilidad. El rootfs utilizado ahora contiene solo stdlib:
  **no acredita ejecutar las suites reales de Flask, Requests, pytest o SymPy**.
- Adaptador de checks públicos, colección estable, regresiones y namespace de
  sondeos del crítico (tarea 4). `purpose=probe` se rechaza mientras no exista.
- Proveedor/prompts de repositorios, brazos S/I2/F/E y su contabilidad completa.
- Memoria con procedencia y publicación por evidencia pública, sin consultar el
  resultado final del donante.
- Evaluador oficial separado, auditoría integral, lock y campañas independientes.
- Confirmación de H1–H4. Esta entrega no cierra ECHO-5.1 ni demuestra ventaja
  sobre un agente único.
