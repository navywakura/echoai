# S6 · por qué sigue rojo y qué significa el verde

29 septiembre 2026. Investigación posterior al cierre auditado de B10.
Se analizaron código, contratos y artefactos existentes. Cero llamadas nuevas
al modelo, cero partidas nuevas y ningún examen reabierto. Este informe no
cambia un veredicto ni los criterios de las condiciones cerradas.

**Hallazgo principal:** B10 produce mejoras reales de niveles en desarrollo,
pero todas fallan el requisito de no perder puntuación en ninguna partida
individual. La pérdida concreta es de eficiencia, no de niveles resueltos.
Además, el refinamiento explora poca diversidad de conducta y no demuestra
ventaja de ECHO sobre FIJO. Una auditoría correcta certifica este resultado
negativo; no lo convierte en una mejora.

## Dos ensayos distintos bajo el programa S6

El S6-A original generaba operaciones para rejillas: 300 peticiones por brazo
y 201 tareas reservadas. Cerró rojo. S6-B pasó a estrategias acotadas en juegos
sintéticos, primero sobre v5.7 y después sobre v5.8. Los identificadores
B0–B10 son revisiones del experimento; B1–B5 también nombran sus cinco criterios
finales. Conviene explicitar cuál de los dos sentidos se usa.

B10 permite únicamente `REVALIDATE_NOOP=1..8` bajo condiciones observables.
No entrena los pesos de Qwen, no inventa un algoritmo arbitrario y no ejecuta
el selector completo de cuatro clases de petición del S6-A inicial. Su brazo
ECHO selecciona fallos mediante una heurística y recibe el historial de sus
intentos. El experimento aísla esta intervención y su selección de evidencia.
El actor se inicializa de nuevo en cada partida; entre rondas persisten el
programa aceptado y el historial, no una mente que haya acumulado todo el juego.

## Qué exige el contrato actual

Primero una propuesta tiene que superar seguridad/formato (V1), ejecución y
repetición determinista (V2), ganar al menos dos niveles A sin ninguna pérdida
individual de niveles o puntuación A (V3), y no perder niveles ni puntuación
en ninguna partida B (V4). La tolerancia numérica de puntuación es `1e-10`.

A y B contienen 40 partidas y 200 niveles posibles cada uno. Solo A se muestra
al modelo; de B recibe una señal de rechazo. El piloto tiene tres parejas de
semillas de muestreo: **534 = 178 + 178 + 178**, políticas medidas en el mismo A;
no son 534 tareas ARC independientes. Para promover, ECHO debe aceptar al menos
una mejora y superar la suma A de FIJO. Después vienen campaña, auditoría,
congelación de las cuatro políticas y examen nuevo.

| Criterio final | Condición exacta | Qué pretende demostrar |
|---|---|---|
| B1 | ECHO obtiene ≥105% de los niveles de SEMILLA y su puntuación media no baja | Mejora con ayuda del modelo |
| B2 | ECHO resuelve más niveles que FIJO | Valor adicional de la selección/petición de ECHO |
| B3 | ECHO resuelve más niveles que SIN FILTRO | Valor adicional de verificar utilidad y conservación |
| B4 | ECHO conserva niveles y puntuación agregados en los ocho juegos oficiales de desarrollo | Conservación fuera del banco sintético |
| B5 | Procedencia, fuentes, propuestas, decisiones, solucionador y replays son verificables | El resultado es reproducible y no depende de filtrar información del examen |

Los cinco deben cumplirse juntos. En B10 la reserva sería 24800–24859, dos
versiones y tres repeticiones: 360 partidas/1800 niveles por brazo. Sigue sin
abrir. La auditoría válida del piloto no es todavía B5 de un examen final.
Un verde S6 tampoco equivale a una puntuación concreta en ARC-AGI-1/2/3 oficial.

Fuentes: [contrato B10](ECHO45-S6-B10-DESIGN.md),
[verificador](../seed/game_selfimprove_b5.py),
[comparación individual](../seed/game_selfimprove_b3.py),
[criterios finales](../seed/s6_precise_exam.py).

## Lo que falló en las distintas etapas

| Etapa | Evidencia documentada | Problema localizado |
|---|---|---|
| S6-A | SEMILLA/FIJO/ECHO 24/201; SIN FILTRO 25/201; cero aceptaciones | Las propuestas no resolvían los casos de la criba. Se rechazó una operación que después sí transfirió a una reservada. Los filtros también pueden descartar utilidad. |
| B0/B1 | B0: 60 propuestas inválidas; B1 se detiene en calibración | Protocolo de salida: respuestas truncadas, claves/condiciones inválidas. No se llegó a probar utilidad. |
| B2 | FIJO y ECHO mejoran A 56→62, pero convergen a la misma política; examen: 1350 frente a SEMILLA 1387 | Falta de ventaja del selector y generalización negativa; proteger totales ocultaba regresiones individuales. |
| B3 | ECHO=FIJO=SEMILLA 1668; SIN FILTRO 1586 | Verificar evita degradación, pero no aparece mejora sobre la base ni ventaja sobre FIJO. |
| B4/B5 | Cero aceptaciones; controles globales mejoraban unas partidas y empeoraban otras; algunos controles precisos humanos sí pasaban | Alcance de los cambios demasiado amplio y propuestas poco útiles dentro del espacio permitido. |
| B6/B7 | B6: FIJO 537 > ECHO 534. B7: una mejora ECHO aceptada +3, empate 537–537 | Hubo una mejora autónoma verificada en B7; faltó superar la ayuda genérica. |
| B8/B9 | Propuestas repetidas o sin efecto. B9: las 18 condiciones no coincidían con ninguna de 2654 contradicciones observadas | Confundir que una condición pueda activarse con que modifique una operación realmente ejecutada. |
| B10 | Las 18 propuestas ganan +8 A; todas rechazadas V4 | Intervenciones aplicables, pero mismo coste de eficiencia en una partida B; poca diversidad funcional y refinamiento insuficiente. |

Son cohortes y condiciones diferentes. Las cifras de filas distintas no
constituyen una curva de progreso comparable ni una puntuación ARC oficial.
El B8 original quedó parcial por infraestructura; su continuación CPUQ8
declarada terminó sin promoción. No se reetiqueta el primero como completo.

El cambio de conservación agregada a conservación individual se documentó
en B3, tras los problemas de B2. Es una exigencia más fuerte; no apareció
accidentalmente durante B10. [Histórico B0–B2](ECHO45-S6-B-RESULTS.md) ·
[S6-A](ECHO45-S6-RESULTS.md) · [B3](ECHO45-S6-B3-RESULTS.md) ·
[B4](ECHO45-S6-B4-PILOT-RESULTS.md) · [B7](ECHO45-S6-B7-RESULTS.md) ·
[B9](ECHO45-S6-B9-RESULTS.md).

## La regresión exacta de B10

Las 18 propuestas producen A **178→186**: +8 niveles, +4,49% relativo.
**Ninguna pierde niveles en ninguna partida A ni B.** Todas mejoran también
los niveles y la puntuación agregados de B. Sin embargo, todas empeoran
ligeramente la puntuación de la misma partida B, que sigue resolviendo 5/5.

| Medida de esa partida | Base | Propuestas B10 |
|---|---:|---:|
| Niveles resueltos | 5 | 5 |
| Acciones para el último nivel | 737 | 843–951 |
| Puntuación de la partida, escala 0–100 | 2,845294 | 2,841152–2,842850 |
| Caída relativa de esa puntuación | — | 0,0859–0,1456% |

Es una pérdida determinista de eficiencia, no ruido de redondeo: el umbral
`1e-10` no la permite. Por ejemplo, la primera propuesta sube B 181→189 y
su suma de puntuación 1692,3531→1715,5542, pero falla V4 por esa partida.
La regla vigente exige una mejora que no empeore ningún caso; no admite
compensar una pérdida individual con otras ganancias. Por eso «cero aceptadas»
no significa «cero propuestas con utilidad».

El operador modifica la predicción de una transición y borra el plan pendiente
tras observar acciones sin cambio. La base solo actualiza esas transiciones
al observar movimiento. La reparación permite abandonar predicciones obsoletas;
también puede cambiar una trayectoria que ya alcanzaba la meta. Los registros
demuestran el cambio y su coste. No identifican por sí solos una razón interna
del LLM ni prueban que cada revisión de transición fuera conceptualmente errónea.

El +4,49% anterior es de desarrollo. No demuestra ni refuta el requisito de +5%
en otra cohorte reservada que no se ha medido.

## Por qué el refinamiento actual se queda corto

1. **Novedad de texto no equivale a novedad de conducta.** Hay 13 programas
   distintos entre las 18 respuestas, pero solo **seis comportamientos**
   distintos en A y también en A+B, comparando acciones, frames, niveles,
   puntuación y reinicios. Cambiar una condición por otra no siempre cambia
   dónde actúa el parche. Cuatro de nueve parejas FIJO/ECHO producen el mismo
   comportamiento completo en estas partidas.
2. **La evidencia de tareas no se renueva tras cada rechazo.** Cada uno de
   los seis actores recibe el mismo conjunto de observaciones en sus tres
   peticiones. Cambia su historial de intentos, pero la selección sigue usando
   la política aceptada, que permanece vacía. Las peticiones no incluyen una
   comparación causal detallada de las trayectorias de los candidatos fallidos.
3. **La protección produce feedback deliberadamente escaso.** El modelo sabe
   que ganó niveles A y que B lo rechazó; no recibe el caso B, sus acciones ni
   el detalle de eficiencia. Esa separación protege los datos, pero limita
   la información disponible para localizar cuándo debe abstenerse de aplicar
   una reparación. La solución de investigación es aportar contraejemplos de
   desarrollo, no convertir la reserva/protección en ejemplos para el modelo.
4. **El espacio puede expresar una reparación conservadora.** Un control
   humano anterior consiguió +8 A sin ninguna pérdida A/B y pasó su auditoría.
   Se comprobó que ese programa era legal en las 18 gramáticas B10. Ninguna
   respuesta usó `stagnation`, una señal temporal presente en el control.
   Esto descarta que el lenguaje estuviera imposibilitando ese control;
   no permite atribuir su descubrimiento a ECHO ni introducirlo a posteriori.

Los tres primeros puntos y la disponibilidad del control son comprobaciones
de artefactos/código. Que un modelo mayor, otro prompt o más muestreo resuelva
el atasco sigue siendo una hipótesis. No se midió esa comparación.

## Por qué ha consumido tanto tiempo

B10 deja **4320 registros finales de partida** entre evaluación, replays y
auditoría independiente: cada propuesta distinta se prueba sobre baterías
completas; la auditoría las reconstruye con otra caché. Hubo además descargas
fallidas, problemas de memoria/caché de inferencia, agotamiento de GPU gratuita,
continuaciones CPU, desconexiones y recuperación del apagado. Son costes de
ejecución y custodia. No explican ni eliminan las regresiones ya reproducidas.

Las auditorías sirven para confirmar un resultado; no siguen entrenando al
agente hasta que mejore. Esperar más después de un cierre negativo no cambia
la política. [Recuperación B10](ECHO45-S6-B10-RECOVERY.md).

## Próximo experimento que justificaría continuar

**Propuesta, todavía no implementada ni lanzada como B11.**

- Declarar claramente si el objetivo exige conservar también la eficiencia
  de cada partida o conservar capacidades y rendimiento agregado. B10 mantiene
  su rojo. Cualquier criterio distinto exige un contrato nuevo antes de medir;
  no se elige una tolerancia para hacer pasar la pérdida ya observada.
- Construir un conjunto de desarrollo más amplio con casos de progreso,
  bloqueos y éxitos que proteger. Devolver al refinamiento diferencias reales
  entre la conducta anterior y la propuesta, incluyendo regresiones encontradas
  en ese desarrollo. No mostrar B ni una reserva al modelo.
- Medir diversidad de acciones/resultados sobre A además de diversidad del
  JSON, contabilizando todos los intentos y conservando igual presupuesto
  para FIJO/ECHO. Evitar gastar rondas en cambios de forma con el mismo efecto.
- Separar mediante controles el valor de escoger evidencia, el texto de la
  petición y el feedback. Ambos brazos deben tener el mismo modelo, operaciones
  y acceso a información; una ventaja de ECHO debe medirse, no suponerse.
- Exigir una reparación del modelo aceptada y ventaja reproducible sobre FIJO
  antes de campaña/examen. Congelar después las cuatro políticas y medir B1–B5
  en una reserva nueva. La evaluación ARC oficial se realiza por separado.

El análisis de conservación aquí expone detalles de B. Una condición nueva
no debe usar ese caso para fabricar reglas específicas ni tratar el mismo B
como una protección nunca inspeccionada. Debe declarar el historial y fijar
una protección fresca; las cohortes reservadas anteriores siguen cerradas.

## Reproducción y evidencia

```sh
lab/arc3/ARC-AGI-3-Agents/.venv/bin/python -m seed.s6b10_diagnose
```

El analizador solo lee los artefactos existentes y escribe su informe.
Comprueba hashes de fuentes, trazas y veredictos; conserva los hashes de todos
sus archivos de entrada. No ejecuta juegos ni inferencia. La equivalencia de
conducta está limitada a las partidas medidas; no afirma equivalencia global
entre programas.

[Datos del diagnóstico](../lab/seed/s6b10-diagnosis-20260929/report.json) ·
[Analizador](../seed/s6b10_diagnose.py) ·
[Cierre B10](ECHO45-S6-B10-RESULTS.md) ·
[Control humano](ECHO45-S6-TRANSITION-RESULTS.md).
