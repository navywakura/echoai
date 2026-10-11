# ECHO-5 · checkpoint de investigación del 11 de octubre de 2026

**ECHO-5 todavía no está en verde.** Este corte publica código, documentación y
evidencia seleccionada de una implementación en investigación. No anuncia un
release final ni un pase de S6. El paquete de terminal continúa en 4.5.0b1 y
ECHO-5 mantiene su entorno de desarrollo separado.

El runtime implementa representación de objetos y relaciones, programas tipados,
conceptos reutilizables, composición jerárquica, planificación e interacción.
También incluye currículo por contraejemplos, controles MiniGrid/BabyAI,
integración del razonador con MissionAgent y un panel web local de decisiones.
El currículo usa problemas verificables y comparaciones controladas; no entrena
una GAN ni modifica pesos de un LLM.

Estos son los resultados de la confirmación cognitiva r1. Su auditoría se
ejecutó en procesos independientes y tiene `valid: true`; esa validez no
convierte todas las puertas científicas en positivas.

| Componente | Resultado registrado | Alcance y límite |
|---|---|---|
| Objetos y relaciones | 48/48 casos compatibles; abstención en 24/24 controles | 12 ambiguos y 12 fuera del lenguaje; familias sintéticas reservadas, sin puntuación ARC oficial |
| Conceptos y memoria | 16,91 % menos trabajo que biblioteca vacía; 3,24 % más que fija | Incluye adquisición; cumple el margen prerregistrado, sin superioridad sobre biblioteca fija |
| Composición y prefijos | 57,79 % menos trabajo por reutilización de prefijos | Conserva respuestas dentro del banco evaluado |
| Currículo adaptativo | 256/256; aleatorio 201/256; secuencial 152/256 | 32 ejecuciones emparejadas y costes contabilizados; sin LLM |
| MiniGrid/BabyAI | 54/56; fijo 0/56; pasivo 0/56; sin memoria 20/56; sin planificación 6/56 | Entornos y presupuestos especificados; no investigación abierta sobre tareas arbitrarias |
| MissionAgent en simulación discreta | 4/12; convencional 3/12; horizonte uno 4/12 | Integración software; empate con el control de horizonte uno |
| Gazebo/PX4, confirmación r1 | 17/18 recibos válidos; ECHO 2/3 misiones nominales, convencional 3/3 | Resultado negativo: llegada fallida y fallo de observación/recuperación en batería baja |

La [selección de recibos](../research-archive/20261011/README.md) conserva tanto
la confirmación cognitiva válida como la confirmación SITL fallida. Las tablas
de capacidades no sustituyen a los denominadores, controles y gates registrados.

La corrección posterior investiga un sesgo de velocidad vertical del estimador
y el cierre seguro tras una excepción del adaptador. La calibración permanece
separada del examen; una regresión unitaria o un vuelo favorable no basta para
abrir la siguiente fase. El estado fechado publicado en el archivo muestra la
ejecución observada, no un servicio de estado en vivo. Si aparece un recibo
inválido, la cadena debe detenerse antes de la batería dependiente.

El [checklist](../ECHO-5/docs/CLOSURE-CHECKLIST.md) y el
[diagnóstico robótico](../ECHO-5/docs/SITL-CONFIRMATION-R1-DIAGNOSIS.md) detallan
lo que falta. La confirmación nueva necesita casos nuevos, auditoría válida y
un finalizador que mantenga los umbrales del contrato. No se acredita hardware
real por una prueba Gazebo/PX4. S6 permanece fuera del cierre de esta versión,
pendiente de investigación después de ECHO-5.5.

El proyecto [echounity](https://github.com/navywakura/echounity) añade un mundo
isométrico observable: cámara del robot, rayos de profundidad, odometría,
cartografía acumulada y un modelo acotado de los efectos de sus comandos.
El evaluador CPU de navegación r2 obtuvo 16/16 frente a 15/16 desde cero y
0/16 sin mapa persistente. Sus capturas y recibos pertenecen a esa evaluación;
no se suman al examen de Gazebo/PX4 ni demuestran visión RGB aprendida.

El panel expone observaciones, hipótesis, acciones y consecuencias registradas.
Su diagnóstico LIF es una visualización separada del controlador. Las 500.000
unidades del banco asociativo histórico son contadores, no 500.000 neuronas LIF.
No se declara conciencia, ausencia universal de alucinaciones ni ahorro de
energía sin medirlo.

Esta publicación adapta importaciones a la distribución pública, cuya raíz ya
contiene `core/`. Los hashes de los experimentos siguen identificando las
fuentes originales del laboratorio; las pruebas del paquete publicado se
registran aparte. No se han editado las fuentes congeladas del ensayo activo.
Los archivos personales, credenciales, configuración de asistentes y entornos
temporales quedan fuera. [Detalles de distribución](DISTRIBUTION.md).
