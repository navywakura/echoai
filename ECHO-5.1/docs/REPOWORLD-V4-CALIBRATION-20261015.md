# RepoWorld — calibración v4 del traspaso al editor

Implementación congelada: `ec57aa1`, rama `research/echo-5.1-pcworld1`.
Artefactos: `ECHO-5.1/artifacts/repoworld-gates-v4-20261015/`.

## Compuertas locales

- Verify nuevo: **443 pruebas pasadas, 3 omitidas, cero fallos**. RepoWorld
  ejecuta 176 (173 pasadas + 3 omitidas), PCWorld 257 y diseño 13.
  El resumen de entrega indicaba 445; este informe usa los logs recién ejecutados.
- Smoke nuevo de SymPy: válido, replay idéntico, rollback observado, fuentes
  intactas; 127 recibos auditados, dos propuestas y una regresión bloqueada.
- Preflight: 36/36 reatestados, sin volver a ejecutar sus tests. Se autentican
  los recibos originales, se comprueban todos los hashes de snapshots/runtimes,
  identidad del registro/dataset y planes públicos. Solo cambiaron protocolo,
  evidencia de lecturas y tests de interfaz; ejecutor y checks siguen iguales.
- Official-controls: 36/36 reatestados, 72 logs y controles negativo/positivo
  autenticados, sin repetirlos. Curador aislado, harness y contratos conservados.
- `check_ready.py` alcanza la frontera del proveedor con red bloqueada y sin
  construir el proveedor real. `operate.py` valida las cuatro compuertas.

Los archivos `link-provenance.json` conservan procedencia y diferencias de fuente;
no se presenta evidencia reutilizada como ejecución nueva. Claves del relay
nuevas, privadas y fuera de Git. No se modificó el código durante estas compuertas.

## Alcance remoto

Una instancia reservada: `sympy__sympy-19007`, brazo E, semilla 73.
Qwen2.5-Coder-32B-Instruct Q4_K_M, 2 T4, límite global 25.000 tokens,
24 llamadas LLM y 8 parches. Cuaderno privado:
`navywakura/echo51-repoworld-handoff-v4-20261015`, versión 1.

No hay comparación entre brazos ni evaluación del oráculo final en este ensayo.
El contrato sigue `design`, `launch_enabled:false`; no se sella la campaña.

## Precisiones de la implementación ensayada

- El umbral de 8.000 tokens se evalúa entre llamadas; una llamada puede
  sobrepasarlo. No se garantiza una reserva estricta de exactamente 17.000.
- `has_locus` comprueba que hay una proyección de fuente observada vigente.
  No prueba por sí solo que el símbolo objetivo entero se haya localizado.
- Estos límites se registran sin cambiar la implementación congelada durante
  la calibración. Aplicar un parche tampoco equivale a resolver el issue.

## Resultado remoto

**Calibración técnica válida; objetivo funcional no alcanzado.**

| Métrica | Observado |
| --- | ---: |
| Capas en GPU | 65/65 |
| Preparación / duración total del worker | 348,016 / 486,417 s |
| Duración del episodio | 129,995 s |
| Llamadas LLM | 8 |
| Tokens entrada / salida / total | 6.707 / 320 / 7.027 |
| Máximo de entrada por llamada | 841 |
| Herramientas / checks base / parches | 10 / 2 / 0 |
| Tokens restantes | 17.973 |
| Auditoría | 120 recibos válidos; contabilidad completa |
| Reservas pendientes / desbordamientos / CAM destroyed | 0 / 0 / 0 |
| Estado | `finished`, `task_success:false`, diff vacío |

Modelo fijado y verificado: revisión `9d3053fce650fe1cdbdb75998c2a87add9d178ef`,
SHA-256 `4d64b316b5e6319d9613e0d97935d9ebd631fc7e334da400d00085eca749d085`,
llama.cpp b11577. No hubo errores reportados por el worker.

## Causa observada y alcance de la conclusión

Las ocho salidas del modelo fueron la misma búsqueda:

```json
{"action":"repo_search","arguments":{"path":"sympy/matrices/expressions/","pattern":"BlockMatrix"}}
```

Todas recibieron `UNSAFE_PATH: path must be canonical and relative`.
`repoworld/tools.py::_path` conserva el validador estricto de snapshots:
la barra final produce un componente vacío y `pcworld/snapshots.py::_parts`
lo rechaza. El feedback no entrega una ruta corregida ni explica la barra final.
El modelo no eliminó ese carácter, a diferencia de lo observado en V2 anterior.

No hubo búsquedas exitosas, outlines, lecturas de fuente ni parches. Al llegar
a ocho llamadas de localización sin fuente observada, el supervisor cerró el
episodio limpiamente y conservó 17.973 tokens. Esta ejecución comprueba la
**ruta de abandono sin locus**, no el traspaso exitoso al editor ni su capacidad
de reparación. Menor coste que V2 no implica mayor eficacia: ambos entregaron
un diff vacío y esta ejecución no alcanzó el método.

La repetición aquí es de **búsquedas inválidas**, no de lecturas válidas. Por eso
el detector de lecturas redundantes no se activó; el límite de ocho llamadas
impidió que la repetición consumiera todo el presupuesto.

### Siguiente corrección acotada (pendiente, no aplicada aquí)

- Hacer accionable el rechazo de ruta: indicar que la ruta relativa de directorio
  debe ser `sympy/matrices/expressions`, sin barra final.
- Evaluar normalización solo en la frontera de búsqueda de directorios, con
  registro de argumento original/canónico. Mantener rechazo de absolutos,
  traversal `..`, NUL y escapes; no relajar el validador general de snapshots.
- Añadir un mock con la búsqueda exacta fallida y repetición del rechazo; comprobar
  recuperación o parada explícita. Después renovar gates y calibrar nuevamente.
- Validar por separado la reserva estricta de tokens y que la evidencia de
  traspaso cubra el locus elegido, no únicamente un fragmento cualquiera.

No se retocó el código ni se repitió inferencia para buscar un resultado verde.
Los recibos de esta ejecución quedan congelados.

## Apagado y cuota

Kaggle quedó **COMPLETE**, `relay_result.stopped:true`, con cero errores del
worker. Relay y túnel locales detenidos; sus PID ya no existen. La respuesta
inicial `worker-stop.json` era una solicitud, no confirmación; el cierre se
corroboró después con el resultado del worker y el estado terminal de Kaggle.
Cuota: **21,94 → 21,80 h**, consumo aproximado **0,14 h** por lectura redondeada.
No quedan procesos propios consumiendo GPU ni una campaña en segundo plano.

## Checklist para continuación

- [x] HEAD y árbol limpio inicial comprobados; código `ec57aa1` intacto.
- [x] Verify nuevo: 443 pasadas, 3 omitidas; smoke hermético válido.
- [x] Preflight 36/36 y controles oficiales 36/36 reatestados con procedencia.
- [x] Frontera del proveedor y helper comprobados offline.
- [x] Una calibración real 32B/2 T4; auditoría y apagado completos.
- [x] Abandono sin código observado comprobado con modelo real.
- [ ] Recuperación de búsqueda con ruta no canónica.
- [ ] Traspaso real a editor con fuente relevante y presupuesto disponible.
- [ ] Parche útil aplicado, checks públicos y no-regresión.
- [ ] Evaluación oficial sellada y comparación S/I2/F/E con ablaciones.
- [ ] Cierre científico independiente de ECHO-5.1; contrato sigue en design.

## Evidencia privada y reproducción

```bash
G=ECHO-5.1/artifacts/repoworld-gates-v4-20261015
python3 "$G/remote/operate.py" check
# Artefactos de esta calibración ya terminada: no reutilizar su directorio para otro run.
```

`software/`, `smoke/`, `preflight/`, `official-controls/` y
`remote/calibration/` contienen los cinco gates técnicos autenticados.
`remote/audit.json`, `remote/diagnostic-summary.json` y el resultado descargado
permiten distinguir el resultado funcional del gate técnico.

## Hashes de custodia


- `software/report.json`: `f054de93284cd85ce6ae8b518d3868394098507d5287b7ab3591cc3420b878f2`.
- `smoke/report.json`: `9ae3d4f00dfc7187593b3dbd8be2d16bf061940daf72394bc783174be92c1d14`.
- `preflight/report.json`: `c27d8b9ab9ee598c31ae6f7e3fabed35c5d188cc7fac5c5a8ae9657f0c44599b`.
- `official-controls/report.json`: `8d8e252f3d6e67534b1e7f11e13a46fe8234c74f40de19ed4ec915f6afcf3de4`.
- `readiness.json`: `3c1fe921ae4460fccd9ea55a0f678a84246a77fad634f72a872622c657379e47`.
- `remote/calibration/report.json`: `6ce7df8f25f07227cea79079620e106b8318cdba02da99778907dfbce0ca359e`.
- `remote/audit.json`: `b7c6ebcbb7bcf337b4939eb4eb6f06e5048b4a9b0e62e3db772b709e5cec6a5a`.
- `remote/diagnostic-summary.json`: `bb8afe5417406702415a63545bbab0517cbb4a1a5c697d458cf74b323ec43f14`.
- `remote/kaggle-output/gpu-proposer-results.json`: `1efd9d5f7cb8f750fd6a1cc426749bbe205ab353b69726ea96cc2e56004f5c57`.
