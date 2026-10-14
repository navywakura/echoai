# Gate 3: una instancia, inferencia remota y parada

Este procedimiento está preparado, **no ejecutado**. No lanzar Kaggle hasta que
`offline-preflight`, `mock-smoke` y `official-controls` (36/36) sean válidos y
correspondan a las fuentes actuales. El contrato continúa en `design`.
`calibrate-remote` es un alias de `calibrate`, con las mismas comprobaciones.

**Estado local final del 14 de octubre:** los controles oficiales y públicos
pasaron 36/36 tras sustituir Requests-2674 por 2317 según la política registrada.
Los informes antiguos `controls-r4` y su recuperación conservan el fallo previo;
no utilizarlos como gates actuales. Se ha comprobado offline que la calibración
alcanza la construcción del proveedor, interceptada antes de cualquier conexión.
**La calibración remota sigue pendiente.** Véase el [informe](REPOWORLD-CURATOR-ALL-20261014.md).

## Preparación local (sin GPU)

Desde la raíz del worktree, elegir un directorio privado nuevo `RUN` bajo
`ECHO-5.1/artifacts/`. Crear `relay-secrets.json` con dos valores aleatorios
independientes, claves `client_token` y `worker_token`, y permisos 0600.
No publicar secretos, cuadernos que los incluyan ni resultados privados.

El relay se inicia **cuando se vaya a calibrar**, con diario persistente:

```bash
python3 ECHO-5.1/scripts/inference_relay.py "$RUN/relay-secrets.json" \
  --port 8786 --journal "$RUN/relay-journal" --log "$RUN/relay.jsonl"
cloudflared tunnel --url http://127.0.0.1:8786
```

Conservar ambos PID propios. Usar el origen HTTPS que devuelve el túnel para el
worker. El proveedor local puede usar `http://127.0.0.1:8786`; no necesita salir
por el túnel. Su JSON debe incluir los campos de
`QWEN-LOCAL-REPAIR.example.json`, sustituyendo:

- `endpoint`, `tokenize_endpoint`, `template_endpoint`: puerto 8786.
- `model`: `pcworld-qwen25-coder32b`.
- `revision`: `9d3053fce650fe1cdbdb75998c2a87add9d178ef`.
- `tokenizer`: `embedded GGUF 4d64b316b5e6319d9613e0d97935d9ebd631fc7e334da400d00085eca749d085`.
- `timeout_seconds`: 240; `key_env`: `REPOWORLD_RELAY_TOKEN`.

Exportar `REPOWORLD_RELAY_TOKEN` leyendo `client_token` sin imprimirlo.
Mantener Q4_K_M, contexto 4096, salida 768, semilla 73 y temperatura 200 milésimas.

## Worker privado en Kaggle

Reutilizar `write_bundle()` de `scripts/prepare_kaggle_repair.py` mediante
`runpy.run_path`, **sin llamar a su función prepare() de reparación 14B**.
El objeto de entrada debe contener:

```python
bundle = {
    "schema": "pcworld.gpu-repair-input.v1", "scientific_claim": False,
    "gpu_model": "qwen25-coder32b", "jobs": [],
    "config": worker_provider_config,
    "relay": {"broker_url": tunnel_https_origin,
              "worker_token": credentials["worker_token"], "max_seconds": 600},
}
write_bundle(bundle, output, private_kernel_slug,
    extra_sources={"inference_relay.py": relay_source}, timeout_seconds=1800)
```

`worker_provider_config` usa las mismas identidades del modelo, pero endpoints
locales de Kaggle en `127.0.0.1:8785` y sin `key_env`. `relay_source` es el texto
del script local `inference_relay.py`. El preparador escribe el cuaderno privado,
pero no lo sube. Revisar que `jobs` siga vacío antes de lanzar ese único cuaderno
con 2×T4. No incluir repositorios, pruebas reservadas ni parches de referencia.

El worker comprueba hashes del modelo/binarios y las 65 capas en GPU. Los 600 s
limitan la espera/inferencia del relay **después de descargar y cargar el modelo**;
no garantizan diez minutos de cuota total. La envoltura limita el proceso completo
a 1800 s. Una calibración cortada por ese límite queda fallida, no verde.

## Único comando de calibración

Sustituir las rutas por los gates actuales; no reutilizar informes cuyo manifiesto
de código difiera. El comando comprueba esa identidad antes de consultar al modelo.

```bash
python3 ECHO-5.1/scripts/run_repoworld.py calibrate-remote \
  --registry "$REGISTRY" \
  --contract ECHO-5.1/docs/SWE-CONTRACT.json \
  --sample ECHO-5.1/docs/swebench/SWE-SAMPLE.json \
  --preflight "$PREFLIGHT" --curator "$CURATOR" --smoke "$SMOKE" \
  --provider "$RUN/provider-config.json" \
  --instance sympy__sympy-19007 --output "$RUN/calibration"
```

## Parada y comprobación

El supervisor solicita `/stop` en un `finally`, incluso si falla el episodio.
`worker-stop.json` acredita una solicitud, **no confirma la terminación remota**.
Comprobar en Kaggle que el worker finalizó y que `gpu-proposer-results.json`
contiene `relay_result.stopped: true` (o documentar timeout/error). El worker
termina `llama-server` en su propio `finally`; detener además la sesión/cuaderno
GPU en Kaggle y comprobar su estado final. Cerrar solo los procesos propios del
relay y túnel. Si el supervisor muere abruptamente, el plazo del worker limita
la espera; detener igualmente la sesión de Kaggle.

Auditar el episodio con `run_repoworld.py audit-episode`. Registrar latencia,
contabilidad y cierre del worker. Este gate comprueba el pipeline, no demuestra
resolución oficial de SWE-bench ni autoriza por sí solo la campaña completa.

## Gates locales actuales

Desde la raíz del worktree:

```bash
EVIDENCE=ECHO-5.1/artifacts/repoworld-requests-replacement-20261014
REGISTRY="$EVIDENCE/registry.json"
PREFLIGHT="$EVIDENCE/preflight"
SMOKE="$EVIDENCE/smoke"
CURATOR="$EVIDENCE/official-controls"
VERIFICATION="$EVIDENCE/software"
```

La autoridad HMAC vincula cada diario a su ruta absoluta: conservar estos gates
en su ubicación original, no usar copias movidas ni editar `authority.json`.
Son directorios persistentes del worktree. `verify_final.py` en la misma carpeta
recomprueba firmas, fuentes, muestra y hashes de logs sin contactar un modelo.
Los archivos históricos de recuperación de `/tmp/echo-curator-*-r2` corresponden
a las fuentes anteriores y no sustituyen a estos gates.

## Curador local: perfil de Podman de esta entrega

Tras recuperar el espacio de metadatos de Btrfs, el curador usa un servicio
rootless propio, iniciado con esta opción explícita de extracción:

```bash
podman --storage-opt overlay.ignore_chown_errors=true system service \
  --time=0 unix:///tmp/repoworld-docker-api/api.sock
```

La opción evita que los propietarios de archivos de qhull, fuera del rango
subordinado disponible, impidan descargar las imágenes oficiales de Matplotlib.
Puede modificar propietarios durante la extracción; los contenidos y los
identificadores de imagen siguen fijados. Los controles vacío/referencia deben
validarse con este mismo perfil antes de usarlo en la evaluación final.
No se modifica `~/.config/containers/storage.conf`.

El perfil operativo, la orden de arranque y las identidades de las imágenes se
conservan en `curator-runtime-r4.json` y `rootless-unpack-policy.json` dentro de
la carpeta de evidencia. Para repetir los controles usar el `curator-config.json` de
`ECHO-5.1/artifacts/repoworld-curator-all-20261014/` y exportar
`REPOWORLD_CURATOR_SERVICES` con la ruta absoluta del nuevo
`ECHO-5.1/artifacts/repoworld-requests-replacement-20261014/services.json`, junto con su
SHA-256 en `REPOWORLD_CURATOR_SERVICES_SHA256`. El perfil histórico de Requests
y su ruta dummy forman parte del entorno fijado; no intercambiar manifiestos.
Detener solo este servicio propio después de la ejecución. Gate 3 ejecuta el
repositorio con Bubblewrap; el servicio del curador no necesita estar activo
para inferencia/calibración.
