# Calibración remota v2 — resultado del 14 de octubre

**Gate técnico válido; resultado del agente negativo: diff vacío.**
Se ejecutó una sola instancia reservada, `sympy__sympy-19007`, con las
fuentes de usabilidad de `9a9ab57` y los gates documentados en `259be85`.
No se inició campaña ni evaluación oficial. No se hicieron cambios de código
ni de presupuesto durante el episodio.

## Ejecución y parada

Cuaderno privado: `rogeernavarro/echo51-repoworld-usability-v2-20261014`, v1.
Qwen2.5-Coder-32B-Instruct Q4_K_M fijado; 65/65 capas en CUDA0/CUDA1, dos T4.
Kaggle terminó COMPLETE; `errors=[]`, `relay_result.stopped=true`.
Relay y túnel locales propios también detenidos, verificando PID e identidad.

- Preparación remota: 465,861 s.
- Calibración local: 405,703 s.
- Worker completo: 883,307 s (aproximadamente 14,7 minutos).
- Cuota observada: 22,62 h antes; **22,37 h después**.
- Consumo aproximado según cuota redondeada: 0,25 h GPU.
- 63 peticiones relay: incluyen plantilla y tokenización, no son 63 generaciones.
- 21 llamadas LLM, 21.980 tokens, 22 herramientas, 8 intentos de parche, 2 tests.
- Auditoría válida: **304 recibos**, contabilidad completa, cero reservas pendientes.
- Fuentes sin cambios durante la ejecución.

## Qué funcionó y qué no

Se registró un reinicio de cursor auténtico incompatible. Los ocho errores de
parche devolvieron `PATCH_FORMAT_ERROR` con contexto real. Hubo **ocho lecturas
de rescate exitosas** (una tras cada rechazo); no se excedieron dos por intento.
Los dos baselines públicos pasaron. No hubo un candidato aceptado para staging,
por lo que no se ejercitó el guardarraíl de regresión sobre un nuevo candidato.

Todas las lecturas de rescate pidieron empezar en la línea 220 de
`sympy/matrices/expressions/blockmatrix.py`, donde hay ejemplos de documentación.
La función `_entry()` comienza en la línea 235. El agente recibió las líneas
reales, pero sus diffs siguieron usando contexto que no coincidía. Los rechazos
mantuvieron el árbol intacto; terminó `budget_stopped` al agotar ocho intentos.
El hash del diff vacío es
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.

## Comparación descriptiva con la calibración anterior

| Medida | Anterior | Usabilidad v2 |
|---|---:|---:|
| Llamadas LLM | 17 | 21 |
| Tokens | 15.698 | 21.980 |
| Intentos de parche | 8 | 8 |
| Candidatos aceptados para staging | 0 | 0 |
| Diff final | Vacío | Vacío |
| Auditoría | 251 recibos válidos | 304 recibos válidos |

Las correcciones funcionan mecánicamente, pero este episodio no demuestra
mejora de resolución ni eficiencia. Es una comparación de desarrollo sobre un
mismo issue, no una estimación estadística ni confirmación independiente.
El gate técnico comprueba inferencia y contabilidad; no declara éxito científico.

## Siguiente trabajo propuesto, no realizado

Investigar por qué la lectura se ancla en la documentación: comprobar selección
de símbolo, continuidad de paginación y conservación del fragmento observado
antes de generar el diff. Hacerlo primero offline, sin relajar la comprobación
exacta de hunks ni consultar el oráculo reservado. No se ejecutaron los 96
episodios ni se generó un nuevo lock en esta entrega.

## Evidencia y checklist

Directorio privado: `artifacts/repoworld-gates-v2-20261014/remote/`.

- [x] Calibración real con dos T4 y modelo fijado.
- [x] Gate remoto válido y auditoría de 304 recibos.
- [x] Activación real de cursor-reset, feedback y lectura de rescate.
- [x] Kaggle COMPLETE, worker y procesos propios detenidos.
- [x] Cuota final registrada: 22,37 h.
- [ ] Parche útil / resolución del issue: no conseguido.
- [ ] Nuevo sellado y campaña: no realizados.
- [ ] Evaluación oficial y cierre científico de ECHO-5.1.

### Hashes

- `calibration/report.json`: `0e02dc697c402a9a93dfa1195f6bac66fd5753652a0eb09369afa4933ccbd641`.
- `calibration/episode/submission.json`: `e4fb49343e9ec69ce1389216be2af0043729350e844b1d6f219d48b2d067cc6f`.
- `audit-episode.json`: `81eaeb1b16508e8069a70f7bc5f096acaa5ec69c5fdeec8d7ddbcac1541c9fef`.
- `usability-observations.json`: `d2c4f92d38a1125915b4ee70712d4b5fc783a8efc8e94b0da3e2b892ebae3993`.
- `kaggle-output/gpu-proposer-results.json`: `1e990c6d40d9dec27f1d1b929356412e2afedfb342f9cba8f208b71c7223394e`.
- `quota-after.json`: `a9ee3c53fa581b815d7a37cf859a4c6e4f3f6aadfc6e0172ed38419b52be2b94`.
