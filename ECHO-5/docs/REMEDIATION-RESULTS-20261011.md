# Revisión posterior a r3: implementación y primer piloto

11 de octubre de 2026, 23:14, Europe/Madrid. Revisión de desarrollo, con fuentes
`ebc21caf9511298c9bff3ae3d04a9406b79f3b62f4144fe2a417de7744593ace`.
Los cinco instrumentos están implementados y sus mediciones reproducidas en
procesos nuevos. **Esto no demuestra cinco mejoras científicas.** El cierre r3
conserva su alcance e identidad anteriores; no se ha reabierto S6 ni publicado.

## Evidencia y pruebas

- [Pruebas previas](../artifacts/remediation-checks-20261011-r1/result.json):
  entorno y sintaxis válidos; suite base de 414 casos, 24 omitidos porque
  necesitan el entorno opcional. No hubo errores ni fallos.
- [Perfil nativo](../artifacts/remediation-checks-20261011-r1/remediation-native.json):
  59 pruebas, sin omisiones, fallos ni errores, incluyendo las comprobaciones
  nativas omitidas por la suite base. Los recuentos se solapan; no sumarlos.
- [Piloto](../artifacts/remediation-pilot-20261011-r1/result.json): cinco bloques
  medidos y auditados, 62,48 segundos de pared, del 23:08:50 al 23:09:53.
- [Diagnóstico posterior sobre los mismos casos](../artifacts/remediation-grammar-autopsy-20261011-r1/audit.json):
  doce búsquedas y doce reproducciones, 15,52 segundos, terminado a las 23:13:21.

La revisión independiente encontró y permitió corregir antes de medir:
cohortes reducidas que podían pasar por completas, falta de vinculación entre
informe y auditoría, ausencia de recibos ante errores de arranque y falta de
verificación del archivo de fuentes. También se corrigió el diagnóstico que
confundía consulta indefinida con desacuerdo entre predicciones y el que decía
que una solución no se había alcanzado cuando faltaba terminar su nivel de
búsqueda. Las pruebas reproducen esos fallos y comprueban su rechazo.

## Exploración con habilidades iguales

28 mundos, siete perfiles prerregistrados: objetos en habitaciones de tamaño
5, 8 y 10, llave/puerta en tamaños 6 y 8, apertura ordenada de puertas y
colocación de objetos. Tres actores reciben la misma observación parcial,
habilidades, mapa, planificación y presupuesto. Todos mantienen el destino
hasta alcanzarlo o invalidarlo. Cambia sólo la selección de frontera.

| Selector | Éxitos | Acciones | Trabajo lógico |
|---|---:|---:|---:|
| Información estimada | 28/28 | 300 | 232.985 |
| Frontera cercana | 28/28 | 309 | 231.435 |
| Frontera aleatoria | 28/28 | 318 | 255.746 |

Los 84 episodios se reprodujeron con decisiones y resultados idénticos. La
información estimada ahorró nueve acciones frente a cercanía, pero consumió
1.550 unidades adicionales de trabajo (+0,67 %). **No existe ventaja de
acierto en este piloto ni demostración de equivalencia universal.** Los
intervalos son amplios. Ningún perfil fue retirado después de observarlo.
La política no está aprendida con Active Neural SLAM: el artículo inspira
el contraste, no aporta pesos ni resultados a ECHO.

## Referencias semánticas

32 significados explícitos y 20 rechazos sintácticos coinciden con el parser.
94 comparaciones de trayectorias nativas (41 positivas y 53 negativas), más
tres rechazos nativos, coinciden con referencias redactadas independientemente.
Cero falsos éxitos, discrepancias de vinculaciones o errores del instrumento.
El dominio sigue siendo el lenguaje limitado y las escenas de una habitación.
Esto reduce el riesgo de errores compartidos; no constituye comprensión general.

## Generador independiente y cuello de búsqueda

La nueva construcción usa poliminós irregulares, relaciones, contenedores,
distractores y composiciones, con oráculo basado en coordenadas del generador,
independiente de la segmentación y del intérprete de programas del actor.
La evaluación usa **biblioteca vacía, gramática completa de 326 átomos, beam 24,
profundidad máxima 4 y presupuesto de 2.000.000 unidades por tarea**.

- Tareas compatibles independientes: **0/18**, todas agotaron presupuesto en
  profundidad 2; cero respuestas incorrectas emitidas.
- Plantillas anteriores, bajo esa misma configuración: **0/9**, también por
  agotamiento en profundidad 2.
- Controles de ambigüedad: **3/3** abstenciones por ambigüedad identificada.
- Color fuera del lenguaje: **3/3** agotamientos, no prueba de haber identificado
  la imposibilidad. No se presentan como controles superados.

Estas condiciones difieren de la confirmación anterior con biblioteca y
gramática acotada. El dato no acredita una regresión del sistema r3 completo ni
atribuye todo el fracaso a la novedad de las escenas.

La autopsia inicial resolvió **4/4** casos de desarrollo con los 32 átomos del
contrato previo, sin entregar el testigo al buscador. Para esclarecer la
diferencia, un diagnóstico posterior fijó el primer caso ya registrado de
cada una de las tres familias comunes, en ambos generadores. Se compararon
los dos alfabetos en **los mismos seis casos**, a igual presupuesto:

| Generador | Alfabeto de 32 átomos | Alfabeto de 326 átomos |
|---|---:|---:|
| Independiente | 1/3 | 0/3 |
| Plantillas anteriores | 3/3 | 0/3 |

Con 326 átomos no se terminó la profundidad 2. Con 32 se alcanzó profundidad 3;
en los dos casos independientes sin respuesta ya había hipótesis ajustadas
a las demostraciones, pero se agotó el presupuesto antes de completar ese
nivel y comprobar el consenso. La abstención respetó el contrato.

**Esta comparación respalda un cuello de coste/anchura de búsqueda.** No es
descubrimiento autónomo de qué gramática usar ni confirmación nueva de
transferencia. El lenguaje reducido se eligió como diagnóstico, no por ECHO.
El diario permite investigar después poda segura, reutilización de análisis y
distribución del presupuesto sin introducir el programa testigo en el actor.

## Currículo calculado por demanda

Cuatro ejecuciones emparejadas, cuatro adquisiciones por ejecución, seis entradas
candidatas por adquisición y ocho casos nuevos por ejecución. Cada brazo paga
sus propias predicciones; el adaptativo paga también las opciones descartadas.

| Selector | Exactos finales | Acierto medio entre prefijos de adquisición | Trabajo de aprendizaje | Trabajo con evaluación |
|---|---:|---:|---:|---:|
| Secuencial | 24/32 | 75 % | 484.284 | 868.751 |
| Aleatorio | 32/32 | 81,25 % | 484.264 | 959.971 |
| Adaptativo | 32/32 | 100 % | 995.301 | 1.323.758 |

El adaptativo alcanzó soluciones antes en tres de cuatro pares frente al azar,
pero empató al final y gastó aproximadamente el doble en aprendizaje. La
evaluación consume menos una vez reducidas las hipótesis, sin compensar todo
el coste de selección. **Resultado inconcluso, sin superioridad coste/éxito
confirmada.** Cuatro ejecuciones no justifican una afirmación general.

## Qué se deriva para la siguiente intervención

1. Investigar el coste de búsqueda con gramática completa: evitar repetir
   análisis de rejillas y estudiar poda justificada o reparto de presupuesto.
   Mantener abstención cuando no se ha completado la comprobación de consenso.
2. Adaptar el gasto de selección del currículo a la incertidumbre restante,
   conservando controles por demanda y el coste total. No atribuir ahorro a
   una tabla precalculada que el control no necesita.
3. Ampliar la exploración a topologías/tamaños registrados antes del siguiente
   ensayo. Conservar este empate; no elegir mapas sólo porque favorezcan ECHO.
4. Mantener la referencia semántica independiente como regresión y el segundo
   generador como evaluación separada. Las ideas de Popper, ARGA y Stitch
   siguen siendo hipótesis de intervención, no resultados importados.

No se aplicó una nueva política de síntesis después de mirar estos resultados.
Los procesos de evaluación terminaron. El panel fue reiniciado con las fuentes
actuales y responde HTTP 200; el visor del piloto lee registros históricos.
