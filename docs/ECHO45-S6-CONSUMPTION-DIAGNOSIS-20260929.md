# S6 · distinguir coincidencia de guarda y consumo real

Análisis posterior de **A de desarrollo**, sin acceso a reserva ni nuevas
llamadas al modelo. No se modifica B8 ni se reescriben sus veredictos.

El diagnóstico B8 decía que la propuesta ECHO `motor_ready=1 → HOLD=100`
cambiaba una configuración en 2410 decisiones. Era una oportunidad estimada,
no una lectura real del parámetro. La ejecución mostró cero acciones distintas
y cero ganancia. El modelo repitió esa propuesta al recibir feedback.

Al reconstruir las transiciones reales antes/después de `choose()` del actor
nativo encontramos **85 asignaciones de HOLD=40**, todas con `motor_ready=0`.
Se exige además una tecla de reinicio conocida en la cola y la acción que
ejecuta esa tecla. La guarda `motor_ready=1` coincide con **cero** de esas
asignaciones. Las otras propuestas HOLD sí coinciden, pero mantienen 40,
el valor ya existente. Los límites COOLDOWN propuestos tampoco reducían
las esperas visitadas. Esto explica los doce rechazos sin culpar a V3/V4.

Se añadió `echo_arc/consumption_evidence.py`, con cuatro pruebas que pasan:
distingue retorno temprano de asignación, valor nativo de cambio de espera,
rechaza inferencias a partir de acciones no relacionadas y excluye B o
políticas modificadas. Se aplicó a los 40 diarios nativos A y conserva sus
hashes de procedencia. **Diagnóstico preparado y comprobado, no integrado en
los prompts B8 congelados ni demostrado como mejora del agente.**

Límites: prueba dónde se asignó HOLD en esa trayectoria nativa. No predice
trayectorias nuevas ni generaliza automáticamente a otros parámetros o a
políticas ya reparadas. Incluso cambiar la espera no demuestra mejorar una
acción o un nivel. Sigue siendo necesario ejecutar V1–V4.

Próxima condición de investigación: utilizar consumidores observados, con
el mismo acceso y presupuesto para ambos brazos, al seleccionar evidencia y
restringir propuestas demostrablemente inactivas. Deberá declararse cómo se
registra el consumo con políticas reparadas y qué controles separan selector
y feedback. No se aplica retroactivamente a B8 ni abre reserva por sí sola.

[Datos y procedencia](../lab/seed/s6b8-20260929/consumption-review-v2.json) ·
[Resultado parcial B8](ECHO45-S6-B8-RESULTS.md).

## Comprobación directa completada

`echo_arc/consumer_observe.py` observa las líneas realmente ejecutadas que
leen HOLD y aplican COOLDOWN_CAP. Usa el diario existente; no cambia el actor
ni consulta el estado privado. También admite políticas reparadas y reconoce
la lectura de HOLD=0, aunque no cambie el valor de la espera. Rechaza reemplazar
otro trazador y lo restaura si falla el actor. Seis pruebas pasan, incluida
igualdad de partidas completas con/sin observador para tres políticas.

Repetición de **40 partidas A conocidas**, sin modelo ni reserva: paridad
exacta del comportamiento, 178 niveles y **85 lecturas HOLD**. Confirma el
análisis previo por transiciones. [Recibo](../lab/seed/s6-consumers-20260929/summary.json).

Matiz: el actor nativo no lee COOLDOWN_CAP porque el parche introduce esa
operación. Cero lecturas nativas de ese control **no prueba** que un parche
que lo introduce sea inactivo. La evaluación debe distinguir lectura existente,
operación nueva, cambio de acción y mejora final. Los veredictos anteriores
siguen sustentados en ejecución, no en este observador.

Se prepararon `consumer_requests.py` y `parameter_first_grammar.py` para una
condición posterior. El modelo elegiría primero el parámetro y después la
guarda, con el mismo lenguaje y valores expresables de B5; ambas peticiones
recibirían observaciones de consumo del mismo tipo. ECHO seleccionaría casos
cercanos a resolver con lecturas observadas, y FIJO conservaría la selección
genérica. Tres pruebas verifican el lenguaje, selección y exclusión de campos
privados. **Preparado y probado; todavía no integrado en una campaña ni medido
como mejora de ECHO.** B8 y su continuación CPU mantienen sus prompts fijados.
