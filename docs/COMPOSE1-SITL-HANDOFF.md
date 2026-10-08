# COMPOSE-1 — continuación tras el banco funcional

2026-09-14. Trabajo software pendiente, autorizado como continuación de
COMPOSE-1. No depende de comprar hardware. Referencia vigente:
[resultado funcional](COMPOSE1-RESULTS.md); no modificar su código, diseño,
particiones ni evidencia congelados. Utilizar una versión nueva y preservar
`compose1_green=false` del primer certificado.

## Primero: aislar la contribución de composición

El horizonte uno y cuatro empataron en el banco inicial. Antes de publicar una
ventaja de composición, diseñar y congelar un examen donde los efectos de
habilidades separadas deban combinarse. Una meta tras una pared con una única
abertura no basta para discriminar esos mecanismos.

Mantener un cuerpo compatible con el dron. Candidatos de desarrollo: observar
una abertura desde un lateral antes de usarla, elegir entre accesos con costes
de retorno distintos y revalidar un acceso que cambió fuera de vista. Si se
añade un mecanismo accionable por aproximación, declararlo como interacción
del mundo simulado; no presentarlo como manipulación física aprendida.

Cada habilidad necesita precondiciones perceptivas, efecto esperado, plazo,
coste, condición de terminación y salida por fallo. Separar efectos enseñados
de efectos aprendidos. No entregar como reglas la secuencia que resuelve B/C.
No escribir transiciones imaginadas en CAM/T/Q ni añadir otro bus cognitivo.

Comparar completo, horizonte uno, Q reactiva y un planificador convencional
con los mismos sensores, habilidades, memoria y presupuesto medido. Publicar
resultados negativos, tiempo, éxito, intervenciones, coste y abstenciones.
Fijar KPI, N, semillas reservadas e intervalos antes de abrir el nuevo examen.
La ventaja debe atribuirse a un mecanismo mediante ablación, no al nombre
del módulo. No declarar necesarios cuatro pasos si uno vuelve a bastar.

## Después: puente de ejecución Gazebo/PX4

1. Reutilizar los locks y canales SENSOR/GROUND/DYNAMIC/PATTERN vigentes para
   traer observaciones públicas. El simulador conserva geometría y verdad;
   el consumidor conserva únicamente evidencia recibida. No pasarle SDF,
   pose verdadera, nombre de sala ni mapa del evaluador.
2. Dar a cada observación marco, captura, llegada, incertidumbre y procedencia.
   Construir ocupación con envolvente del cuerpo y margen de localización.
   El píxel/haz de replay FUSION no certifica por sí solo un corredor libre.
3. Sustituir el salto cinemático por habilidades asíncronas acotadas. Publicar
   la predicción antes de pedir movimiento; observar ejecución, timeout,
   desviación y resultado. PX4 estabiliza y ejecuta sus failsafes; nunca
   escribir poses ni motores para hacer coincidir T.
4. Revalidar el siguiente tramo con evidencia fresca. Caducidad, conflicto,
   pérdida de canal o coste no estimable deben producir una salida definida
   y verificable; hover no es siempre una garantía de seguridad.
5. Medir coste y duración de habilidades en A. Mantener el modelo energético
   como aproximación declarada hasta POWER-1. Exigir reserva de retorno y
   aterrizaje sin inventar unidades físicas a partir del contador cinemático.
6. Ejecutar desarrollo y validación física en particiones nuevas, con código
   congelado, controles y trazas firmadas. Preservar C sellado de TRANSFER-3;
   distinguir estos mundos de integración de su examen final.

Esta integración mínima prueba consecuencias físicas de COMPOSE. PX4-1
continúa debiendo certificar la autoridad completa, límites y fallos del
enlace. Un resultado favorable aquí no cierra PX4-1, POWER-1 o SAFE-1.

## Puerta de revisión

El informe nuevo debe separar evidencia válida, éxito funcional, ventaja
causal de composición y ejecución física. Recalcular decisiones y consecuencias,
probar que un mutante que teletransporta o filtra el mapa falla, y comprobar
que un informe verde alterado se rechaza. Mantener el mismo binario por mundo.
No marcar el hito cerrado por haber conectado el transporte o por ganar sólo
al control Q. La demostración final debe satisfacer el contrato general de
[ECHO-3](ECHO-3-ACCEPTANCE.md), con límites explícitos y rojos conservados.
