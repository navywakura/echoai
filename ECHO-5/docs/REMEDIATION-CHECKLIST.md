# Revisión de mecanismos posterior a r3

**Publicación 5.0.0: verde dentro del alcance validado.**
[Release y límites](RELEASE-5.0.0.md) ·
[Veredicto r3](../../research-archive/20261012/closure-verdict-20261011-r3/result.json).
Los objetivos de investigación no demostrados permanecen abiertos y no se
convierten en resultados positivos por esta publicación.


Actualización, **12 de octubre de 2026, 00:06 (Madrid)**: las correcciones de coste
terminaron con cuatro auditorías válidas. Detalle en
[resultados de eficiencia](SEARCH-EFFICIENCY-RESULTS-20261012.md).

| Corrección nueva | Implementación y validación | Resultado y límite |
|---|---|---|
| Reutilización, firmas y cota de pérdida | Comprobadas; alfabeto completo, mismo presupuesto y referencias externas | 12/18 independientes frente a 0/18; 9/9 plantillas frente a 0/9; seis agotamientos pendientes |
| Consenso prioritario | Nivel retenido completo, contraejemplos tempranos, abstención al agotar trabajo | Sin respuestas erróneas en la muestra; dos ajustes nuevos siguen sin presupuesto suficiente para cerrar consenso |
| Exploración híbrida | Puerta observable, cuota y enfriamiento; auditoría nativa | 28/28; 4,45 % menos trabajo que frontera cercana, mismas acciones; ninguna activación informativa en esta muestra |
| Currículo eficiente | Paradas exactas y actualización de supervivientes; controles optimizados | 64/64, 49,23 % menos coste total que adaptativo anterior; todavía 21,16 % más coste que aleatorio, que logra 56/64 |
| Tests y custodia | 499 tests sin fallos, 26 opcionales omitidos; perfil nativo 32/32 | Fuentes congeladas; piloto CPU final de 147,32 segundos; sin promoción automática |

- [x] Implementar y medir las cuatro intervenciones, con trazas reales.
- [x] Reproducir las cuatro etapas en procesos independientes.
- [ ] Resolver las seis tareas nuevas pendientes dentro del presupuesto.
- [ ] Aislar y demostrar utilidad del disparador informativo frente a cercanía optimizada.
- [ ] Confirmar coste/utilidad del currículo frente a controles en más ejecuciones independientes.

La sección siguiente conserva los resultados del **piloto anterior**, que motivó
las correcciones; no debe confundirse con la ejecución nueva. S6 sigue aplazado.

El cierre anterior terminó `closure_verified`, con alcance limitado, en
`artifacts/closure-verdict-20261011-r3/result.json`. Esta tabla corresponde a
una revisión nueva. Un instrumento correcto puede medir una pérdida o un empate.

| Intervención | Implementación | Comprobación científica |
|---|---|---|
| Exploración con habilidades iguales | Tres selectores sobre las mismas fronteras; sin datos privados del mapa | Piloto por tamaño y misión, pares completos, coste e incertidumbre; confirmación aparte |
| Semántica independiente | Referencias explícitas de orden, ubicación y objetos; trayectorias positivas/negativas nativas | Acuerdo con significado independiente, detección de mutaciones; no lenguaje arbitrario |
| Segundo generador | Escenas de construcción distinta y oráculo independiente; controles de ambigüedad | Exactitud/abstención por familia y costes; comparación no pareada con plantillas |
| Autopsia de síntesis | Prefijos evaluados/retenciones, testigo externo a la búsqueda | Clasificar dónde se pierde el testigo; no equiparar guía humana y descubrimiento |
| Currículo por demanda | Controles calculan lo que consultan, presupuestos y costes por fase | Medir adquisición y selección incluidas; admitir ausencia de ventaja |
| Custodia y reproducción | Protocolo previo, archivo de fuentes, procesos separados, diario existente | Tests antes de medir, cada resultado reproducido; errores de instrumento detienen la cadena |

Estado de ejecución: **implementado, medido y auditado**. La suite base ejecutó
414 casos (24 opcionales omitidos); el perfil nativo pasó 59, con solapamiento.
El piloto de cinco bloques terminó en 62,48 segundos. Una autopsia posterior
comparó dos alfabetos en seis casos idénticos y también se reprodujo.

| Comprobación | Resultado de esta revisión |
|---|---|
| Exploración | Empate 28/28 en los tres brazos; no ventaja de acierto demostrada |
| Semántica | 32 referencias, 20 rechazos sintácticos, 94 comparaciones de trayectorias y 3 rechazos nativos coinciden |
| Transferencia con gramática completa | 0/18 nuevos y 0/9 plantillas; agotamiento en profundidad 2, sin respuestas erróneas emitidas |
| Diagnóstico de búsqueda | 4/4 con alfabeto acotado; comparación posterior sobre seis casos: 4/6 acotado frente a 0/6 completo; diagnóstico, no selección autónoma de gramática |
| Currículo por demanda | Adaptativo 32/32, aleatorio 32/32, secuencial 24/32; aprendizaje adaptativo más costoso y más temprano en varios pares; inconcluso |
| Custodia | Cinco auditorías válidas y diagnóstico posterior reproducido; no promoción |

Resultados, límites y siguientes intervenciones en
[el informe medido](REMEDIATION-RESULTS-20261011.md). Recibos en
`artifacts/remediation-pilot-20261011-r1/` y
`artifacts/remediation-grammar-autopsy-20261011-r1/`, sin modificar recibos de r3.
S6 queda aplazado hasta después de 5.5.
