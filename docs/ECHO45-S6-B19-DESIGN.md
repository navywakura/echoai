# S6-B19 — conservar el coste antes de promocionar

Condición nueva y privada del 5 de octubre de 2026. B18 permanece cerrado y
rechazado por sus dos regresiones de puntuación. Este contrato se congela con
las fuentes antes de la primera propuesta B19. No autoriza el examen final.

El diagnóstico previo consta de 132 partidas de desarrollo retrospectivo y
la reconstrucción de ocho trayectorias ya guardadas. Diez duraciones HOLD,
con la guarda ganadora B18 fija, no encuentran mejora suficiente sin pérdidas
en el cribado. Los datos consumidos de B18 se incorporan explícitamente al
desarrollo; no vuelven a considerarse protegidos ni ciegos.

HOLD inhibe nuevos reinicios deliberados. No representa una espera inmóvil.
En H4, reiniciar sustituye una copia que reproduce una trayectoria. La copia
puede estar moviéndose o sosteniendo una puerta. `pending_effect=0` solo
indica que `_tried_at` está vacío; no certifica que reiniciar sea inocuo.
No se entrega el estado privado del simulador a ECHO ni al LLM.

Se corrigen tres limitaciones del buscador en un módulo separado. Una vez
que la cobertura estimada alcanza los dos niveles requeridos, el ranking
prioriza reducir intervenciones asociadas a pérdidas, aunque sacrifique una
ganancia adicional. Conserva todas las lecturas realmente modificadas,
incluidas las tardías, pero no considera una lectura con el valor basal
como otra intervención del parche. Cada tercer refinamiento prueba también
una duración menos agresiva de la escala 0,1,2,4,8,12,16,20,24,32,40; el resto
refina las guardas manteniendo el valor. La escala limita búsqueda, no altera
la gramática ni el umbral de aceptación. El ranking sigue siendo una
heurística: ninguna inferencia sobre trazas sustituye una partida real.

Los tres brazos tienen el mismo cribado dirigido de doce casos: A18, A42,
A51, A53, A59, A68, A76 y A77, más v3/28026, 28027, 28031 y 28039 consumidos
de B18. El punto de partida es el programa aceptado B14 de 378 niveles en
su A original, con su historia aceptada; el paquete no contiene la guarda
B18 ganadora ni registros de PROBE. El conocimiento humano del diagnóstico
y la selección dirigida del cribado quedan declarados.

| Brazo | Primera propuesta | Refinamientos |
| --- | --- | --- |
| guard_only | LLM | Buscador B18, solo guardas |
| synth | Núcleo determinista | Buscador B19, coste y valor |
| hybrid | La misma respuesta LLM que guard_only | Buscador B19, coste y valor |

Cada brazo dispone de doce oportunidades, sin transferir las sobrantes a
otro brazo. Se detiene al primer candidato que gana al menos dos niveles en
el cribado sin perder nivel o score en ninguno de sus casos. Se mide cada
propuesta en los doce casos y en un replay completo. Otro proceso, con
caché separada, reconstruye peticiones, respuestas, trayectorias y veredictos.
La generación inicial cuenta como una oportunidad en ambos brazos y una
sola llamada física compartida. No se remuestrea durante la auditoría.

Se usa el Qwen3-4B-Instruct-2507 Q4_K_M y el runtime CUDA cualificados de B18,
con los mismos hashes, temperatura y límites de contexto/salida. Semilla de
generación 790101. GPU T4 gratuita de Kaggle; cuatro procesos CPU para juegos,
Python 3.12.13, numpy 2.3.2, arcengine 0.9.3. Máximo una llamada física al
modelo y 6000 partidas físicas. Ni servicios de pago ni publicación de código.

Si hybrid supera el cribado y su auditoría, el primer ganador de cada brazo
se congela y se contrasta sobre 160 partidas de desarrollo completas:
80 históricas A (v2/v3, semillas 0–39), las 40 consumidas B18 (28020–28039)
y 40 adicionales (31000–31019), siempre repetición 0 y 2000 decisiones.
Se exigen al menos dos niveles de ganancia total y cero pérdidas individuales
de niveles o score, con tolerancia 1e-10; replay completo y auditoría
independiente. No se escoge otro candidato si falla esta ampliación.

Solo si hybrid supera también esa fase se abre B nuevo, antes no medido:
80 partidas, versiones 2 y 3, semillas 31100–31139, repetición 0, presupuesto
2000. Se miden la base y los primeros candidatos que hayan pasado toda la
cualificación. Cero pérdidas por partida, replay íntegro y nueva ejecución
independiente son obligatorios. No se envían resultados B al buscador ni se
vuelve a elegir una política después de verlos. Este B es distinto de todos
los bloques previos revisados en las fuentes S6; el examen continúa separado.

Los doce casos de cribado usan el diario observable existente. Las partidas
de ampliación y B se ejecutan sin añadir observación. Se guarda cada fila
con su hash antes de borrar diarios efímeros. Una discrepancia, fuente
cambiada, contexto inválido o interrupción ambigua detiene el instrumento;
nunca se cuenta como un resultado negativo de ECHO. Las auditorías usan
procesos y cachés diferentes y exigen igualdad de filas completas.

El éxito acreditaría conservación en este nuevo bloque, dentro de este
banco procedural. No acreditaría todavía ventaja causal del LLM, mayor
puntuación ARC oficial ni automejora general. S6 necesita posteriormente el
piloto emparejado, campaña y examen de cuatro brazos B1–B5. Si synth iguala
al híbrido, se informa del empate. Ninguna rama de este runner abre el examen
o declara `s6_green=true`.
