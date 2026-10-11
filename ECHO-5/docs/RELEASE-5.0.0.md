# ECHO-5 5.0.0 — cierre de alcance validado

12 de octubre de 2026. **Verde oficial dentro del contrato de ECHO-5.**
El veredicto r3 devuelve `closure_verified`, `release_eligible: true` y todos
sus criterios satisfechos. S6 permanece abierto hasta después de ECHO-5.5.

## Qué se publica

Representación de objetos y relaciones, conceptos con evidencia, composición
jerárquica, planificación e interacción, currículo por contraejemplos,
MiniGrid/BabyAI, integración MissionAgent y finalización del logger Gazebo/PX4.
El panel local muestra decisiones registradas; su diagnóstico LIF de 256 unidades
no dirige la política. El neocórtex no intervino en estos ensayos.

La mejora posterior conserva los 326 operadores y 2.000.000 unidades por tarea:
`certified_bound` obtiene **12/18** independientes y **9/9** plantillas,
frente a **0/18 y 0/9** del baseline. Reduce trabajo agregado un 27,90% y
34,36%, respectivamente. Es 66,7% de exactitud en la muestra, no un incremento
relativo calculable sobre cero. La caché sola no desbloqueó estas tareas.

El híbrido obtiene 28/28 con un 4,45% menos de trabajo que frontera cercana.
Su disparador informativo no se activó: todavía no acredita una ventaja de
exploración informativa. El currículo eficiente consigue 64/64 frente a 56/64
aleatorio y reduce un 49,23% el coste del adaptativo anterior; cuesta un 21,16%
más que el aleatorio. Las ocho ejecuciones pareadas no bastan para afirmar
superioridad estadística general. Consultar los informes por familia.

## Validación y procedencia

El cierre r3 y la remediación posterior usan snapshots diferentes. Los
recibos conservan sus identidades originales, no hashes de esta distribución
adaptada a `core/`. Las cuatro auditorías de remediación son procesos separados,
no cuatro implementaciones independientes del solver. Se preservan resultados
negativos anteriores. Las comprobaciones de publicación tienen recibo propio.

[Expediente público y manifiesto](../../research-archive/20261012/README.md) ·
[Resultados de búsqueda y coste](SEARCH-EFFICIENCY-RESULTS-20261012.md) ·
[Checklist](REMEDIATION-CHECKLIST.md) ·
[Portabilidad](PUBLICATION-PORTABILITY.md).

La suite del laboratorio ejecutó 499 pruebas, con 26 omisiones opcionales y
sin fallos; el perfil externo requerido pasó 32/32. La copia pública pasó por separado **502 pruebas, 26 omisiones opcionales**,
**32/32 externas**, sintaxis JavaScript y custodia sin cambios; los tres tests
adicionales comprueban la adaptación de distribución. La repetición del piloto en estas fuentes públicas pasó cuatro auditorías y
conservó resultados, acciones y costes lógicos; solo cambiaron tiempos de reloj
en exploración. Son los mismos casos, no una muestra científica nueva.
Gazebo/PX4 es SITL, **no hardware real**.

## Límites y trabajo futuro

Seis tareas independientes no resueltas: `inside_erase_crop` (0/3) y
`right_erase_crop_rotate` (0/3). En dos casos de la primera familia hay
hipótesis compatibles, pero falta cerrar el consenso dentro del presupuesto.
No se emitieron respuestas incorrectas en esta muestra; no implica cero errores
universales, ausencia de fuga en cualquier entorno ni verificación formal total.
No se declara una nueva puntuación oficial ARC ni investigación abierta arbitraria.

Las propuestas siguientes siguen siendo investigación:

- Optimizar consenso conservando la comprobación de todos los competidores
  exigidos por el contrato. Comprobar solo los ya generados puede omitir
  contradicciones y no autoriza una respuesta certificada.
- Abstracciones o búsqueda bidireccional: contabilizar adquisición y todos los
  pasos ejecutados. Una macro no convierte dos ejecuciones en una unidad real.
  Un tamaño final menor no permite podar cualquier expansión intermedia.
- Mapas con puertas y ambigüedad, válidos y resolubles, definidos antes del examen;
  comparar también frontera cercana con la misma evaluación perezosa.

## Uso

Este release distribuye fuentes, no un wheel nuevo ni pesos de LLM.
El terminal sigue en 4.5.0b1. Desde `ECHO-5/`, con CPython 3.12.13:

```sh
make setup
make setup-sandbox
make test
make panel
```

Panel: `http://127.0.0.1:8765` o `http://echoai.localhost:8765`.
ECHO-5.1 investigará colaboración equivalente en coste; ECHO-5.5 persistencia
y sistema instalable. RSI y S6 no quedan acreditados por este release.
