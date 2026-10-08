# SELF-C v2 — utilidad posterior de T preservada

2026-09-22. Contrato previo al banco. Autorizado por el usuario; v1, sus
umbrales, código, trazas y resultado rojo permanecen intactos.

## Pregunta distinta y límite explícito

V1 alcanzaba el techo físico de vidas completadas con o sin atribución y
su política no consultaba T. V2 pregunta si **proteger las transiciones
nominales durante una alteración corporal temporal permite elegir mejor una
acción después**, sin impedir aprender cambios externos que siguen presentes.
No es otra ejecución de la prueba de supervivencia v1 ni una reparación
autónoma del cuerpo. Es una prueba controlada de reutilización de memoria.

Se heredan WORLD-1, los sensores WSP16, el diagnóstico SELF-B y el permiso
de aprendizaje SELF-C v1. No se cambia su física ni se crean CAM/T/Q nuevas.
El banco restaura explícitamente el cuerpo entre ensayos de un paso; al
examinar reutilización, el ejecutor restablece los acoplamientos nominales,
pero **conserva el pulso externo**. La vuelta al cuerpo nominal es una
condición garantizada del experimento y comunicada por recibo a todos los
brazos, no algo que el agente deduzca o realice por sí solo.

## Protocolo

1. Calibración nominal SELF-A/B: 64 pasos de pares y ocho de referencia larga.
2. T se aprende mediante ocho ejecuciones nominales de un paso por acción:
   **24 pasos adicionales**, estados restaurados. No se carga una tabla de
   sucesores del juez ni se utiliza la calibración anterior para inflar T.
3. Diagnóstico por SELF-B, registrado y común a los controles. Solo observa
   paquetes/recibos; las causas privadas no entran en el consumidor.
4. Exposición: doce rondas de acciones 0,1,2, cada una desde restauración
   explícita al mismo estado oculto: **36 pasos por brazo**. El número doce
   permite que la experiencia alterada supere las ocho muestras nominales
   bajo KCC; todos reciben exactamente las mismas acciones y observaciones.
5. Reutilización: el cuerpo nominal vuelve por intervención del ejecutor;
   permanece la condición externa. Se solicita alcanzar un WSP objetivo en
   **una acción real**. Tres objetivos por condición: los resultados físicos
   alcanzables por las tres acciones; el juez los transforma en solicitudes,
   pero nunca entrega el índice de la acción correcta al selector. Los
   objetivos potencialmente coincidentes se conservan, no se filtran.
6. T y SENSATION/PATTERN no aprenden durante esos tres ensayos. Q tampoco
   debe cambiar: en este banco todas las recompensas físicas son cero y
   parte de cero; se comprueba su igualdad completa. Objetivos, predicción,
   propuesta, gate y resultado se guardan antes/después de ejecutar.

Un objetivo solicitado no afirma un hecho ni se inserta en CAM. No contiene
semilla, familia, acción deseada o etiqueta de causa. El selector compara
las tres predicciones de la **T aprendida** con el objetivo de 16 bytes.
Entre coincidencias decide Q; desempata con la propuesta original y wait.
Sin coincidencia usa Q y declara que no dispone de coincidencia en T; se
puntúa el resultado físico, no se inventa un éxito por declarar confianza.
El selector no importa física, diagnóstico, registros corporales ni juez.
El gate original puede vetar. No cuarto actuador, segundo bus ni LLM.

## Brazos emparejados

- `selective`: permiso SELF-C v1 durante exposición; consulta T al reutilizar.
- `unprotected`: enseña todas las transiciones válidas. Es aquí también el
  control sin atribución; no se lo cuenta como dos controles independientes.
- `freeze_all`: retiene todas las actualizaciones durante exposición; T nominal
  permanece intacta, incluso cuando el entorno sí cambió.
- `no_t`: aprende selectivamente como el primario, pero decide solo con Q.
  No borra tablas: es una ablación del acceso a T, no un agente con otro pasado.

La política de exposición es supervisada e idéntica, no autónoma. La
evidencia de supervivencia continua de v1 queda separada. En causas mixtas,
retener una transición corporal puede también impedir aprender su parte
externa: se publican esos fallos, sin fabricar sucesores contrafactuales.

## Desarrollo y confirmación acotada

- Desarrollo: H={30,37}, temperatura={48,65}.
- Confirmación: H={31,38}, temperatura={49,66}; ejecutar después del desarrollo,
  sin cambiar fuentes, pesos de decisión ni criterios. Orden de objetivos inverso.
- En ambos: cuatro acoplamientos × pulsos {-16,0,+16}; 48 condiciones,
  144 solicitudes por brazo. Nominal, propia, externa y mixta desglosadas.
- Smoke: solo H=30/temperatura=48, doce condiciones; no autoriza cierre.

La confirmación usa posiciones nuevas dentro del mismo simulador y mecanismos
conocidos. No equivale a los B/C finales de E4-SELF-1 ni generalización a
averías fuera del prior. La segunda fase también se publica si desarrollo falla.

## Criterios fijados antes de ejecutar

En **cada** fase completa, no solo en el total:

- Primario ≥60% de objetivos logrados y al menos 1/3 en cada clase causal.
- Ventaja ≥5 puntos porcentuales sobre cada control, incluyendo `no_t` y
  `freeze_all`. Publicar victorias/pérdidas/empates emparejados y todos los fallos.
- Alguna ventaja propia frente a `unprotected` y alguna externa frente a
  `freeze_all`; sin pérdidas frente a esos controles en el grupo nominal.
- Cero actualizaciones con efecto corporal en el primario; alguna en
  `unprotected`. Primario debe permitir actualizaciones externas legítimas.
- Actualizaciones retenidas dejan T y SENSATION/PATTERN idénticos; lecturas
  de tarea sin aprendizaje y sin alterar Q. Una sola CAM/T/Q por brazo.
- Diagnósticos correctos en este dominio, pronósticos previos, secuencias
  de exposición iguales, cero terminalidad, hechos falsos, destrucción o
  llamadas corticales. Contabilidad de recursos y restauraciones explícitas.
- Pruebas de ausencia de lectura privada, cambios de T que cambien la
  decisión, ablación que no lee T, veto, recibos/IDs inválidos, capacidad,
  no sobrescritura y manipulación de evidencia. Replay completo en proceso
  nuevo y revalidación de certificados anteriores, incluida la v1 roja.

Si pasa, `self_c_v2_green` solo acredita reutilización controlada dentro de
este contrato. `self1_green=false`: faltan los B/C finales del conjunto.
Si falla, conservar el resultado y no cambiar criterios para pintarlo verde.
Hardware después del software; METAVERSE-1 último.
