# S6-B17 — implementación y seguimiento

Preparación del 4 de octubre de 2026. El contrato experimental está en
[ECHO45-S6-B17-DESIGN.md](ECHO45-S6-B17-DESIGN.md). Este documento de seguimiento
no forma parte de sus fuentes congeladas y puede recibir tiempos y resultados.

Lanzamiento confirmado: **4 de octubre, 23:57:26 Madrid**, servicio de usuario
`echoai-s6b17.service`, PID inicial 483025. Perfil congelado:
`5453471b3e747818ab122f55d49fc94a28934bae8b4356ad4ba2df495379b96b`, 192 fuentes.
Los nueve contextos superaron la cualificación con un máximo de 1662 tokens de
entrada, frente a 3072 permitidos. La ejecución arrancó con las 80 partidas de
paridad; la auditoría independiente está encadenada después del micro completo.
El visor de decisiones se lanzó tras crear el diario. Piloto, campaña y examen
no están ejecutándose bajo B17.

**Paridad completada a las 00:00:50 del 5 de octubre:** 80 partidas más sus
80 replays, 378 niveles, trayectoria completa idéntica y los 141 consumos
reales alineados con el contador anterior. El digest de la trayectoria anterior
se conserva: `4458a4c2e5f4d8ac6c46547fcbc62785e0aca93bd0bdecb6d23d7456d63c2d2c`.
La nueva telemetría no alteró el comportamiento de la base. Recibo:
`lab/seed/s6b17-20261004/parity.json`.

Ventana inicial orientativa desde ese arranque: micro entre las 01:30 y las
02:30 del 5 de octubre; micro auditado aproximadamente entre las 02:30 y las
04:00. Se revisará con los tiempos reales y las políticas reutilizadas en caché.

Se implementó un registrador pasivo sobre el observador existente. La prueba
de integración ejecuta una decisión real del actor y confirma que acción,
snapshot y diagnósticos anteriores coinciden exactamente con el observador
previo. Otra prueba coloca la consecuencia seis decisiones después del consumo
y comprueba que el contexto retenido corresponde al consumo, incluido un valor
cero de `pending_effect`, y no al punto posterior de divergencia.

El selector nuevo conserva los contraejemplos del linaje y puede elegir un
descendiente que reduce las pérdidas. Tiene un máximo de siete refinamientos
por raíz y evita que el selector heredado vuelva a abrir una raíz cerrada.
Las pruebas de ordenación usan valores sintéticos distintos de los casos que
motivaron el diseño; también comprueban invariancia ante reordenar la gramática.

La auditoría reconstruye los 24 intentos y repite sus candidatos válidos en otra
caché. Un test de transporte simula el circuito completo y después modifica un
veredicto: la reconstrucción lo rechaza. Otros tests detienen discrepancias de
medición y rechazan entradas protegidas antes de ejecutar. Una ganancia de
cuatro niveles con una pérdida de score sigue rechazada por V3.

Validación previa: 21 tests B17 y 18 de regresión B16/recovery aprobados. La
cualificación verifica nueve contextos con el tokenizador nativo, incluidos
objetivo parcial, mejor descendiente y formato de consecuencias diferidas.
Sus trazas temporales sintéticas son fixtures declarados; B16 no contenía esa
cronología y no se le inventan mediciones. No hay generación de respuestas ni
partidas de entorno durante esta cualificación.

Se corrigieron antes de congelar una ruta incorrecta al fixture B16
(`micro-records`, no `steps`), el retorno del selector heredado a un linaje
cerrado y un recibo compacto que carecía de leyenda en el prompt B17. Se conserva
el primer fallo de cualificación en `lab/s6b17-qualification-attempt1.log`.
Las correcciones no alteran fuentes ni resultados B16.

Estimación previa, pendiente de la calibración real de B17: los replays B16 sin
caché tardaron aproximadamente 100 segundos por bloque de 80 partidas con cuatro
workers; sus 24 llamadas al modelo promediaron 70,5 segundos. El techo B17 es de
4000 partidas primarias, 2000 de auditoría y 16 llamadas. Con el coste de
orquestación, una orientación inicial es 1,5–2,5 horas para el micro y 45–75
minutos para la auditoría, aproximadamente 2,5–4 horas en total. La caché puede
acortar este plazo; carga, suspensión y fallos pueden alargarlo. No es una
estimación para cerrar S6 ni para el examen reservado.

Al terminar el micro se conserva el resultado aunque sea negativo y se ejecuta
la auditoría independiente. Un híbrido que pasa A habilita preparar el protocolo
del siguiente piloto. Antes de campaña o examen todavía hacen falta conservación
protegida, ventaja contra FIJO y el resto de B1–B5. Un empate con el sintetizador
no prueba una aportación adicional del LLM.

El estado vivo se consulta en
`lab/seed/s6b17-20261004/status.json`; los resultados de cada intento estarán en
`steps/micro/`; `micro.json`, `micro-audit.json` y `closed.json` documentarán
las fases al completarse. El resumen del roadmap se actualizará automáticamente.
Se trabaja en local y no se publica código ni resultados en web/GitHub.
