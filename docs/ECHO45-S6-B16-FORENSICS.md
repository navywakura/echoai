# S6-B16 — por qué refinar HOLD todavía no produce conservación

Revisión del 4 de octubre de 2026. B16 terminó con 24 propuestas, ninguna
válida para V3. El mejor total de ambos controladores fue 378, igual a la
base. Las nueve propuestas HOLD del controlador actualizado ganaron cinco
niveles en A18/A53, pero perdieron siete o nueve en otros casos, además de
las regresiones de score. S6 permanece abierto.

El problema inmediato es la selección de condiciones de aplicación. El
instrumento conserva las observaciones, el operador solicitado y el objetivo
de refinamiento, pero el generador no acota la regla al contexto en que ayuda.
La información temporal que recibe tampoco enlaza explícitamente cada
consumo del control con sus consecuencias posteriores. La primera diferencia
de acción no identifica necesariamente el punto donde aplicar una guarda.

El [análisis ejecutable](../lab/seed/s6b16-forensics-20261004/analyze.py) produce
un [recibo con hashes y datos por llamada](../lab/seed/s6b16-forensics-20261004/analysis.json).
Comprueba las 183 fuentes congeladas, peticiones, prompts y mediciones A. No
genera partidas ni llamadas al modelo, no lee trayectorias B y no abre el examen.
La revisión de cierre anterior ya recalculó 24/24 resultados y sus replays.

| Comprobación | Resultado |
| --- | --- |
| Correspondencia operador solicitado/propuesto | 24/24 |
| Contexto completo, sin variante reducida | 24/24 |
| Entrada del controlador actualizado | 1670–2197 tokens; límite 3072 |
| Refinamientos realmente dirigidos a HOLD | 6 |
| Comportamientos distintos anterior / actualizado | 3 / 7 |
| Propuestas actualizadas con `world_events` o `level` en la guarda | 0/9 HOLD |
| Controles positivos de PROBE2 permitidos | Los dos, en las 12 llamadas HOLD de ambos brazos |

Esto descarta como explicación del rojo de este micro el truncado del prompt,
un nuevo fallo de transporte o la exclusión gramatical de las dos soluciones
conocidas. No determina cuánto contribuyen el modelo 4B, su cuantización, el
formato, la gramática o el presupuesto: esas causas requerirían controles
separados. La guía asociativa de 500k unidades no es la variable de este ensayo.

Las condiciones son demasiado generales. En la base hay 141 consumos HOLD
registrados, agrupados en 140 registros por partida y 133 vectores de features
distintos. Las nueve reglas actualizadas se activan en **136–141 consumos**,
el **96,45–100 %**, repartidos en las mismas diez partidas. Cuatro de los seis
refinamientos amplían la cobertura de su propuesta raíz en estas observaciones;
los otros dos conservan su guarda y cambian HOLD de 1 a 2. Ninguno restringe
su aplicación según `world_events` o `level`.

Ejemplo real: después de perder niveles con
`path_pending=0 AND reset_known=1 AND reset_useful=1`, el modelo eliminó
`reset_useful=1`. La regla pasó de cubrir 136 a 139 consumos de la base.
La sintaxis y la aplicabilidad son válidas, pero la reparación amplía el
alcance de una intervención que ya perjudicaba otros casos. Las preferencias
del generador siguen concentradas en condiciones booleanas frecuentes.

La primera petición HOLD permite 48.600 combinaciones de valor y guarda.
Después del primer rechazo quedan 485 guardas para HOLD=1 en la llamada
`updated-740101/001`. El controlador descarta incompatibilidad y algunas
equivalencias demostradas; no calcula qué guardas distinguen las oportunidades
de ganancia de los contextos de pérdida. B16 añadió evidencia e instrucciones,
pero dejó esa inducción casi por completo al siguiente JSON del modelo.

El feedback presenta una consecuencia con retraso. Estos índices empiezan
en cero y provienen de las trayectorias de la primera propuesta actualizada:

| Caso | Resultado de la regla amplia | Estado compatible con consumo previo | Primera diferencia interna | Primera acción distinta |
| --- | --- | --- | --- | --- |
| A18 | +1 nivel | 788 | 789 | 805 |
| A51 | −2 niveles | 206 | 207 | 236 |
| A53 | +4 niveles | 96 | 97 | 98 |
| A68 | −5 niveles | 221 | 222 | 337 |
| A76 | −2 niveles | 47 | 48 | 54 |

La columna de consumo previo es una inferencia limitada: el estado anterior
a la primera diferencia interna coincide con una lectura HOLD registrada,
ambas ejecuciones aún realizan la misma acción y el siguiente estado difiere
en la espera. Los resúmenes conservan consumos agregados, sin su índice
temporal individual. El nuevo instrumento debe registrar esa asociación
explícitamente. Tampoco se ha localizado mediante intervención cuál de las
lecturas causa la pérdida final de cada partida.

En A53, al preparar la espera, `pending_effect=0`, `reset_pending=1` y
`hold_remaining=0`. En la acción que B16 muestra como contraste de ganancia,
ya son `pending_effect=1`, `reset_pending=0` y `hold_remaining=39`.
El resumen de consumos incluye los valores anteriores, pero el contraste
etiquetado como ganancia muestra los posteriores y no enlaza los dos momentos.

Esta distinción impide una corrección tentadora pero errónea: exigir que una
nueva guarda coincida con el estado de la primera acción distinta del caso
positivo. Lo calculamos sin aplicar ese filtro al experimento: reduciría las
485 guardas a 215 y **eliminaría la guarda que PROBE2 ya verificó con 383**,
porque esta exige `pending_effect=0`. Por tanto, convertir indiscriminadamente
los contrastes actuales en restricciones duras puede destruir una solución
válida.

Tampoco debe prohibirse intervenir en toda partida que antes perdió. El
control positivo de PROBE2 toca lecturas de A59, A76 y A77, que pierden score
con la regla amplia, y aun así conserva sus resultados. Hace falta distinguir
momentos dentro de la partida. La etiqueta de pérdida global no convierte
todas sus lecturas en ejemplos negativos causales.

El planificador introduce dos fricciones adicionales. Después de dos intentos
HOLD con ganancia agregada no positiva, la pausa de familia obliga a explorar
predicción. En las tres semillas, la tercera llamada fue REVALIDATE_NOOP y
quedó en 378. En la semilla 740117, la segunda llamada había reducido la pérdida
de niveles de nueve a siete, conservando las cinco ganancias; ese progreso
intermedio no evitó la pausa. El micro solo ofreció dos refinamientos efectivos
por semilla, aunque el máximo del selector era tres.

Además, `repair_outcomes.target_for` solo admite propuestas raíz sin
`target_id`. El refinamiento posterior mantiene el JSON del primer intento
374 aunque exista un descendiente 376. El recibo del último descendiente sí
está presente; su código no pasa a ser el objetivo explícito ni sus contrastes
reemplazan los de la raíz. Conviene mantener el linaje y escoger el mejor
descendiente como punto de reparación, con un límite de trabajo para evitar
bucles. Estas fricciones son secundarias respecto de la selección de guardas;
corregirlas por sí solas no demuestra que aparecerá una mejora sin pérdidas.

La revisión de ingeniería obliga a corregir el enfoque. B16 sí arregló el
enlace entre operador y prueba, la presencia del objetivo, el orden de las
ganancias y el transporte. Sus tests comprobaron esas propiedades. Se
sobrestimó que entregar esa información bastaría para que el modelo indujera
una buena restricción. Faltaba comprobar funcionalmente la discriminación
temporal y dotar a ECHO de una búsqueda explícita sobre su lenguaje finito.
Siete comportamientos distintos frente a tres acreditan diversidad, no mejora.
Otro prompt más largo o más horas con este esquema no tienen una ventaja
demostrada.

Se comprobó una alternativa calculable usando solo datos existentes. Sobre
el primer intento B16, se ordenaron las 485 guardas legales para HOLD=1 con
esta clave, sin evaluar nuevas partidas:

```python
key = (
    -numero_de_casos_que_ganaron_con_alguna_lectura_cubierta,
    numero_de_lecturas_cubiertas_en_casos_que_perdieron,
    numero_de_condiciones,
    serializacion_canonica,
)
```

Los conteos usan las lecturas de la base y los resultados del intento propio
B16, no resultados de candidatos PROBE2. El orden coloca en el **puesto 5**
la guarda `reset_known=1 AND pending_effect=0 AND world_events<=16`. PROBE2 ya
midió HOLD=1 con esa guarda: **383 niveles, cero regresiones A y replay exacto**.
La evaluación protegida de ese parche sigue pendiente. La guarda es un control
de capacidad en este informe; no se incorpora como respuesta al agente.

El resultado es retrospectivo y no ciego: el ingeniero conocía PROBE2 cuando
diseñó esta clave. No acredita descubrimiento autónomo, causalidad de cada
lectura ni generalización. Solo muestra que una lista corta obtenida con
operaciones sencillas sobre la evidencia propia puede contener una reparación
que las llamadas libres no propusieron. La clave minimiza exposición a casos
con pérdidas; no garantiza ausencia de regresiones. Debe contrastarse con
ejecuciones completas y con problemas nuevos.

La siguiente condición propuesta tiene estas piezas, aún sin integrar en
el actor ni lanzar como campaña:

1. Registrar el instante de consumo, features anteriores, valor anterior y
   propuesto, junto con el vínculo a resultados posteriores en el diario A.
   Verificar paridad de comportamiento de esta instrumentación. Las observaciones
   retrospectivas siguen etiquetadas como tales; intervenciones acotadas en A
   podrán comprobar atribuciones dudosas, contabilizando sus ejecuciones.
2. Incorporar síntesis acotada de guardas sobre el lenguaje existente. El LLM
   propone una hipótesis de mecanismo; ECHO enumera y ordena sus posibles
   alcances con la evidencia propia. Se conserva diversidad y se comprueban
   candidatos completos en el simulador. Ninguna clasificación de trazas
   sustituye V3, V4 ni un replay real del programa modificado.
3. Conservar la mejor propuesta parcial de cada linaje y su historial de
   contraejemplos. Medir reducción de pérdidas conservando ganancias. Una
   mejora parcial puede justificar otro intento dentro del tope; nunca
   acredita aceptación ni reduce el umbral de conservación.
4. Comparar primero el controlador B16, el sintetizador sin LLM y el híbrido.
   Prerregistrar presupuesto total de propuestas, partidas, tokens y parada;
   contar todos los descartes, no solo los finalistas. Medir éxito sin pérdidas,
   coste hasta el primer éxito y variedad efectiva. El protocolo debe admitir
   que el sintetizador solo iguale o supere al híbrido: ese resultado no prueba
   una aportación adicional del LLM.
5. Solo después abrir piloto, auditoría, campaña y examen. La nueva capacidad
   mecánica debe estar disponible a los comparadores pertinentes con el mismo
   presupuesto. La ventaja adaptativa de ECHO sobre FIJO debe medirse, no
   introducirse asignándole herramientas o intentos adicionales.

Antes de congelar esa condición se necesitan pruebas funcionales de retraso
entre consumo y acción, de recuerdos cuyo caso global pierde pero contiene
intervenciones útiles, de selección del mejor descendiente y de conservación
del espacio de guardas. Los tests deben usar otros valores y situaciones,
incluyendo casos donde ninguna guarda legal sea suficiente. Una abstención
correcta también es un resultado válido.

V3 permanece en ≥2 niveles adicionales y cero pérdidas individuales. V4
conserva B. El examen reservado nuevo mantiene B1–B5. No se declara S6 verde
por recuperar 383 en desarrollo, por ordenar bien un control ya conocido ni
por pasar tests del instrumento. No se ha iniciado otro piloto durante esta
investigación.
