# RepoWorld — calibración remota v3 (2026-10-14)

## Resultado

La calibración técnica terminó y su gate es válido, pero **no resolvió SymPy**:
`budget_stopped`, ocho intentos de parche rechazados y diff vacío. No se ha
sellado un nuevo contrato ni lanzado la campaña de 96 episodios.

Fuentes: commit `c805cd9` (código de `1dc18c0` sin cambios), rama
`research/echo-5.1-pcworld1`. Cuaderno privado
`navywakura/echo51-repoworld-atomic-v3-20261014`, versión 1.
Artefactos: `ECHO-5.1/artifacts/repoworld-gates-v3-20261014/remote/`.

## Ejecución y contabilidad

| Medida | Resultado |
|---|---|
| Modelo | Qwen2.5-Coder-32B-Instruct Q4_K_M fijado |
| GPU | 2 Tesla T4, 65/65 capas en CUDA |
| Preparación del worker | 366,844 s |
| Calibración | 422,592 s |
| Tiempo total del worker | 814,35 s (~13,6 min) |
| Llamadas LLM | 20 |
| Tokens entrada + salida | 24.498 / 25.000 |
| Herramientas | 22 |
| Intentos de parche | 8 / 8 |
| Parches aplicados | 0 |
| Tests contabilizados | 2 (no validación de un parche nuevo) |
| Auditoría | 294 recibos válidos, contabilidad completa |
| Reservas pendientes / excesos | 0 / 0 |
| CAM destroyed | 0 |
| Evaluación oficial | no ejecutada |
| Cuota GPU antes / después | 22,37 / 22,15 h |

La diferencia de cuota es 0,22 h a la precisión publicada por Kaggle.
El hash del modelo coincide con el fijado:
`4d64b316b5e6319d9613e0d97935d9ebd631fc7e334da400d00085eca749d085`.
Kaggle hizo inferencia; el candidato se ejecutó localmente en Bubblewrap.
El resultado del worker tiene `errors: []` y `stopped: true`; la sesión
terminó `COMPLETE`. Relay y túnel propios detenidos, sin procesos vivos.

## Qué demostró y qué no

Las 302 líneas de las diez páginas leídas se compararon con el snapshot real:
todas son exactas, sin mutilación. La primera página abarcó 22–93 (72 líneas).
Las siguientes fueron 100–149, 150–169, 210–229, 100–149, 145–164, 165–174,
180–199, 170–189 y 200–219. **Ninguna incluyó `def _entry(`, en la línea 235.**
El agente no pidió la página 220–259 que sí se comprobó en el smoke local.

Se observaron siete `hunk context mismatch` y un `truncated hunk`.
Los ocho errores activaron lectura de rescate, pero el modelo siguió proponiendo
contexto inexistente y leyendo zonas que no contenían el método objetivo.
Se agotaron los ocho parches; quedaron solo 502 tokens. No hubo un parche
aplicado cuya semántica se pudiera juzgar con pruebas de regresión.

La corrección de atomicidad funcionó en las lecturas observadas. No garantiza
que el localizador encuentre el método, que un diff esté bien formado ni que
la solución sea correcta. La salida 0 de `calibrate` certifica el recorrido
técnico, no una reparación del issue. No hay evidencia para declarar ventaja
científica o autorizar una campaña útil basándose en esta entrega vacía.

## Siguiente intervención propuesta (no implementada)

1. Medir con mocks una localización por símbolos/definiciones y permitir al
   editor buscar un símbolo cuando sus lecturas todavía no lo contienen.
   La regla debe ser general, sin introducir la línea 235 como respuesta fija.
2. Exigir contexto observado antes de generar un diff y conservar esa ventana
   en el prompt de reparación. Comprobar el manejo de diffs truncados localmente.
3. Renovar gates si cambia el código; usar otra calibración reservada solo
   después de superar esos checks. No aumentar presupuesto ni relajar el parser
   como sustituto de resolver la localización.

La intermitencia de la prueba de cancelación documentada en gates v3 sigue
pendiente; el pase secuencial no la convierte en una corrección.

## Evidencia y hashes

- `calibration/report.json`: `df351261931d72e66df46d5781c3b81f9af4f29801a1bc8428fd4b2b438e644b`.
- `audit-episode.json`: `27231e1513f5b018145d9430649775492fde0bd9bdd4c9eaa14d7162e2ccf2e2`.
- `reading-observations.json`: `bceaa63f735f0d61de300952dc5001384be1fbc034e768f8af1d997c6e82a5bb`.
- `kaggle-output/gpu-proposer-results.json`: `b558ea77b0bd5aff04532b670026a0b2c1c9c7ea7116a0cbb328ee4e2f62ed51`.
- `kaggle-terminal.json`: `9a82f3e3448ab94289736be1f09a9d8981ceb4ff47863c371d169923853a9e13`.
- `quota-start.json`: `a9ee3c53fa581b815d7a37cf859a4c6e4f3f6aadfc6e0172ed38419b52be2b94`.
- `quota-after.json`: `1aaeb2901f7333cafed468c3936f96755fb8cffe5a0abc509c5e5b100a3ff9a8`.
