# LOCALDEV-1 — arnés local de desarrollo

Implementado el 2 de octubre de 2026 en `harness/localdev/`, versión 0.1.0.
La orden instalada es `echo-dev`; también funciona `python3 -m harness.localdev`
desde la raíz de echoai. El ejecutor utiliza Python del sistema y Bubblewrap.
El comprobador de tipos vive en un entorno independiente:
`~/.local/share/echo-localdev/tools`, con dependencias fijadas en
`harness/localdev/requirements-tools.txt`.

El módulo permite comprobar código y producir un parche candidato mediante
fallos observados. Su verde significa que pasan los controles de ingeniería
seleccionados. S6, la transferencia ARC, EGO-MEMORIA y RSI conservan sus propios
contratos y estados. No hay una medición que permita atribuirle un 80 % de
desarrollo autónomo, un 90 % de cobertura o corrección universal.

```bash
echo-dev doctor
echo-dev scan
echo-dev run
echo-dev demo
```

Cada orden crea evidencia nueva bajo `lab/localdev/`; admite `--output RUTA`.
Se rechaza reutilizar un directorio existente. Los fallos de calibración se
conservan junto a los resultados posteriores.

| Pieza | Implementación y alcance |
|---|---|
| Mapa | `inventory.py`: AST de Python, firmas, anotaciones declaradas, importaciones, ciclos, cuerpos duplicados y posibles stubs. Los JS/JSX se inventarían como otros lenguajes |
| Copia | `common.py`: copia con hashes; excluye `lab`, archivos ocultos, modelos, dependencias, archivos grandes, enlaces simbólicos y el proyecto legado |
| Ejecutor | `runner.py` + `worker.py`: espacio de nombres aislado, código de solo lectura, stdout/stderr, errores estructurados, recursos y veredictos por prueba |
| Casos generados | `cpu_contracts.py`: 100 rejillas deterministas, leyes de rotación y reflexión, formas límite, conservación de paleta y repetición de primitivas |
| Bucle | `engine.py`: pruebas fijas, propuesta JSON, hashes esperados, lista de archivos editables, diagnóstico, nueva validación y parche revisable |
| Regresión del arnés | `tests/test_localdev.py`: aislamiento real, límites, recibos, propuestas inválidas, HTTP simulado y ciclo completo |

El mapa es estático. Un ciclo de importaciones o un cuerpo duplicado señala un
lugar para revisar; por sí solo no acredita un defecto. Las importaciones
dinámicas, interfaces inferidas y comportamientos dependientes de ejecución
requieren pruebas adicionales. El análisis no importa los módulos que visita.
Se usa el [AST de Python](https://docs.python.org/3/library/ast.html).

El perfil `run` fija cinco comprobaciones: compilación sintáctica de las fuentes
Python copiadas; clases `TestWorld`, `TestTConf`, `TestCorridor`, `TestGate` y
`TestBench` de la batería existente NEXUS-0; propiedades de las primitivas; los
doce tests existentes de `tests.test_rsi1`; y mypy sobre el nuevo arnés. No se
lanza el descubrimiento indiscriminado de todas las pruebas del repositorio.
Hay pruebas que abren campañas o requieren herramientas externas, y no forman
parte de este perfil. Para seleccionar otra batería:

```bash
echo-dev run --test tests.mi_modulo.MiContrato
python3 -m unittest tests.test_localdev -v
```

La segunda orden ejecuta el controlador de integración en el anfitrión. Sus
casos de ejecución de candidatos abren sus propios sandboxes. Esto evita
habilitar sandboxes anidados dentro del ejecutor. La prueba HTTP crea un
servidor local simulado; no consulta un proveedor ni carga un modelo.

Los dobles de prueba están declarados en cada recibo. Los doce tests RSI usan
su transporte simulado existente y una réplica diminuta 999; el solver y su
biblioteca son reales. Los destinos de artefactos quedan en el espacio temporal
de la prueba. No se modifica el comportamiento del runtime para fingir una GPU.
La prueba de protocolo con una respuesta sintética acredita transporte y
formato, sin medir la capacidad de un LLM. NEXUS-0 continúa sin LLM.

El trabajador ve `/usr`, una copia de las fuentes, un `/tmp` privado y dos
directorios temporales de salida. No se montan el hogar, credenciales, sockets
del anfitrión, dispositivos GPU ni artefactos científicos. Los módulos existentes
`navi10_*.py` del directorio padre se copian como dependencias de código cuando
se trabaja con este repositorio. La red se aísla y se limpia el entorno. El
trabajador se copia al directorio de evidencia, se monta de solo lectura y su
hash figura en el recibo. [Política de aislamiento de Bubblewrap](https://github.com/containers/bubblewrap).

Los límites predeterminados por trabajo son 60 segundos de pared, 1.536 MiB
de espacio virtual por proceso y 512 KiB combinados de stdout/stderr. Los
perfiles pueden declarar otros tiempos hasta 600 segundos. También se limita
el tamaño de archivo, descriptores y procesos mediante
[`resource`](https://docs.python.org/3/library/resource.html). El temporal en
memoria tiene 64 MiB. Las salidas persistentes se supervisan cada 0,5 segundos:
32 MiB o 2.000 archivos provocan detención. Esta supervisión puede sobrepasar
transitoriamente el umbral; no es una cuota de disco instantánea. La memoria es
un límite por proceso, sin cgroup agregado. El máximo RSS registrado no es la
suma de todos los procesos concurrentes. Se combina `getrusage` dentro del
trabajador con muestreo de `/proc` cada 100 ms. El recibo distingue máximo RSS
de un proceso y máximo muestreado de la suma del árbol. Cuando un timeout impide
el recibo final, no se inventa el consumo CPU del trabajador: queda sin dato.

La prueba de aislamiento comprueba que un candidato no pueda escribir su
fuente, leer un archivo privado, ver una variable de credenciales ni conectar
con el puerto del anfitrión. Otra comprueba que el timeout termine también un
hijo. Estas comprobaciones dependen del kernel y de Bubblewrap disponibles;
no constituyen una demostración formal de seguridad ante código adversarial.
El controlador y las pruebas siguen siendo componentes confiables.

El bucle de reparación admite únicamente archivos Python enumerados con
`--allow`. Rechaza fuentes que aparezcan en los perfiles científicos
congelados, pruebas, contratos, el propio arnés, rutas externas, enlaces,
ediciones duplicadas, hashes obsoletos y cambios vacíos. Un lote se valida
completo antes de escribirlo. Se permiten hasta ocho archivos y 64 KiB por
propuesta. La copia se modifica entre intentos; el repositorio original conserva
su código. Si cambian los originales durante una ejecución, queda registrado
`CUSTODY_FAILED` y el parche pierde el verde.

```text
copia y contrato → sintaxis / pruebas / tipos
                         ↓ fallo real
                  propuesta estructurada
                         ↓ archivos permitidos + hash
                  aplicar a la copia
                         ↓
                  volver a comprobar
                         ↓
          candidate.patch + recibo, sin merge automático
```

Ejemplo de configuración para un módulo nuevo con su contrato ya escrito:

```bash
echo-dev loop \
  --allow ruta/modulo_nuevo.py \
  --test tests.test_modulo_nuevo \
  --endpoint http://127.0.0.1:8080/v1/chat/completions \
  --model MODELO_LOCAL \
  --max-attempts 3 --max-seconds 600
```

Las rutas del ejemplo se sustituyen por archivos del trabajo concreto. El
comando comprueba sintaxis, tests fijos y tipos de los archivos candidatos.
El proponente puede ser un servidor compatible local o una URL HTTPS explícita;
`--key-file RUTA` enlaza una clave elegida por el usuario. La clave no se copia
al sandbox ni se guarda en el recibo. El controlador solo envía los archivos
permitidos y diagnósticos acotados. No hay proveedor predeterminado, detección
automática de secretos ni llamada a un LLM al ejecutar `run` o `demo`.

El adaptador limita cada salida a 2.048 tokens solicitados, conserva el uso que
declare el proveedor y exige JSON. Cada intento reserva presupuesto antes de
contactar: una respuesta inválida o un error también consume un intento. El
máximo es diez intentos y una hora para un contrato; los valores predeterminados
son tres y diez minutos. El plazo se aplica a las pruebas y a la petición HTTP,
incluida una respuesta que se bloquee. No se negocian ni debilitan pruebas tras
un fallo. Una suite vacía, un skip, un fallo esperado o un recibo ausente no
pueden dar verde.

`demo` contiene un `clamp` defectuoso. Un mutador AST determinista enumera
intercambios de límites basándose en la presencia de un fallo de prueba. La
primera propuesta sigue fallando; la segunda pasa tres pruebas, incluida una
familia de 500 casos con semilla fija. La demostración verifica el mecanismo
del bucle sin gastar tokens de un modelo. No demuestra investigación autónoma,
aprendizaje de pesos ni automejora recursiva.

Cada trabajo guarda `spec.json`, la copia del trabajador, `stdout.log`,
`stderr.log`, `out/details.json` y `result.json`. El bucle añade contrato,
presupuesto, feedback, propuestas, historial de intentos y `candidate.patch`.
Los logs se vacían al disco conforme llegan; pueden seguirse con `tail -f`.
Los registros contienen operaciones y errores observados, no pensamientos
inventados ni un segundo bus cognitivo. El trazado cuenta líneas ejecutadas
en el perfil indicado; no informa de cobertura de ramas ni porcentaje de
proyecto completo. En RSI se desactiva ese trazado: la calibración conservada
agotó 90 segundos con él y completó los mismos doce tests sin él en unos cinco.

El informe de cierre y las mediciones se guardan en
[ECHO-LOCALDEV-RESULTS.md](ECHO-LOCALDEV-RESULTS.md). El siguiente uso práctico
es desarrollar un módulo nuevo, fijar sus pruebas antes del bucle y revisar el
parche validado. Cualquier cambio posterior en una condición científica
necesita su contrato propio; este arnés no sustituye esa evaluación.
