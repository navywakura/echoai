# RepoWorld — gates locales v3 y preparación remota

Fuentes de partida: `1dc18c0`, rama `research/echo-5.1-pcworld1`.
Esta entrega es **0 GPU y 0 llamadas LLM**. No inicia Kaggle, relay ni túnel.

## Resultado comprobado tras recuperar Btrfs

| Comprobación | Resultado |
|---|---|
| Verify secuencial | 427 pasados, 3 opcionales omitidos, cero fallos |
| RepoWorld | 157 pasados + 3 omitidos |
| PCWorld | 257 pasados |
| Diseño | 13 pasados |
| Preflight público | 36/36 instancias, 12/12 repositorios |
| Smoke y replay | 173 recibos válidos, una regresión bloqueada |
| Controles oficiales enlazados | 36/36; no reejecutados |
| `check_ready.py` | válido, lectura atómica 220–259 y frontera del proveedor alcanzada |
| `remote/operate.py check` | salida 0, cuatro gates válidos |
| GPU / llamadas LLM | 0 / 0 |

El balance Btrfs ejecutado por el propietario permitió completar las escrituras.
No se borraron artefactos ni se cambió código. El primer verify concurrente con
preflight falló en `test_registration_after_frontend_death_is_stopped_and_observed`
con `startup cancellation unconfirmed`. Una prueba aislada falló exigiendo CPU
positiva pese a confirmar TIMEOUT y job_empty; el diagnóstico instrumentado pasó.
La suite completa ejecutada una vez tras acabar preflight pasó sin modificaciones.
Esto evidencia sensibilidad temporal; **no demuestra que la intermitencia esté
corregida**. Se preservan los fallos en `software-concurrent-failure/`,
`startup-isolated.log` y `startup-diagnostic.log`; la ejecución secuencial está
registrada en `software-sequential.log` y `finish-sequential.log`. Conviene investigar
esta prueba antes de afirmar estabilidad bajo carga concurrente.

## Rutas y comandos locales

Desde `/home/roger/github-restructure/worktrees/echoai-pcworld1`:

```bash
G="$PWD/ECHO-5.1/artifacts/repoworld-gates-v3-20261014"
RUN="$G/remote"
REGISTRY="$G/registry.json"
```

| Gate o artefacto | Ruta relativa a `$G` |
|---|---|
| Verificación nueva | `software/` |
| Smoke nuevo | `smoke/` |
| Acciones mock | `smoke-actions.json` |
| Auditoría smoke | `smoke-audit.json` |
| Preflight nuevo | `preflight/` |
| Controles oficiales enlazados | `official-controls/` |
| Procedencia del enlace | `official-controls/link-provenance.json` |
| Auditoría de preparación offline | `readiness.json` |
| Configuración del proveedor | `remote/provider-config.json` |
| Claves nuevas privadas | `remote/relay-secrets.json` |
| Helper preparado | `remote/operate.py` |

Los comandos ejecutados se conservan en `commands.json` y se coordinan con
`run_local.py`: verify, smoke y preflight se ejecutan en procesos separados.
Tras la interrupción, el smoke completo se conservó; verify y preflight
se relanzaron porque sus procesos habían terminado sin sellar el gate.
El Parquet temporal ausente se restauró desde la revisión fijada
`6ec7bb89b9342f664a54a6e0a6ea6501d3437cc2`, comprobando el SHA-256
`7a21f37b8bc179c7db5beeb14e88ac538ba283455c776e6b2535bbfb6e3551b4`.
La restauración descargó únicamente datos, sin GPU ni inferencia; los checks
del preflight se ejecutan aislados sin red.

Se usan el registro v2 existente y sus runtimes fijados, sin reconstruirlos.
La extracción/preparación conserva `umask 022`; el directorio de secretos es
0700 y las claves son 0600. No copiar los gates a otra ruta: su autoridad
HMAC está vinculada a su directorio absoluto.

## Smoke con lectura atómica

La primera acción pide `file_view` de
`sympy/matrices/expressions/blockmatrix.py`, desde 220, con 40 líneas.
La auditoría exige las líneas 220–259 íntegras, sin cursor adicional,
`Matrix([\n` en la 225 y `def _entry(` en la 235, conservadas en el feedback.

Después se comprueban agotamiento de localización, error de contexto,
dos lecturas de rescate, rechazo de la tercera, regresión pública bloqueada,
un parche inocuo retenido y replay idéntico. Es un episodio simulado:
el parche final de smoke no pretende resolver el issue SWE-bench.

## Controles oficiales: evidencia reutilizada con auditoría

`link_controls.py` verifica el gate original de
`repoworld-requests-replacement-20261014/official-controls` y su resumen público
`docs/swebench/REPOWORLD-CURATOR-COMPLETE-20261014.json`. Recomprueba firmas,
36 identidades/commits, 72 hashes de logs, log agregado, dataset, muestra,
servicios y el commit limpio del harness.

Frente al manifiesto original, solo admite cinco archivos modificados
(tools/workspace/protocol y sus dos tests) y el nuevo test de herramientas.
Las demás fuentes, incluido el curador aislado, deben coincidir exactamente.
También comprueba que la modificación del contrato respecto a `0e70ff8` se
limita a los tres campos de lectura declarados en `context`; no cambian
oráculos, identidades ni semántica del curador.

El nuevo gate incluye `controls_reexecuted=false`, origen y hash de la
procedencia: **no son 36 ejecuciones nuevas** ni se reescribe el gate antiguo.
La evidencia corresponde a controles oficiales ya realizados con un curador
que permanece intacto.

## Helper remoto v3 preparado, no iniciado

```bash
python3 "$RUN/operate.py" check
```

Valida software, smoke, preflight y official-controls con el manifiesto actual,
y la configuración del modelo. No realiza inferencia ni inicia procesos remotos.
Las claves client/worker son nuevas, distintas entre sí y respecto a v2.
`remote/preparation-audit.json` registra esa comprobación sin exponerlas.

En una fase futura autorizada:

1. `python3 "$RUN/operate.py" start` inicia relay/túnel propios y prepara el
   cuaderno **privado** `rogeernavarro/echo51-repoworld-atomic-v3-20261014`.
   No lo sube automáticamente a Kaggle.
2. Iniciar una única sesión con dos T4 y el modelo fijado; esperar readiness.
3. `python3 "$RUN/operate.py" calibrate` ejecuta una sola instancia reservada,
   `sympy__sympy-19007`, con `umask 022`, leyendo la clave sin imprimirla.
4. Auditar el episodio, comprobar parada efectiva de Kaggle y después ejecutar
   `python3 "$RUN/operate.py" stop` para cerrar solo los procesos locales propios.

El comando subyacente es:

```bash
python3 ECHO-5.1/scripts/run_repoworld.py calibrate-remote \
  --registry "$REGISTRY" \
  --contract ECHO-5.1/docs/SWE-CONTRACT.json \
  --sample ECHO-5.1/docs/swebench/SWE-SAMPLE.json \
  --preflight "$G/preflight" \
  --curator "$G/official-controls" \
  --smoke "$G/smoke" \
  --provider "$RUN/provider-config.json" \
  --instance sympy__sympy-19007 \
  --output "$RUN/calibration"
```

Para ejecutarlo directamente hacen falta `umask 022` y la variable
`REPOWORLD_RELAY_TOKEN` cargada desde el archivo privado. Preferir el helper,
que configura ambas sin imprimir la clave. Nunca usar `set -x` con secretos.

El proveedor sigue fijado a Qwen2.5-Coder-32B Q4_K_M, contexto 4096,
entrada máxima 3200 tokens y salida máxima 768. El worker tiene un plazo de
600 segundos tras la carga y la envoltura limita el conjunto a 1800 segundos.
La duración ni el éxito del próximo episodio están garantizados.

## Pendiente después de esta entrega

La comprobación offline se detiene al construir el proveedor: no se emite
un falso recibo de calibración remota. El contrato continúa en `design` y
`launch_enabled=false`. Faltan calibración v3 real, auditoría y nuevo sellado.
Los locks anteriores no autorizan estas fuentes. Leer el código completo no
prueba todavía que el modelo pueda resolver el issue ni cierra ECHO-5.1.

## Hashes de los gates comprobados

```text
software/report.json  910c8eda77ecde8ac11e070336f9787e380057e4281ac658b8d9da6a3e37643d
preflight/report.json  4a0ec07a65458eefe19049315292c7d18b91ba3146dc097607c293e20fe53fcb
smoke/report.json  875de026f343486559b1b42bbaa2e99da3b346b7529bc289359baa59e507eb51
official-controls/report.json  db9bc1155cee7c1e9749492c6b5c4b88c7297f0c3cc9ab2631a5f4634cf48ebe
```
