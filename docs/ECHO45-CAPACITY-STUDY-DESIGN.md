# ECHO 4.5 banco de capacidad y visualización

2026-10-01. Comparación exploratoria de desarrollo posterior a CAPACITY-500K.
Se mantienen intactos S6-PROBE1, sus fuentes y los exámenes reservados.

## Pregunta y alcance

¿Cuánto aporta ampliar la memoria asociativa que orienta la búsqueda de
programas, y basta una capacidad intermedia? No se amplía el núcleo LIF ni
se entrenan pesos del LLM. La representación 3D es una disposición gráfica
de asociaciones reales, no anatomía, actividad eléctrica ni pensamiento.

Se comparan base sin guía y guías de 640, 4.096, 16.384, 65.536 y 500.000
pesos de un byte. Los rasgos, programas de entrenamiento, DSL, solver,
presupuesto y verificador son los mismos que en CAPACITY-500K. No se afirma
que aumentar capacidad cree nuevas operaciones.

## Datos y presupuesto

Se reutilizan exactamente los 60 programas verificados y las 250 tareas de
desarrollo del perfil `lab/seed/capacity500k-arc1-20260930/profile.json`.
Estos datos ya son conocidos; este ensayo no es un nuevo examen ciego ni
una puntuación oficial ARC. Solo se permiten IDs de desarrollo presentes
en ese perfil. Nunca se leen el holdout del gimnasio ni ARC evaluation.

Una respuesta por tarea, profundidad 4, máximo 400 expansiones, cero LLM.
Las respuestas de test se eliminan antes de pasar una tarea al solver.
Todas las nuevas mediciones tienen un replay completo en otro proceso.
Una discrepancia detiene el estudio. No se selecciona tamaño por un caso
favorable: se miden las 250 tareas completas de cada nuevo brazo.

Los 750 resultados y 750 replays originales de base/640/500k se importan
solo después de comprobar igualdad determinista, hashes, cobertura y
presupuesto. Los tres brazos intermedios requieren otras 750 resoluciones
y 750 replays. Los resultados importados conservan su fecha y procedencia.
Las comparaciones de CPU entre lotes son descriptivas; no constituyen una
prueba de aceleración. El renderizado nunca entra en los cronómetros.

Antes de jugar se congelan contrato, ejecutor, pruebas, fuentes originales,
datos y estado por SHA-256. Dos workers como máximo, con prioridad reducida.
La ejecución larga espera a `S6-PROBE1: DONE` y a un resultado sin fallos de
replay. Si S6 está bloqueado no se interpreta como una finalización válida.
Resultados parciales nunca se publican como un brazo auditado completo.

## Métricas

Aciertos exactos por tarea, diferencias apareadas frente a base y 640,
ganancias y pérdidas por ID, expansiones, aplicaciones DSL, CPU, bytes de
pesos y pesos no cero. La CPU no incluye la preparación de las guías.
Se conserva el tiempo de entrenamiento por separado. El RSS heredado de
workers no se presenta como memoria aislada de un brazo.

Un control sintético reproduce las cuatro transformaciones geométricas del
banco anterior: 80 ejemplos de entrenamiento y 40 de desarrollo, cinco
capacidades. Se publica como clasificación top-1, separado de ARC.

Es un estudio descriptivo, sin declarar significación por una única tarea
adicional. «Auditado» significa que se reprodujo el resultado, no que S6
esté verde. Elegir un tamaño requerirá después otra cohorte y un contrato.

## GIF y página pública

Se reconstruyen rasgos, ocho índices por asociación, pesos leídos, suma y
puntuación de las 84 familias de operaciones de la guía sobre una tarea
de desarrollo identificada. Cada familia tiene su propio GIF y un JSON
con todos los datos que lo explican. La animación presenta sucesivamente
ramas del cálculo y gira la cámara; no representa tiempos de inferencia.

Para los tres casos ganados frente a base se muestran además los pasos de
sus programas verificados, con entrada y salida de cada paso. Estos casos
se eligen por su interés explicativo después de conocer los resultados;
no son una muestra representativa ni una nueva evaluación.

Las puntuaciones reconstruidas deben coincidir con el diario original y
las salidas reconstruidas con las predicciones guardadas. El público puede
distinguir una operación candidata de un paso del programa ejecutado.
Los diarios nuevos utilizan `echo_arc.observe.Journal`; no hay otro bus.

Gráficas exportables PNG/SVG, tablas CSV, JSON de métricas, manifiesto de
huellas, GIF, imágenes estáticas y página HTML sin dependencias externas.
La página ofrece animación voluntaria y respeta movimiento reducido.
El paquete público contiene resultados y visualizaciones; no fuentes de
ECHO ni pesos del candidato. No se publica automáticamente en otro repo.

## Comandos

Desde echoai, con Python del sistema (perfil original Python 3.14):

```sh
python3 -m seed.capacity_study prepare
python3 -m seed.capacity_study follow
python3 -m seed.capacity_media
python3 -m unittest tests.test_capacity_study
```

`follow` deja estado y diario en `lab/seed/capacity-study-20261001`.
Los medios quedan en `lab/publication/capacity-20261001`.
