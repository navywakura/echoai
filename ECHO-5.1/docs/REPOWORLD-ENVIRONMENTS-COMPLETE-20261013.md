# RepoWorld: completar entornos locales (Opción B)

Continuación de `9e4fde0`, iniciada el 13 y continuada el 14 de octubre de
2026, en `research/echo-5.1-pcworld1`. **Gate 1 local: 36/36, 12/12 repositorios;
cuatro controles oficiales de calibración válidos.** Contrato científico en
`design`, sin inferencia ni GPU en esta preparación. Sin push.

## Alcance y fronteras

Se conservan las 36 instancias registradas y los 12 repositorios. Un pase
del preflight certifica dos ejecuciones iguales del alcance público declarado
para ese commit. No equivale a resolver un issue, ejecutar toda la suite del
repositorio ni obtener una puntuación en SWE-bench Lite.

El curador dispone ahora de `--scope calibration`: comprueba cuatro controles
reservados y produce `official-calibration-controls`. Ese recibo no satisface
el gate `official-controls` de las 36 instancias exigido por el sellado
completo. No se ha reducido silenciosamente la cohorte a los repositorios
que resulten más fáciles de preparar.

## Cambios de infraestructura

- Enlaces Git relativos internos preservados, incluidos sus destinos y modos
  en el manifiesto. Se rechazan escapes, destinos ausentes, ciclos y enlaces
  absolutos. El perfil predeterminado de PCWorld sigue rechazando enlaces;
  la ampliación es explícita para RepoWorld.
- Las copias de ejecución conservan los enlaces, sin aplanar fixtures. Los
  tests y sus destinos transitivos continúan protegidos por montajes de solo
  lectura. Se comprueba la misma clausura de enlaces al admitir un parche y
  al ejecutar, incluidos alias nativos sin suplemento. También se congela
  la carpeta real de cada alias protegido, incluido el primero de la cadena,
  para impedir reemplazarlo. Esa carpeta queda fuera del área editable; si
  sería necesario congelar la raíz completa, el perfil se rechaza.
- Un montaje de archivo de solo lectura no basta si su carpeta puede moverse.
  RepoWorld aplica Landlock antes de ejecutar al candidato: impide mover o
  borrar carpetas fuera del área temporal y rechaza colisiones del repositorio
  con los cuatro directorios reservados. El perfil requiere Linux con Landlock
  ABI ≥ 2 y falla cerrado si falta; no modifica el perfil legacy de PCWorld.
  Referencia: [documentación del kernel](https://docs.kernel.org/userspace-api/landlock.html).
- Los semáforos POSIX utilizan `/dev/shm` dentro de la misma cuota de `/work`.
  El árbol de dispositivos es mínimo y de solo lectura; no se monta el
  `/dev/shm` del host. El techo de disco se reparte en `/work` (75 %) y `/tmp`
  (25 %), redondeado hacia abajo a páginas; la suma no supera el presupuesto.
  `/tmp` queda fuera de la ascendencia del repositorio: las pruebas temporales
  de Pytest no heredan accidentalmente su `tox.ini`. No se inyectan filtros
  de warnings ni se modifican tests para obtener ese aislamiento.
- Suplementos generados ligados a BASE: commit, snapshot, inventario de
  archivos, hashes, metadatos de build y entradas nativas. No pueden
  sobrescribir archivos fuente originales. La admisión no ejecuta los
  archivos recibidos en el supervisor.
- Los parches de C/Cython y de entradas congeladas del build requieren una
  reconstrucción que este perfil todavía no ofrece. Se rechazan, evitando
  probar un parche con una extensión nativa antigua. Esta limitación del
  espacio de acciones afecta por igual a todos los brazos.
- El catálogo de Matplotlib incluye su raíz `lib`; el de Pylint utiliza la
  ubicación pública correcta de sus tests.
- Se corrigió una carrera en el arranque de unidades systemd: una unidad
  todavía no registrada no se considera terminada. La cancelación recoge el
  proceso frontal antes de parar la unidad, comprueba registros tardíos y
  rechaza certificar una limpieza que no haya podido observar.

## Correcciones finales de integración

- El XML de resultados admite hasta 512 KiB; este artefacto queda en el
  supervisor. La salida que recibe el modelo sigue limitada a 40 líneas y
  1.500 bytes. Los tests de Pytest que generan informes grandes dejan de
  perder evidencia por el anterior límite de 64 KiB.
- Hasta 128 objetivos públicos y 16 KiB de nombres, con espacio para flags
  del ejecutor (256 argumentos en RepoWorld; 128 en el perfil legacy).
- El perfil público v1 sigue rechazando omisiones. El perfil v2 permite
  únicamente identidades y motivos de omisión declarados exactamente en el
  plan del operador; no se contabilizan como pases. Las dos ejecuciones
  deben coincidir y contener algún test que pase. La misma política se
  aplica al arranque, a los parches y al restaurar un checkpoint.
- Astropy se recompiló usando NumPy 1.25.2, acorde con su runtime, con
  inventario BASE intacto. Se conservan los intentos anteriores y sus
  advertencias como evidencia de desarrollo.
- Requests-2148 utiliza httpbin y gunicorn fijados en loopback dentro del
  contenedor sin red externa, incluidos HTTPS y redirecciones. No se
  sustituyen tests por respuestas predeterminadas.
- En el curador de pytest-7168, el perfil fijado `--tb=no` evita un fallo
  del código BASE al renderizar el traceback. Conserva las aserciones,
  estados y criterios del harness. El perfil y la imagen quedan ligados al
  lock, igual que el servicio de Requests.

## Verificación

- **Gate 1: 36/36 instancias válidas, 12/12 repositorios**, dos ejecuciones
  públicas coincidentes por instancia, con fuentes congeladas.
- **Gate 2:** smoke real de SymPy con proveedor simulado válido, rollback
  observado y replay idéntico. Auditoría: 68 recibos, dos propuestas y una
  regresión bloqueada; sin presupuesto pendiente. El parche final es una
  modificación neutra de la fixture, no una solución al issue.
- **Controles oficiales de calibración: 4/4 válidos**, con parche vacío
  rechazado y referencia aceptada en Flask-4992, Requests-2148, Pytest-7168
  y SymPy-19007. Fuentes sin cambios durante la comprobación.
- **Software:** 257 pruebas PCWorld, 147 RepoWorld y 13 de diseño (417
  descubiertas). La suite general pasa 415 y omite expresamente las dos
  integraciones del curador; esas dos se ejecutaron aparte con su entorno
  y ambas pasaron. No se cuentan las omisiones como éxitos de la suite general.
- **GPU: 0 horas nuevas; LLM: 0 llamadas reales.** No hay prueba remota,
  lock científico habilitado ni puntuación nueva SWE-bench.

El primer intento de ejecutar también los tests unitarios dentro del venv
mínimo del curador falló por ausencia de `jsonschema`; los unitarios se
comprueban con las dependencias del proyecto y las integraciones reales con
las del curador. Se conserva ese intento fallido. Dos rondas iniciales de
preflight se interrumpieron al consolidar el protocolo y corregir el
reemplazo de alias nativos descubierto en revisión. La prueba real reprodujo
el borrado antes del arreglo; después se rechazan tanto borrado como
reemplazo. La ronda final conservó las fuentes sin modificaciones.

Una ronda posterior se detuvo al escribir `progress.json` con `ENOSPC` de
Btrfs (todo el dispositivo asignado, área de metadatos con escaso margen,
aunque `df` mostraba espacio de datos libre). Se conservaron los logs y
recibos, y se retiraron únicamente cachés BASE regenerables de las rondas
interrumpidas y de intentos fallidos de preparación de Pytest; el inventario
de limpieza queda en los artefactos. Se reinició
el preflight completo sin modificar fuentes ni sustituir instancias.

Perfiles fijados del curador:

- Servicio Requests: `85b82310450cdb1a58b4cac223f1fe231e6039713ce4844db37dc3d860b3cf02`.
- Renderizado Pytest: `fdfb6c1eb14cfd4e3b2ae536e371f1b5664b0c4ab597c97ace435cf669f06479`.

## Recuento público por repositorio

| Repositorio | Instancias | PASS por ronda | SKIP declarados por ronda |
|---|---:|---:|---:|
| astropy/astropy | 1 | 7 | 0 |
| django/django | 6 | 209 | 0 |
| matplotlib/matplotlib | 2 | 140 | 0 |
| mwaskom/seaborn | 1 | 43 | 0 |
| pallets/flask | 2 | 256 | 0 |
| psf/requests | 2 | 72 | 0 |
| pydata/xarray | 1 | 37 | 0 |
| pylint-dev/pylint | 1 | 3 | 0 |
| pytest-dev/pytest | 7 | 694 | 1 |
| scikit-learn/scikit-learn | 2 | 301 | 0 |
| sphinx-doc/sphinx | 2 | 16 | 0 |
| sympy/sympy | 9 | 180 | 0 |

Cada ronda se ejecutó dos veces. Una omisión de Python 2 en pytest-5103 se
conserva con su identidad y motivo exactos; no cuenta como pase. Los alcances
son públicos y limitados, no suites completas. Astropy excluye de antemano
red y CuPy en su perfil CPU/offline; seaborn usa utilidades sin descargas.

Los hashes por instancia, runtime, suplemento, plan y recibo quedan en
[el manifiesto compacto](swebench/REPOWORLD-ENVIRONMENTS-VERIFICATION.json).
Los artefactos locales definitivos están en
`ECHO-5.1/artifacts/repoworld-option-b-20261014/`: `preflight-r4`,
`software-r4`, `curator-r2`, `smoke-r2`, `smoke-audit.json` y
`curator-integration-r2.log`. Los cuatro gates comparten el mismo manifiesto
de fuentes. La auditoría de los recibos públicos verifica su custodia;
no convierte estas pruebas en evidencia de resolución de los issues.

## Qué permanece abierto

- Preparar y validar los controles oficiales del resto de las 36 instancias.
  Los cuatro controles de calibración no satisfacen ese gate de campaña.
- Calibrar el 32B remoto, revisar tiempos y cuota real, y sellar el contrato.
- Ejecutar S/I2/F/E y las ablaciones bajo el mismo presupuesto, congelar los
  parches y después evaluar con el oráculo separado.
- Medir H1/H2/H3/H4/T20 y transferencia independiente; no se garantiza una
  ventaja de E sobre F ni se eligen tareas por favorecer al router.
- Este perfil no admite reparaciones de C/Cython sin reconstruir y validar
  sus artefactos. Un kernel compatible, systemd/cgroup v2 y Bubblewrap siguen
  siendo dependencias del host: no se afirma portabilidad universal Linux.


## Reproducción

Se requieren los artefactos fijados del registro, el dataset autorizado y el
harness v4.1.0. Para el curador debe estar activo un servicio Podman rootless
en `unix:///tmp/repoworld-docker-api/api.sock`, como indica su configuración;
el servicio creado para esta entrega se detuvo al acabar sus controles.
Cada ejecución debe usar un directorio de salida nuevo.

```bash
python3 ECHO-5.1/scripts/run_repoworld.py preflight \
  --registry ECHO-5.1/artifacts/repoworld-option-b-20261014/registry.json --output NUEVO_DIRECTORIO

export REPOWORLD_CURATOR_SERVICES="$PWD/ECHO-5.1/artifacts/repoworld-curator-option-b-20261013/services.json"
export REPOWORLD_CURATOR_SERVICES_SHA256=85b82310450cdb1a58b4cac223f1fe231e6039713ce4844db37dc3d860b3cf02

python3 ECHO-5.1/scripts/run_repoworld.py curator-preflight \
  --contract ECHO-5.1/docs/SWE-CONTRACT.json \
  --sample ECHO-5.1/docs/swebench/SWE-SAMPLE.json \
  --curator ECHO-5.1/artifacts/repoworld-dependencies-20261013/curator-config.json --scope calibration \
  --output NUEVO_DIRECTORIO

python3 ECHO-5.1/scripts/run_repoworld.py verify --output NUEVO_DIRECTORIO
```

Los artefactos pesados, las autoridades HMAC y el material sellado del curador
permanecen fuera de Git. Los registros públicos deben distinguir trabajo
lógico, tiempo, evidencia de ejecución y resultados finales; los hashes no
prueban por sí mismos corrección científica ni ventaja causal de ECHO.
