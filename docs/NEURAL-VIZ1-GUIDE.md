# Tutorial de NEURAL-VIZ-1

Esta aplicación observa ECHO-2 mientras ejecuta Agent.turn(). La inteligencia
rápida sigue en CPU y usa enteros. VTK/OpenGL utiliza la GPU para dibujar el
dron, el mapa descubierto y la escena 3D. La GPU gráfica no decide acciones ni
simula aerodinámica.

## Qué animal estás viendo

El cuerpo actual es PULPO/Body3D: un agente abstracto con posición x,y,z y seis
rumbos (+X,+Y,+Z,-X,-Y,-Z) dentro de 3×3×3 voxeles. La pestaña Dron 3D lo
representa como un cuadricóptero porque el destino del proyecto es robótica al
edge. Sus tres acciones reales siguen siendo approach (avanzar), avoid (cambiar
el rumbo) y wait (mantenerse). Todavía no modela empuje, masa, viento, IMU,
hélices o PID; añadir esos sensores y dinámica será una fase de simulación de
vuelo, no una afirmación sobre el banco actual.

El dron se mueve solo. La GUI nunca pulsa una acción por él: muestra la salida
de Q y el veredicto del gate. Los puntos del mapa y la estela proceden de poses
observadas. Una tarea sin x/y/z muestra «sin pose» en vez de inventar un mundo.

## Por qué muchos WSP dicen OBSERVAR

WSP describe la percepción del turno, no el verbo ejecutado. En Body3D casi
todos los voxeles transitables son EMPTY, por eso el paquete dice
YO → OBSERVAR → AQUI. Debajo puede verse que Q eligió approach o avoid. Cuando
el cuerpo percibe GOAL, THREAT, NOVEL, OBJECT o CLOSED aparecen DESEAR, TEMER,
DESCONOCIDO u otros destinos. La pestaña Mapa WSP muestra las seis conversiones
de celda y todos los átomos definidos.

Un WSP ocupa exactamente 16 bytes: cuatro átomos (src, rel, dst, time), seis
valores corporales E[V,A,D,C,U,B] y seis bytes de flags/extensión. No existen
«16 estados»: existen 16 posiciones binarias con funciones distintas. Cada
posición puede contener los valores que permite su tipo.

## Cómo leer la red neuronal

WSP 16 B son los bytes de entrada. LIF 256 HI y LIF 256 LO son los dos bancos
importados que forman la prueba CAPACITY-1 de 512 LIF. El brillo indica cuántos
spikes emitió cada neurona para el WSP actual. Adaptive-LIF 128 mantiene estado
temporal entero; rosa intenso significa spike y rosa tenue refleja adaptación.

CAM → Q muestra las tres salidas de política. El amarillo más fuerte es la
acción ejecutada. GATE aparece verde al entregar la acción física. Puedes
orbitar la red arrastrando y acercar con la rueda.

La rama LIF/Adaptive-LIF está rotulada «monitor». CAPACITY-1 demostró su mejora
perceptiva, pero el Agent actual todavía decide mediante CAM/Q/gate. La GUI no
dibuja una conexión falsa desde Adaptive-LIF hasta Q.

## Memoria, predicción y aprendizaje

CAM guarda episodios WSP sin destruir ranuras. «slot» identifica la memoria
asociada al estado y «usadas/4096» indica ocupación.

T aprende T(estado,acción) → siguiente estado. pred es su predicción; filas es
el número de transiciones observadas y conflictos cuenta sucesores que no
coincidieron con el incumbente.

PATTERN usa contexto temporal de orden dos cuando la tarea lo activa. Aprende
regularidades que T de un solo paso no distingue. OFF significa que esa tarea
ha elegido el camino base, no que la aplicación haya perdido el módulo.

Q contiene un valor entero por acción. Reward es la consecuencia física y ΔQ
es el cambio real de la entrada elegida. Las líneas verdes del diario son
turnos donde Q cambió.

GATE compara la propuesta con certeza, amenaza e inhibición. Veredicto 0 es OK,
1 es MODIFY y 2 es BLOCK. La acción ejecutada puede diferir de la propuesta.

SLEEP-2 se ejecuta periódicamente fuera del paso rápido. Lee CAM y T y produce
reglas compactas; no borra ni reescribe las memorias fuente.

## Vida, muerte y herencia

H es vitalidad entera. Temperatura es la variable homeostática de HEAT-1b,
también entera y abstracta: no es la temperatura de tu CPU. En la tarea HEAT,
H=0 o temperatura 0/127 termina la vida; después hay respawn conservando la
memoria del individuo.

En GEN-1f cada acción termina una vida. Cada 48 muertes se llama al
spawn_child() real. El hijo hereda sólo evidence_budget=8 y nace con CAM, Q y T
nuevas. El evento NACIMIENTO y el contador G permiten grabar ese instante.

## Córtex y ATTEND

El córtex no se llama periódicamente. ATTEND lo despierta sólo cuando el camino
rápido tiene un miss, baja confianza, novedad, mapa ausente o conflicto. Tras
leer una señal una vez, Q/T pueden resolverla y ATTEND queda en silencio. Una
única llamada es el comportamiento esperado del sistema de dos relojes, no un
fallo del contador.

En muestra DESPIERTA/silencio y la razón de cada turno. CÓRTEX cuenta llamadas
acumuladas. LLM ENTRADA enseña el extracto que el mundo entregó; LLM SALIDA
enseña el WSP que sobrevivió a la gramática y parse_reply. No se muestra un
chain of thought privado: se muestran la entrada, salida, razón, propuesta,
gate y consecuencia que sí pueden auditarse.

Para repetir la demostración Qwen, selecciona «CORTEX-1 · Qwen lee una señal»
y pulsa Ejecutar. Esto crea un agente nuevo y vuelve a producir el primer
despertar. En CPU una inferencia puede tardar cerca de un minuto; la GUI debe
seguir orbitando y mostrar CÓRTEX/LLM OCUPADO durante la espera.

## Tareas y controles

El desplegable elige una tarea y Ejecutar crea un agente nuevo. Pausa detiene
los ticks, Paso ejecuta exactamente un turno y el deslizador cambia ticks por
segundo. Abrir JSON permite cargar otra tarea declarativa sin añadir ramas de
escenario a la GUI.

GUI-3.5 cuerpo 3D muestra navegación, PATTERN, CAM, T, Q y SLEEP desde cero.
HEAT-1b muestra regulación térmica, muerte y respawn. GEN-1f muestra vidas y
herencia. CORTEX-1 muestra el cable local hacia Qwen y el firewall WSP.

La pestaña Red neuronal sirve para estudiar decisiones. Dron 3D sirve para ver
la pose autónoma y el mapa observado. Mapa WSP sirve para decodificar cada byte.
Tutorial documenta los límites para que una grabación no atribuya al sistema
capacidades que todavía no tiene.

## Evolución prevista después de ECHO-3

La ampliación a tres mundos, vuelo con IMU/motores/PX4, aerodinámica, viento,
órdenes personalizadas y exámenes fuera de muestra está guardada en
[POST-ECHO3-DRONE-METAVERSE.md](POST-ECHO3-DRONE-METAVERSE.md). Es una fase
futura: nada de ese documento debe aparecer como capacidad actual de esta GUI.
