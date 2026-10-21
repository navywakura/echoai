# ECHO-4.5: integración de memoria y solver, sin S6

2 de octubre de 2026. Nav cambia el orden: S6 queda aplazado y se priorizan
memoria→ARC, refinamiento, síntesis, vistas, consistencia y capacidad. Los
resultados y criterios anteriores de S6 permanecen intactos.

Se implementan módulos aditivos. `arc_memory.py` adapta el diario, la consulta
de evidencia, la reputación por resultados y la retirada de recuerdos de
EGO-MEMORIA-3E. Las pruebas privadas de la aldea no se trasladan a ARC. Cada
recuerdo nuevo contiene un programa y su reproducción exacta de demostraciones
permitidas. La política de acciones de la aldea no se considera transferida
por el solo hecho de importar su clase: se informa qué mecanismos intervienen.

`integrated_grid.py` busca programas reutilizando prefijos, retiene resultados
distintos sobre demostraciones e inputs de test, utiliza preimágenes de
transformaciones invertibles para refinar hipótesis y reserva una fracción del
presupuesto para vistas. No usa respuestas de test. La consistencia agrupa
predicciones de programas distintos; AMBIGUOUS permanece visible.

Los tres tamaños de guía comparados son 640, 65.536 y 500.000 pesos asociativos.
Cada guía aprende exclusivamente de los programas históricos verificados y
las demostraciones de sus tareas de entrenamiento. Se congelan esos recibos
y el estado del DSL S2v. Los pesos no son neuronas LIF. El tamaño mayor no se
selecciona como ganador por su nombre: se compara acierto y coste.

La primera fase es desarrollo público conocido: muestra determinista por hash
de ARC-1 y ARC-2 training, excluyendo el examen reservado del gimnasio y
todos los autores de los programas históricos usados para ajustar memoria y
guías. Se empieza por 16 tareas de cada banco para calibrar tiempo y descubrir
fallos de integración; después se amplía a 64 por banco. Los resultados del
desarrollo pueden orientar revisiones, cada una en un directorio nuevo. No se
presentan como un examen ciego ni permiten cambiar condiciones históricas.

Todos los brazos nuevos comparten techo de 2.000 programas, profundidad 4,
beam 12 y 96 comprobaciones adicionales desde la primera solución exacta.
Se registran programas, aplicaciones de primitivas, lecturas de memoria, caché,
tiempo CPU/pared y RSS. El estado de cada tarea empieza del mismo entrenamiento
congelado. No se aprende con respuestas de test ni entre tareas de evaluación.
El coste de adquisición se registra por separado y se incluye al comparar el
coste total. Las vistas tienen como máximo una quinta parte del techo de
programas; sus transformaciones se cuentan como trabajo.

Los brazos son: base sin los mecanismos nuevos, candidato completo, sin memoria,
sin refinamiento, sin vistas, sin consistencia, sin guía, guía 640 y guía 65.536.
El candidato completo emplea 500.000 unidades. El comparador conserva aciertos
y pérdidas por tarea. Si un módulo no aporta ventaja se informa y puede quedar
desactivado en el candidato recomendado; no se disfraza como verde científico.

Antes de una confirmación se fijarán fuentes y cohortes nuevas, tras el
desarrollo. Se exigirán los siguientes contrastes:

| Puerta | Condición |
|---|---|
| I1: ingeniería y custodia | Tests de etiquetas privadas, límites, memoria alterada, revalidación y replay pasan; fuentes S6/aldea sin cambios |
| I2: memoria funcional | En familias nuevas del generador, memoria mejora acierto o reduce al menos 20% del trabajo con igual acierto; retirada formativa perjudica más que retirada de igual tamaño ajena a la familia |
| I3: composición | Refinamiento resuelve más tareas compuestas que una pasada, sin pérdidas en las familias simples de control |
| I4: vistas y consistencia | Comparación independiente con/sin cada mecanismo, presupuesto común; no se atribuye ventaja por su mera implementación |
| I5: guía | Comparar los tres tamaños y sin guía; exigir mejora de aciertos sin pérdidas individuales para trasladar un verde de capacidad a esta configuración |
| I6: ARC público e integración | Confirmar utilidad en tareas ARC de desarrollo fuera del ajuste, con pérdidas y costes explícitos; el seguimiento conocido se separa de una reserva nueva |
| I7: auditoría | Otro proceso y caché nueva reproducen decisiones y resultados; atribución de cada mecanismo mediante ablaciones |

El verde de familias sintéticas tiene ese alcance. El verde completo de 4.5
sin S6 todavía requiere integrar habilidades previas y cumplir las puertas ARC
pendientes bajo un contrato de evaluación apropiado. Este trabajo no borra el
0/120 anterior en ARC-2 ni el 11/112 anterior en ARC-3. El aplazamiento de S6
no convierte automáticamente el resto del roadmap en completo.

Los diarios de desarrollo utilizan `echo_arc.observe.Journal`, con decisiones,
programas y resultados reales. Los exámenes nuevos y las auditorías se ejecutan
sin instrumentación de visor. No hay un segundo bus, LLM en NEXUS-0, entrenamiento
remoto, alquiler de GPU ni nuevas propuestas S6 en esta condición.
