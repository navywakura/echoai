# GEN-1c — calibración heredable, contrato previo al resultado

Fecha: 2026-09-09. GEN-1 y GEN-1b se conservan rojos. Este tercer banco aísla
la pregunta mínima del roadmap: si un entero heredado reduce el tiempo de
aprendizaje del hijo sin copiar Q/T/CAM.

## Tarea

Cada vida ofrece un actuador/contexto WSP y tres órdenes. `approach` o `avoid`
es la orden correcta; `wait` nunca lo es. La respuesta del actuador contiene
ruido entero determinista del 30% y la vida termina tras la observación. El
hijo debe estimar qué orden funciona. Esto representa calibración de un mando
o sensor al edge, no navegación ni supervivencia completa.

El mecanismo es el de GEN-1b: `evidence_budget` usa `T.n[s][a]` para probar
las acciones menos observadas antes de confiar en Q. Candidatos 1, 2 y 4;
el naïf usa 2. `evidence_budget=0` conserva la selección histórica.

Tras cada vida se examina `Q.best` sin ejecutar el mundo ni escribir memoria.
Éxito significa escoger la orden verdadera. Criterio: primera vida con ocho
aciertos consecutivos. Censura en 50 vidas se contabiliza como 51.

## Separación fijada

- Selección: contextos `3,7,11`; semillas `3109,3121,3137`.
- Examen: contextos `5,9,13,17`; semillas
  `3203,3221,3251,3271,3299`.
- Cada pareja comparte exactamente contexto, ruido y fase.
- El mejor presupuesto se fija antes de abrir las 20 parejas de examen.

Brazo heredado, configuración directa, naïf 2, ablación a 2, histórico 0 y
control sin actualización Q. El hijo nace con memorias vacías y sólo recibe
el presupuesto. Configuración directa debe reproducir al heredado; ablación,
al naïf. El control sin Q debe obtener cero criterios.

## Cierre

El ganador debe ser distinto de 2. En examen: al menos 18/20 hijos alcanzan
criterio; mediana heredada menor que naïf; suma capada heredada como máximo
80% de la naïf; al menos 10 victorias estrictas y como máximo 4 derrotas; suma
heredada menor que la histórica. `false_facts`, `destroyed` y `cortex_calls`
permanecen a cero. El auditor reconstruye criterio, selección y comparaciones
desde las 50 vidas. Si falla, el resultado permanece rojo.

## Resultado medido

Rojo por el umbral prefijado: presupuesto 4, 20/20 criterios, suma heredada
235 frente a 316 del naïf y mediana 9 frente a 12, pero sólo 7 victorias
estrictas (mínimo 10), una derrota y 12 empates. La revisión posterior detectó
que la secuencia de ruido incluía la acción elegida. Este informe se conserva
como piloto, no como cierre: `lab/echo2_gen1c_report.json`.
