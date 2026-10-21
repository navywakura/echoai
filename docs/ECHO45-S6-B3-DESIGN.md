# S6-B3 · cuatro brazos sobre la base temporal v5.8

2026-09-27. Contrato previo a llamadas al modelo y al examen 18000–18059.
Nav autoriza ejecutar el examen H1/H3 y los cuatro brazos en segundo plano.
S5-F2 es independiente: no se usa su resultado para cambiar esta campaña.
Los cierres anteriores S6-A/B2 permanecen ROJOS.

## Alcance y brazos

Base común: v5.8 con H1/H3 ya programados y comprobados en desarrollo.
SEMILLA conserva exactamente ese agente sin ayuda externa. FIJO pide siempre
una política general ante tres fallos. ECHO selecciona P1 reparación próxima,
P2 fallos relacionados, P3 generalización del último avance aceptado o P4
diario; aprende de las aceptaciones de cada tipo. P3 queda excluido hasta
haber un avance aceptado. SIN FILTRO conserva la última política propuesta
por ECHO que pasa seguridad, ejecución y determinismo, independientemente
de su utilidad. No consume llamadas adicionales.

Se comparan **políticas acotadas de selección y composición de mecanismos
existentes**, no generación arbitraria de algoritmos, neuronas o código.
El LLM solo emite datos JSON. Se permiten los cuatro controles anteriores
HOLD/MIN_EVIDENCE/BABBLE/WALL_MIN y ENTRY_PROBE_LIMIT,
ORDER_MIN_SUPPORT/COUNT_MIN_SUPPORT, ORDER_ENABLED/COUNT_ENABLED,
AFTER_EFFECT_POLICY y PROBE_STRATEGY. Límites y características observables
están fijados en `echo_arc/temporal_policy.py`; la gramática exige defaults
completos y exactamente una condición y una modificación. No se admite
identificar semilla, familia, color, coordenadas ni solucionador.

## Desarrollo y verificación

A: versiones 2/3, semillas 0–19, rep 0. B: versiones 2/3, semillas 20–39,
rep 0. Ambos contienen las once familias, 40 partidas por conjunto y 2000
decisiones por partida. Nuevo agente en cada partida. Solo A alimenta las
peticiones: resumen de niveles, fallos de predicción, acciones sin coordenadas
y soporte/conflictos de memoria sin colores ni reglas del solucionador.
B, juegos oficiales y ambos exámenes quedan fuera de los prompts.

- V1: parser de datos cerrado, límites enteros, rechazo de campos desconocidos
  y duplicados; sin ejecutar código del modelo.
- V2: ejecutar en A y repetir las 40 partidas en un pool y cache independientes;
  registros completos idénticos. Cada juego tiene límite de 240 segundos y
  4 GiB por proceso. Error, timeout o discrepancia descartan la propuesta.
- V3: al menos dos niveles adicionales en A frente a la política actual,
  sin perder niveles ni puntuación en ninguna partida individual de A.
- V4: sin perder niveles ni puntuación en ninguna partida individual de B.

Tolerancia numérica de puntuación por partida: 1e-10. Se guarda respuesta
antes de verificar, petición, tokens, modelo, veredicto y métricas; cada brazo
tiene diario y cache separados. Una auditoría independiente reconstruye
las peticiones y estrategias; reejecuta las políticas aceptadas en A/B.
La observación del desarrollo conserva el comportamiento del agente.

## Modelo y ejecución

Qwen/Qwen2.5-Coder-7B-Instruct, revisión
`c03e6d358207e414f1eca0bb1891e29f1db0e242`, FP16, dos T4 de Kaggle.
**30 respuestas por brazo**, seis rondas de cinco; dos comprobaciones de
formato previas sin datos de tareas: 62 respuestas máximas en total.
Temperatura 0.7, top-p 0.95, máximo 900 tokens nuevos; mismo calendario de
semillas del modelo por ronda para FIJO/ECHO. La selección se actualiza entre
rondas; cada propuesta se verifica contra el estado actual dentro de la ronda.

Notebooks privados, solo GPU gratuita, sin escalado pagado ni API frontier.
La cuota observada antes del arranque es aproximadamente 84 minutos GPU.
Cada job tiene tope remoto de 900 segundos; devuelve la GPU mientras se
verifica localmente. Si quedan menos de 900 segundos gratuitos, el supervisor
espera reposición y deja el estado visible. No garantiza completar esta semana.
Las respuestas incompletas y fallos se conservan; no se remuestrea en secreto
una ronda fallida ni se cambia a pago. Metadatos, envío y estado remoto quedan
registrados; credenciales privadas nunca viajan al notebook.

## Examen y criterio de cierre

Congelar fuentes antes del desarrollo y las cuatro políticas antes de abrir
**18000–18059**, versiones 2/3, reps 0/1/2, 2000 decisiones: 360 partidas,
1800 niveles por brazo. Se valida determinismo/solucionador en 600 niveles.
No hay observador en el examen; contadores y puntuación conservan la convención
histórica que excluye reinicios automáticos, aunque se guardan y cuentan aparte.
Cada política distinta repite las 120 partidas de rep 0 en pool y cache nuevos.
Políticas idénticas pueden compartir registros: son literalmente el mismo actor.

Después de congelar, medir SEMILLA/ECHO en los ocho juegos oficiales de
desarrollo, tres reps y presupuesto 2000. No elegir otro agente con esos datos.

| Criterio | Condición, conservada del contrato B2 |
|---|---|
| B1 | ECHO ≥105 % de los niveles de SEMILLA y puntuación media ≥SEMILLA |
| B2 | ECHO supera los niveles de FIJO |
| B3 | ECHO supera los niveles de SIN FILTRO |
| B4 | ECHO no pierde niveles ni puntuación total en desarrollo oficial |
| B5 | Fuentes intactas, registros/puntuación válidos, solicitudes y estrategias reconstruibles, oráculos 600/600 y replays completos exactos |

**VERDE = B1 ∧ B2 ∧ B3 ∧ B4 ∧ B5**. Publicar ROJO si falla alguno;
PENDIENTE si falta evidencia. No ajustar fuentes ni reemplazar examen una vez
abierto. La auditoría JSON y el informe Markdown se publican automáticamente.
Esto no demuestra resolver ARC-AGI oficial reservado ni ARC-AGI-1/2.
