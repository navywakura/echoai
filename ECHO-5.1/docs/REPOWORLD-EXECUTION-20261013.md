# RepoWorld: ejecución, recuperación y compuertas

> Informe histórico de `9e4fde0`. La continuación de entornos se documenta en
> [Opción B](REPOWORLD-ENVIRONMENTS-COMPLETE-20261013.md); los recuentos siguientes
> describen aquella entrega, no el estado más reciente.

Continuación local de `e0a1a6d` en `research/echo-5.1-pcworld1`.
**El benchmark todavía no se ha lanzado.** La compuerta de entornos sigue
fallando; no se ha iniciado Kaggle ni consumido GPU en esta entrega. El
contrato científico original conserva `status: design` y `launch_enabled: false`.

## Checklist de esta entrega

| Estado | Pieza | Alcance comprobado / pendiente |
|---|---|---|
| Implementado y probado localmente | Checks públicos y rollback | BASE se ejecuta dos veces. Comparación por identidad de test; fallo, desaparición y skip no certifican pase. Un parche regresivo no mueve HEAD con guard activo. |
| Implementado y probado localmente | Protección de tests | Diff de producción acotado; tests/configuración protegidos también se montan `ro`. Las copias de fixtures conservan modos originales para no provocar errores falsos de permisos. |
| Implementado y probado localmente | S, I2, F, E, E_no_guard | Proveedor finito para pruebas, mismo presupuesto global, dos ramas independientes en I2. E_no_guard cambia la retención automática. No son resultados de un LLM. |
| Implementado y probado localmente | Transporte y recuperación | Reservas persistentes, identidad estable, respuesta tardía, deduplicación, reenvío del resultado sin regenerarlo y recuperación del export final. |
| Implementado y probado localmente | Memoria pública | Persistencia con procedencia, lookup cobrado y obligación de comprobar cada nuevo candidato. Un recuerdo nunca importa un veto semántico ni un resultado oficial. |
| Implementado; integración oficial bloqueada | Curador | Harness fijado, controles vacío/referencia en proceso separado, export de parches congelados y conservación de raw/verified. El control real de Requests ha fallado. |
| Implementado y probado localmente | Orquestación y auditoría | Gates autenticados, identidad del estudio ligada al lock, registro de cada celda, límites de cuota, barrera global y export para el plotter. |
| Parcial | Dependencias reales | 7/36 instancias pasan el preflight de desarrollo, cubriendo 6/12 repositorios. Faltan imágenes y preparación por commit. |
| Pendiente | Calibración remota, lock científico y campaña | Prohibidos mientras fallen los entornos/control del curador. Sin puntuación SWE-bench ni gráficas de resultados reales. |

## Evidencia local

El smoke `artifacts/repoworld-smoke-20261013/r4/` usa el commit reservado
`sympy__sympy-19007` y ejecuta tests reales de SymPy en Bubblewrap. Un proveedor
**simulado** propone una regresión; el guard la rechaza; después propone un
cambio neutro que pasa las pruebas públicas. La repetición recupera el mismo
resultado, sin generar de nuevo. No es una solución al issue de SymPy.

**Verificación final: 342 pruebas pasan (74 RepoWorld, 255 PCWorld, 13 diseño/análisis).**
La auditoría del smoke valida 68 recibos, dos propuestas, una regresión y una
retención bloqueada, sin presupuesto pendiente.

La verificación final queda en `artifacts/repoworld-verification-20261013/r3/`;
su gate vincula logs y fuentes, comprobando que estas no cambiaron durante
las suites. El informe compacto publicable está en
[swebench/REPOWORLD-EXECUTION-VERIFICATION.json](swebench/REPOWORLD-EXECUTION-VERIFICATION.json).
Las autoridades HMAC, dependencias, imágenes, parches de referencia y logs
privados quedan en artefactos locales ignorados por Git.

El preflight de desarrollo `artifacts/repoworld-preflight-20261013/r4/`
mantiene **todas las 36 instancias** del registro, incluidas las que no tienen
imagen. No sustituye problemas fallidos ni mezcla los alcances de distintos
commits. Estos son sus pases:

| Commit/instancia | Tests públicos observados, dos veces |
|---|---:|
| seaborn-3407 | 43; utilidades offline, excluye descarga de datasets |
| flask-5063 | 126; módulo público `test_basic.py` |
| requests-2674 | 38; unidades sin transporte externo |
| xarray-4248 | 37; módulo público de utilidades completo |
| sphinx-7686 | 8; módulo público de utilidades completo |
| sympy-20212 | 22; módulo público `test_basic.py` |
| sympy-19007, calibración | 22; mismo alcance público, otro commit |

Son alcances para detectar regresiones públicas; no equivalen a la suite
completa de cada proyecto ni a los tests finales de SWE-bench. La elección
offline se hizo leyendo los tests del BASE, sin consultar candidatos ni
resultados finales. No se reduce el denominador científico.

Bloqueos observados:

- 20 instancias todavía carecen de una entrada de entorno fijada por commit.
- Matplotlib y scikit-learn requieren generación/build de componentes del BASE.
  Astropy ya tiene un build aislado correcto: 42 archivos generados, 17 extensiones,
  imports válidos y 32,3 segundos; falta incorporar ese suplemento al snapshot
  y validarlo en Bubblewrap. Instalar una wheel publicada de la biblioteca objetivo
  no demuestra que se esté probando el código que el agente modifica.
- Django, Matplotlib y Pylint incluyen enlaces simbólicos. El importador actual
  los rechaza; no se han aplanado ni eliminado silenciosamente.
- Pytest necesita su archivo de versión generado con procedencia. Su módulo
  completo también encontró restricciones de semáforos/warnings. El experimento
  auxiliar de 57 tests puros no se presenta como pase del catálogo completo.
- Flask-4992 necesita dependencias compatibles con ese commit; el pase de
  Flask-5063 no se transfiere automáticamente. Requests-2148 necesita un plan
  público offline o servicios de prueba aislados reproducibles.

## Control oficial y motivo de no encender Kaggle

Se instaló el harness v4.1.0, commit
`726c5461e2ef52d83cf1ea2107870a8bb3328d57`, en un entorno de curador separado.
Podman rootless ejecuta su interfaz Docker sin permisos sobre Docker rootful.
Se descargó la imagen oficial de la calibración Requests-2148, digest
`sha256:98917950f24c65799c8a15fd50af114a488aa797010a6af13c36938d3bd0512d`.

En `artifacts/repoworld-official-controls-20261013/r3/`, los controles vacío y
referencia finalizaron en aproximadamente 10 segundos cada uno. Ambos dieron
`raw_resolved: false` y evidencia insuficiente para pasar la compuerta; aparecen
errores de conexión en ambos. Se impuso red externa deshabilitada, memoria
acotada y capacidades reducidas. Falta resolver la dependencia de servicios
de test y demostrar equivalencia bajo esa política; no se atribuye el fallo a
ECHO ni se cambia el oráculo para obtener un pase. Las otras 35 imágenes del
registro no estaban presentes. Los contenidos de los tests y la referencia
no se enviaron al protocolo online.

Por tanto:

- **Gate 1: rojo.** Entornos públicos incompletos y control oficial no válido.
- **Gate 2: verde acotado.** Smoke local con tests reales y proveedor simulado.
- **Gate 3: pendiente.** Ninguna inferencia nueva en Kaggle.
- **Gate 4: parcial.** Software y revisión local documentados; no hay lock
  científico autorizado ni campaña congelada preparada para ejecutar.

Las 22,94 h GPU son la última observación histórica, no una consulta nueva.
No se promete que 96 episodios duren 2–3 horas. El diseño registra 150 celdas
incluyendo calibración, guard y memoria; el episodio remoto de conectividad
es adicional y debe usar una instancia de calibración, no una primaria.

## Recuperación y límites de las afirmaciones

`provider-prepared` fija prompt y coste antes de reservar; `provider-intent`
y `provider-response` enlazan la solicitud con su cuenta. El relay requiere
`--journal` para IDs duraderos. Un cambio de origen del túnel no cambia la
identidad experimental; temperatura, revisión, contexto y demás ajustes sí.
El estudio rechaza mezclar dos locks en el mismo directorio de salida.

Si el episodio vence con una respuesta desconocida, se conserva el cargo
máximo reservado y se marca `token_usage_complete: false`. No se afirma que
se hayan observado esos tokens ni que el worker haya terminado: su parada
debe comprobarse por separado. No hay garantía distribuida de ejecución
exactamente una vez; una entrega al worker perdida puede quedar ambigua y
requiere resolución o cierre contabilizado, nunca regeneración gratuita.

Un límite global registra las filas realmente no iniciadas como `not_started`,
con diff vacío, conservando el denominador. No puede reclasificar como no
iniciada una celda con trabajo previo. Una celda interrumpida sin conciliar
bloquea la liberación del evaluador final.

HMAC acredita custodia de observaciones; no demuestra que una aserción sea
verdadera. JUnit/stdout proceden de un proceso no fiable. Los controles de
colección, exit y archivos protegidos detectan fallos concretos, pero no
constituyen una prueba general contra monkeypatching del runner Python.
Un sondeo propuesto por el crítico conserva autoridad `unknown` hasta contar
con soporte público independiente. El resultado final usa el harness sellado.

## Operación local

```sh
python3 ECHO-5.1/scripts/run_repoworld.py verify --output <verificacion-nueva>
python3 ECHO-5.1/scripts/run_repoworld.py preflight --registry <registry.json> --output <preflight-nuevo>
python3 ECHO-5.1/scripts/run_repoworld.py smoke --registry <registry.json> \
  --instance sympy__sympy-19007 --actions <acciones-mock.json> --output <smoke-nuevo>
python3 ECHO-5.1/scripts/run_repoworld.py audit-episode <smoke-nuevo>/episode
python3 ECHO-5.1/scripts/run_repoworld.py curator-preflight \
  --contract ECHO-5.1/docs/SWE-CONTRACT.json --sample ECHO-5.1/docs/swebench/SWE-SAMPLE.json \
  --curator <capacidad-curador.json> --output <control-nuevo>
```

`registry.json` tiene `schema: repoworld.environment-registry.v1`, ruta
`dataset` y una lista `entries`. Cada entrada contiene `instance_id`, `source`
(Git del commit fijado), `runtime` (directorio de `runtime.json`) y `check_plan`
(catálogo público con argv estructurado, targets y límites). Un plan no acepta
comandos de shell. `dependencies.freeze_python` y `dependency_runtime` congelan
un Python explícito y dependencias ya preparadas; no instalan paquetes del
repositorio en el supervisor. Los inventarios/locks de wheels de esta preparación
están en `artifacts/repoworld-dependencies-20261013/env-investigation/`.

El build de Astropy está en `env-investigation/astropy-build-r1/integration.json`:
commit `7269fa3e33e8d02485a647da91a5a2a60a06af61`, tar generado SHA-256
`df299e0a569f703194eea34a020179777453f867ad1a5fa458ca37c3bd91080a`.
Se ejecutó sin red en un builder rootless con 4 CPU, 3 GiB y techo de 600 segundos;
no modificó archivos versionados. Sus procesos/contenedores temporales terminaron.

La capacidad del curador contiene `python`, `harness`, `dataset`,
`dataset_sha256`, `output` y, opcionalmente, `docker_host`. El intérprete debe
conservar la ruta del virtualenv; resolver su symlink seleccionaría el Python
host. El curador puede descargar imágenes con `--allow-pull`, separado de la
ejecución offline. Esa opción no inicia GPU.

Solo tras pasar ambos preflights y el smoke procede `calibrate`; después,
`seal`, `run`, `audit`, `evaluate`, `audit --export` y
`scripts/plot_swebench_results.py`. Consultar `--help` de cada subcomando.
La salida completa del estudio está ligada por HMAC al lock, registro y
configuración de modelo; no debe reciclarse para otra campaña.

**ECHO-5.1 sigue abierto:** faltan la campaña externa, la evaluación común,
el análisis pareado y la confirmación independiente de H1–H4/T20. No se ha
hecho push ni publicación.
