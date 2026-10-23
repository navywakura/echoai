# RepoWorld — renovación local de gates v2 (14 de octubre de 2026)

Fuentes de partida: `9a9ab57`, rama `research/echo-5.1-pcworld1`.
Esta entrega no inicia GPU, cuaderno Kaggle, relay ni túnel; no consulta al LLM.

## Rutas

Desde `/home/user/github-restructure/worktrees/echoai-pcworld1`:

```bash
G="$PWD/ECHO-5.1/artifacts/repoworld-gates-v2-20261014"
RUN="$G/remote"
REGISTRY="$G/registry.json"
```

| Evidencia | Ruta relativa a `$G` | Método |
|---|---|---|
| Software | `software/` | Nueva ejecución de verify |
| Smoke | `smoke/` | Nuevo episodio simulado y replay |
| Acciones del smoke | `smoke-actions.json` | Rescate de lectura y rollback real |
| Auditoría smoke | `smoke-audit.json` | Firmas, contabilidad y resultado |
| Preflight | `preflight/` | Nuevos checks públicos de 36 entornos fijados |
| Controles oficiales | `official-controls/` | Auditoría y enlace de evidencia existente |
| Procedencia del enlace | `official-controls/link-provenance.json` | Origen, hashes y diferencias de fuentes |
| Preparación offline de calibración | `readiness.json` | Intercepta el constructor del proveedor |
| Configuración remota | `remote/provider-config.json` | 32B fijado, contexto 4096, salida 768 |
| Credenciales privadas | `remote/relay-secrets.json` | Dos claves aleatorias nuevas, modo 0600 |

`registry.json` conserva las rutas y hashes de los entornos existentes. No se
reconstruyen runtimes ni se descargan imágenes en esta entrega. El contenedor
externo de artefactos/credenciales es privado; los comandos de preparación usan
`umask 022`, igual que el preflight, para reproducir permisos de snapshots.

## Enlace de controles oficiales: alcance preciso

El resumen publicado está en
`docs/swebench/REPOWORLD-CURATOR-COMPLETE-20261014.json`.
Se verifican la autoridad HMAC del gate original, sus 36 filas, los 72 logs de
controles vacío/referencia, el log agregado, dataset, muestra, commits base,
manifest de servicios y commit limpio del harness. Las únicas cinco fuentes
que difieren son tools/workspace/protocol y sus dos archivos de tests; el
curador aislado y todas las demás fuentes del manifiesto permanecen idénticos.

El gate nuevo declara `controls_reexecuted=false`, enlaza el directorio original
y autentica el SHA-256 de la procedencia. **No es una nueva ejecución de los
controles oficiales** y no modifica el gate antiguo. Se conserva el resultado
36/36 como evidencia de un curador sin cambios, con su origen verificable. El
script `link_controls.py` falla ante cualquier diferencia adicional de fuentes.

## Smoke v2

Sobre SymPy-19007 reservado: cuatro lecturas iniciales; parche con contexto
erróneo; dos lecturas de rescate; rechazo de una tercera; parche que provoca una
regresión pública y se descarta; parche inocuo retenido; fin y replay idéntico.
Es una prueba de infraestructura, no una solución del issue ni un resultado LLM.

## Calibración remota preparada (NO ejecutada aquí)

Al autorizar el siguiente paso, `python3 "$RUN/operate.py" start` valida los
cuatro gates, inicia relay/túnel propios y prepara un cuaderno privado; no lo
sube ni inicia Kaggle. Usar una única sesión 2×T4 para el cuaderno generado y
esperar la disponibilidad del worker. El helper conserva `umask=0o022` para el
subproceso de calibración.

Comando equivalente, una vez listo el worker:

```bash
umask 022
export REPOWORLD_RELAY_TOKEN="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["client_token"])' "$RUN/relay-secrets.json")"
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
unset REPOWORLD_RELAY_TOKEN
```

No imprimir/exportar las claves en logs ni usar `set -x`. Alternativamente,
`python3 "$RUN/operate.py" calibrate` lee la clave directamente y guarda el log.
El worker tiene límite de servicio de 600 s tras la carga y envoltura de 1800 s.
Tras el episodio, comprobar COMPLETE y `relay_result.stopped`, auditarlo y
cerrar los procesos propios con `python3 "$RUN/operate.py" stop`.

## Lo que no está cerrado

El contrato de diseño sigue sin habilitar lanzamiento. El lock antiguo no es
válido para estas fuentes. Faltan la calibración remota con este protocolo y
un nuevo sellado; la mejora del modelo y los resultados SWE-bench siguen sin
medir. No iniciar la campaña con el lock de la calibración anterior.

## Resultado final comprobado

- [x] Verify: **423 pasados, 3 integraciones opcionales omitidas, cero fallos**
  (RepoWorld 153 + PCWorld 257 + diseño 13).
- [x] Smoke válido: replay idéntico, 173 recibos auditados, dos candidatos
  aceptados para staging, una regresión pública bloqueada.
- [x] Preflight: **36/36** instancias válidas, 12 repositorios.
- [x] Controles oficiales **36/36 enlazados**, 72 logs verificados; no reejecutados.
- [x] Los cuatro gates aceptan el manifiesto actual de fuentes.
- [x] Comando de calibración probado hasta la construcción del proveedor,
  interceptada antes de conexión; no se emite un falso gate remoto.
- [x] Configuración, claves 0600, helper y comando preparados.
- [x] **0 GPU, 0 llamadas LLM**, ningún servicio remoto iniciado.
- [ ] Calibración remota v2 con modelo real.
- [ ] Nuevo sellado y campaña posterior.

### Hashes del enlace de evidencia

- `software/report.json`: `5af4fc4e95652714f86d41abf82e244867d0438f31df9c97c6b17c8711e53bb9`.
- `smoke/report.json`: `1e88f8fbaaf13144d8f7873a45fe04e2688f177551729b81655ab16d5e8172b4`.
- `smoke-audit.json`: `00dd817cd059dc442d11c3c7c661194c8c6a488f51ccbb82f4a0f39f44373ccc`.
- `preflight/report.json`: `73805b024491369116cd7f186dadc2b7e002aa6cc916007dd86c3a1051de7ee5`.
- `official-controls/report.json`: `eae1dc5f87f05c557cada0eea6f7ac76e4a6ec1a67c53150a182e3c00e663522`.
- `official-controls/link-provenance.json`: `28032c3e01fe517c27f9e76a489cb865f286083aee12ab6cdad0fd9cdd1e27fd`.
- `readiness.json`: `33df092df76c8f364edc6e30c18c2548f60f1d7ac7b2910d7628a6fff745cf6d`.

## Actualización posterior: calibración ejecutada

La entrega local descrita arriba fue 0 GPU. Posteriormente, con autorización,
se ejecutó la calibración en T4: gate técnico y auditoría válidos, diff vacío,
worker apagado y 22,37 h restantes. Véase
[resultado remoto v2](REPOWORLD-REMOTE-V2-RESULTS-20261014.md).
No se generó un nuevo lock ni se inició campaña.
