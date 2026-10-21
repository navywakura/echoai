# GEN-1b — contrato congelado antes de medir

Fecha: 2026-09-09. Estado inicial: diseño aprobado, sin resultados.
GEN-1 permanece como resultado negativo y no se reescribe.

## Hipótesis

Un único entero heredado, `evidence_budget`, puede reducir las vidas necesarias
para aprender una política útil si expresa cuánta evidencia local reunir antes
de confiar en Q. El hijo nace con CAM/Q/T vacías y recibe sólo ese entero.

El mecanismo reutiliza `T.n[s][a]`. Si alguna acción tiene menos observaciones
que el presupuesto, propone una de las acciones con menor conteo; los empates
rotan con el turno. Cuando todas alcanzan el presupuesto, decide la Q existente.
El gate se aplica siempre después. No se escribe otra memoria ni otro bus.

`evidence_budget=0` desactiva el mecanismo y conserva el comportamiento previo.
Los únicos presupuestos experimentales son 1, 2 y 4; 2 es el valor naïf de
referencia. El presupuesto permanece constante durante cada individuo.

## Protocolo fijado

- 40 vidas por brazo; H inicial 16; alimento +24; córtex OFF.
- Criterio: primera vida `e>=4` con 3 éxitos en las últimas 4 evaluaciones.
- Cada evaluación usa política greedy sobre un entorno nuevo, sin exploración
  ni escritura de CAM/Q/T. La memoria entrenada se hashea antes y después.
- Selección: objetos en `(1,0,0)`, `(0,1,0)`, `(2,0,0)`; semillas
  `701, 809, 907`; gana la menor suma capada, desempate 2, 1, 4.
- Examen reservado: objetos en `(0,2,0)`, `(2,1,0)`, `(0,2,1)`, `(2,2,0)`,
  `(1,2,1)`; semillas `1009, 1103, 1201, 1301, 1409`.
- Las condiciones y semillas de selección no aparecen en examen.

Por condición de examen se comparan: hijo con presupuesto heredado, hijo naïf
con presupuesto 2, sistema histórico con mecanismo desactivado, ablación del
entero a 2 y configuración directa del presupuesto ganador. Se añade control
sin actualización Q y control sin nutrición.

## Cierre verde

El ganador debe ser distinto de 2. Sobre las 25 parejas reservadas: el hijo
alcanza criterio en al menos 20, gana estrictamente al naïf en al menos 15,
y su mediana capada es menor que la naïf. No puede rendir peor que el sistema
histórico en mediana. La configuración directa debe reproducir al hijo y la
ablación debe reproducir al naïf, incluidas secuencias de evaluación.

Ningún brazo sin Q puede alcanzar criterio; sin nutrición todas las vidas de
entrenamiento duran 16. CAM nace vacía, Q a cero, T vacía; `false_facts=0`,
`destroyed=0`, `cortex_calls=0`. `green()` reconstruye selección, ventanas,
medianas, parejas y controles desde filas, sin confiar en resúmenes.

Si el protocolo falla, GEN-1b queda rojo. No se cambian estas condiciones tras
ver los resultados. Artefacto: `lab/echo2_gen1b_report.json`.

## Resultado medido

Rojo. Selección eligió 4 (puntuaciones 201/189/175), pero sólo 2/25 hijos
alcanzaron criterio; medianas heredada, naïf e histórica quedaron censuradas en
41. El banco mostró que la exploración local por sí sola no resuelve las rutas
fuera del horizonte de crédito. Evidencia: `lab/echo2_gen1b_report.json`.
