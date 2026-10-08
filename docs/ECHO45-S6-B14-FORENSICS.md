# S6-B14: por qué ECHO y FIJO empatan en 1134

Investigación privada del 4 de octubre de 2026, posterior al cierre auditado
de las 14:07:14 de Madrid. **Ambos brazos alcanzaron exactamente la misma
política de 378 niveles en la primera ronda y no aceptaron otra mejora.**
Las tres semillas cambian la generación del modelo, no las 80 partidas A:
378 × 3 = 1134 por brazo. Son niveles gym de desarrollo, no tareas ARC oficiales
ni tres conjuntos independientes de problemas.

**378 no es un límite demostrado del lenguaje.** Los ochenta registros
completos del programa aceptado coinciden con la base de PROBE2. Sobre esa
misma base hay dos propuestas HOLD ya medidas y reproducidas que alcanzan
383 sin pérdidas individuales en A. Las dos estaban permitidas en todas las
30 llamadas posteriores a la primera aceptación de B14. Ningún brazo las
propuso. Su retención en B y su descubrimiento autónomo siguen sin demostrar.

El cálculo está en [analyze.py](../lab/seed/s6b14-forensics-20261004/analyze.py),
con [recibo y hashes de las entradas](../lab/seed/s6b14-forensics-20261004/analysis.json)
y [tabla de las 36 llamadas](../lab/seed/s6b14-forensics-20261004/calls.csv).
Lee artefactos existentes y comprueba las 166 fuentes congeladas. No juega
partidas, no genera propuestas, no lee trayectorias protegidas B y no abre el
examen. El recibo de auditoría B14 es válido: 54 veredictos reconstruidos y
5080 partidas en caché independiente. Se conserva el resultado negativo.

**Qué produjo los 378 niveles.** Los seis recorridos, ECHO/FIJO con tres
semillas cada uno, aceptaron el mismo programa:

```json
{"patches":[{"set":{"REVALIDATE_NOOP":1},"when":{
  "body_known":["eq",1],
  "reset_known":["eq",1],
  "reset_useful":["eq",1]
}}]}
```

Esta regla revisa una predicción de movimiento cuando el movimiento observado
no ocurre, bajo las condiciones indicadas. Corrige la transición aprendida y
vacía el plan pendiente; no enseña una ruta ni consulta respuestas del examen.
Partiendo de 365 niveles, resuelve cinco casos adicionales:

| Índice en desarrollo A | Antes | Después | Ganancia |
|---|---:|---:|---:|
| 51 | 0 | 5 | +5 |
| 59 | 2 | 5 | +3 |
| 68 | 2 | 5 | +3 |
| 76 | 4 | 5 | +1 |
| 77 | 4 | 5 | +1 |
| Total | 365 | 378 | +13 |

Quedan ocho partidas incompletas: A10=3, A15=3, A18=4, A34=3, A41=0,
A53=1, A75=0 y A78=4. Faltan 22 niveles respecto de los 400 posibles. Solo
A41 conserva señal de contradicciones entre los fallos; A18 y A53 contienen
esperas. La mejora aceptada ya había resuelto las otras cinco partidas a las
que beneficiaba ese mecanismo.

**Qué pasó después.** Las 36 llamadas del modelo produjeron REVALIDATE_NOOP.
No hubo ninguna propuesta HOLD ni COOLDOWN_CAP. Las diferencias de petición
son reales: los 18 pares ECHO/FIJO recibieron prompts distintos y las semillas
se aplicaron correctamente. Aun así, 11 pares emitieron la misma propuesta
textual y 16 produjeron el mismo comportamiento en A. Los seis programas
finales son idénticos.

| Medida del piloto | ECHO | FIJO |
|---|---:|---:|
| Llamadas al modelo | 18 | 18 |
| Mejoras aceptadas, todas en ronda 1 | 3 | 3 |
| Propuestas REVALIDATE_NOOP / HOLD / COOLDOWN_CAP | 18 / 0 / 0 | 18 / 0 / 0 |
| Llamadas posteriores a la primera aceptación | 15 | 15 |
| Llamadas posteriores que ganan algún nivel | 0 | 0 |
| Llamadas posteriores con alguna pérdida de score individual | 6 | 5 |
| Llamadas posteriores con cero ganancia de niveles y score total | 9 | 9 |
| Propuestas que repiten comportamiento propio ya medido | 9 | 7 |
| Comportamientos distintos en toda la secuencia | 3 | 5 |
| Propuestas sin testigo compatible del control en los casos seleccionados | 9 | 6 |

No todos los rechazos eran programas inertes: las 30 propuestas posteriores
cambiaron acciones respecto de la política aceptada. Ninguna añadió niveles.
Nueve por brazo cambiaron la secuencia de acciones manteniendo exactamente
los niveles y el score total. Varias restantes ganaron score agregado mientras
perdían score en partidas individuales; el verificador exige conservación
individual. Una propuesta FIJO mejora score sin pérdidas, pero sigue en +0
niveles. Todas fallan V3, que exige al menos +2; ninguna llega a V4. No hay una
mejora de niveles que el verificador haya ocultado en estos dos brazos.

**Fallo 1: explorar una etiqueta no garantiza explorar su mecanismo.**
ECHO eligió CONTRADICTION doce veces, WAIT tres y GENERALIZE tres. En sus
tres llamadas WAIT seleccionó correctamente A53 y A18, pero el modelo
propuso REVALIDATE_NOOP. El contador incrementó `WAIT.trials` y dio por
explorado ese foco, pese a no probar ni HOLD ni COOLDOWN_CAP.

La causa de software es concreta: [`statistics`](../echo_arc/repair_memory.py)
cuenta el `type` solicitado. [`request`](../seed/s6b14_prompt.py) construye la
gramática sobre las ochenta partidas, con los tres controles, sin limitarla
por el mecanismo seleccionado. [`check_answer`](../seed/s6b13_prompt.py)
comprueba el control objetivo únicamente durante REFINE, no durante WAIT.
Cambiar el foco modifica la prosa y los casos, pero no exige correspondencia
entre la pregunta y el experimento ejecutado. La validación B14 comprobó la
selección de casos con señal y la presencia de memoria; no acreditó esa
correspondencia en las respuestas reales del modelo.

Además, en las seis llamadas ECHO de contradicción de las rondas 4 y 6 solo
se muestra A41, cuyas observaciones tienen `reset_known=0`. Las propuestas
exigen `reset_known=1`. Siguen siendo legales porque encuentran testigos en
otras partidas de la gramática global. Dejan sin tratar el caso que motivó
la petición y varias alteran partidas que ya estaban resueltas.

**Fallo 2: el primer éxito domina la asignación posterior.** El planificador
usa la prioridad `(ganancia_aceptada + 2) / (intentos + repeticiones + 1)`.
Conserva los +13 obtenidos sobre la base anterior aunque ya se hayan resuelto
esas oportunidades. En la ronda 4, las prioridades son 7,5 para contradicción,
1 para esperas y 0,667 para generalización. En la ronda 6, contradicción aún
tiene prioridad 3 frente a 1 para esperas. Las tres semillas vuelven a A41
durante las tres últimas rondas. El cálculo no representa bien la utilidad
marginal de ese mecanismo sobre el nuevo programa de 378 niveles.

**Fallo 3: la pausa de diversidad cambia el valor, no la familia.** Después
de observar dos fallos repetidos con REVALIDATE_NOOP=1, el controlador bloquea
ese ajuste durante una llamada. Permite REVALIDATE_NOOP=2, que fue lo que el
modelo emitió en las rondas 4 y 6. Al terminar la pausa vuelve a estar
disponible el valor 1. La secuencia de valores fue 1 → 1 → 1 → 2 → 1 → 2 en
los dos brazos y las tres semillas. Este mecanismo elimina algunas variantes
redundantes, pero no consigue que se pruebe otra familia. El filtro conservador
de equivalencias también actuó; sus garantías no cubren toda igualdad de
comportamiento y quedaron nueve repeticiones ECHO.

**Fallo 4: se pierden extremos relevantes de la evidencia.**
[`cases`](../echo_arc/contrastive_requests.py) ordena los testigos por
`stagnation` y por su serialización JSON. Después toma el primero y el último.
En los consumos HOLD de A53, `stagnation` siempre vale cero, por lo que decide
el orden del texto. Hay 60 consumos, con `world_events` entre 14 y 899, pero
se muestran 104 y 89. El primer consumo, con valor 14, desaparece del resumen.
Ocurre en las seis peticiones ECHO que muestran A53, rondas 2 y 3 de las tres
semillas. Ninguna sufrió recorte por límite de contexto.

A53 acumula 1787 decisiones de espera sin progreso dentro de su presupuesto
de 2000, un 89,35 %. Ese contador identifica una oportunidad de investigación;
no demuestra por sí solo que eliminar esperas sea correcto. PROBE2 sí midió
que reducir HOLD a 0 o 1 cuando `reset_known=1`, `pending_effect=0` y
`world_events<=16` preserva el score individual A y gana cinco niveles:
A18 pasa de 4 a 5 y A53 de 1 a 5. La observación A53 con valor 14 es compatible
con esa guarda; las dos mostradas al modelo no lo son. Esto demuestra una
pérdida relevante de información, pero no demuestra que mostrarla hubiera
hecho que Qwen encontrase la solución.

**REFINE nunca se activó.** El selector exige una propuesta rechazada que
ya gane algún nivel desde la política actual. Ninguna de las quince propuestas
posteriores de ECHO ganó niveles, así que nunca existió tal objetivo. La
infraestructura de refinamiento no puede corregir una hipótesis útil que el
generador todavía no ha formulado. Este bloqueo precede al refinamiento.

**Qué queda descartado y qué sigue siendo hipótesis.** Las 36 llamadas
usaron la variante completa de contexto, entre 916 y 1495 tokens de entrada
frente a un límite de 3072. Los treinta recibos recientes obligatorios están
presentes y coinciden con su resultado previo. Los prompts, semillas, comandos,
salidas y hashes de artefactos son coherentes; la auditoría reprodujo la fase.
No hay evidencia de truncado, intercambio de brazos o reutilización incorrecta
de una respuesta del modelo. La caché reutiliza mediciones de políticas iguales,
y la reproducción independiente confirma las cifras.

Las observaciones acreditan una concentración de propuestas en el mismo
control. No separan causalmente la contribución del modelo 4B cuantizado, la
temperatura, la redacción común, la representación por índices de la política
o el orden de alternativas de la gramática. Atribuir el resultado exclusivamente
a cualquiera de esos factores requeriría una ablación. El tamaño de la guía
de 500k unidades no es el factor variado en B14; este ensayo modifica controles
del actor mediante reglas, no entrena los pesos de esa guía ni del LLM.

El aumento respecto de B13-R1, 1113 → 1134 para ECHO, tampoco permite aislar
el efecto de una corrección: cambiaron simultáneamente el controlador, las
semillas del modelo y la población protegida. Sí está demostrada la mejora
365 → 378 frente a SEMILLA dentro de B14. Sigue sin demostrarse una ventaja
adaptativa frente a FIJO.

**Siguiente investigación propuesta.** Antes de otra campaña larga conviene
medir una condición de desarrollo que corrija estos acoplamientos:

1. Registrar por separado foco solicitado, operador propuesto, aplicabilidad,
   efecto observado y ganancia. Una respuesta de otro mecanismo consume su
   presupuesto, pero no acredita haber explorado el mecanismo solicitado.
2. Vincular las propuestas dirigidas al mecanismo elegido y a sus testigos.
   WAIT debe ensayar HOLD/COOLDOWN_CAP; una guarda dirigida necesita algún
   testigo compatible entre los casos que la motivan. Mantener controles
   genéricos y un calendario fijo de operadores con los mismos recursos,
   para separar selección adaptativa de la mera obligación de variar controles.
3. Actualizar la prioridad según la política vigente y el rendimiento reciente.
   Conservar el historial completo, pero no tratar el beneficio ya incorporado
   de +13 como evidencia de que el mismo mecanismo seguirá ganando ahora.
4. Muestrear evidencia por extremos numéricos, primera/última lectura temporal
   y cobertura de predicados; conservar frecuencias. Comprobar explícitamente
   que el resumen mantiene cambios de fase dentro del presupuesto de tokens.
5. Medir diversidad efectiva de operadores y comportamientos. La pausa debe
   atender la familia agotada; una alternancia 1/2 del mismo control no basta.

Una microablación de contexto y acoplamiento, con semillas y presupuesto
prerregistrados, debe preceder al siguiente piloto. Se medirán correspondencia
foco/operador, cobertura de testigos y ganancia real sobre A con replay, además
de coste y regresiones. Un cambio de gramática o selección se declara como
condición nueva para todos los comparadores pertinentes. Los controles humanos
de PROBE2 sirven para comprobar capacidad del instrumento; sus parches no se
insertan como descubrimiento del agente ni se entregan como respuesta al modelo.

No propongo reducir V3 ni promover un empate. Para S6 siguen pendientes una
ventaja ECHO frente a FIJO, la conservación protegida, la campaña y las cuatro
políticas del examen con B1–B5. Una mejora de desarrollo sobre 378 sería un
paso verificable, y por sí sola todavía no cerraría esas puertas.
