# TRANSFER-3 — demostrar transferencia útil, no rescatar un banco

## Una frase

**Lo aprendido en A debe mejorar el comportamiento en mundos nuevos B/C frente
al mismo agente sin ese aprendizaje, sin transferir el mapa ni conocer el examen.**

Nav autoriza investigar alternativas y persistir hacia esa demostración.
No hay hardware en el laboratorio: este trabajo es software y simulación.
El verde funcional, si se obtiene bajo el contrato aplicable, no acredita
hardware, HIL, vuelo real ni DRONE-3.

## Por qué cambiar el enfoque

V3–v8 estudian una familia concreta de navegación cuyo planificador ya recibe
cinemática correcta. Q sólo interviene en desempates. Hay influencia medible,
pero no ventaja suficiente. La feature 504 es una pista de fallo, no la
definición de TRANSFER-3 ni una condición que obligue a continuar esa línea.

No se reescriben esos rojos. El registro previo
`TRANSFER3-IMPLEMENTATION-20260918.md` se conserva como historial.

La pregunta nueva es: **¿qué propiedad reutilizable del cuerpo o de sus
habilidades necesita aprender el agente, y cómo ayuda ese conocimiento cuando
cambia la geometría?** Cambia la variable experimental, no la obligación de
demostrar aprendizaje, control competente, independencia y seguridad.

## Plan A — calibración de costes de movimiento

### Hipótesis

Una calibración aprendida de costes de acciones permite elegir recorridos
menos costosos en salas nuevas. No se transfiere ninguna ruta.

### Diseño

1. Define una familia de cuerpos/condiciones simuladas con costes enteros,
   positivos y acotados. La condición es común dentro de cada campaña A/B/C;
   cambia entre campañas públicas según una distribución fijada de antemano.
   No selecciones retrospectivamente sólo calibraciones favorables.
2. A ofrece movimientos reales del simulador. El agente aprende usando
   consecuencias disponibles por su interfaz —por ejemplo, variación de energía
   simulada—, nunca leyendo las tablas verdaderas del evaluador.
3. Transfiere exclusivamente parámetros de calibración y el esquema público.
   Borra mapa, historial espacial y episodios antes de cada misión B/C.
4. B/C contienen geometrías nuevas de la misma ontología. Mismo controlador,
   sensores, planificador y gates para todos los brazos; costes aprendidos
   deben participar directamente en la valoración del plan, no quedar ocultos
   en un tercer desempate.
5. Scratch mantiene cinemática competente y un prior nominal defendible,
   fijado antes de la condición particular. No uses T vacía ni un control que
   no pueda moverse. Ambos reciben idéntica información pública inicial.
6. Control causal: misma representación y algoritmo con calibración nominal,
   calibración aprendida, calibración de otra condición/permutada y, como
   cota externa no competitiva, valores verdaderos del evaluador.

### Comprobación de identificabilidad antes de entrenar

Demuestra que existen elecciones ejecutables con costes distintos y que la
calibración puede identificarse a partir de la interfaz disponible.

**No basta con añadir un coste direccional tipo viento.** Si el término es
lineal y conservativo, su suma puede depender sólo del desplazamiento neto:
dos rutas entre los mismos extremos pagarían lo mismo por ese término. Tampoco
basta con rutas de idénticos conteos de acciones. Comprueba matemáticamente
y con fixtures si las alternativas realmente cambian el coste total.

Usa sólo diferencias físicamente interpretables en el simulador —por ejemplo,
costes no conservativos o distintas composiciones de primitivas—, con contrato
explícito y sin fabricar una excepción para que el candidato gane. La cota
oracle sirve para comprobar margen disponible, no para filtrar salas perdedoras.
Si ni la cota puede compensar el aprendizaje, no lances una campaña grande.

### Qué se mediría

- Metas y regresiones de llegada, con restricciones duras sin degradación.
- Coste de misión en unidades simuladas, entre éxitos conjuntos.
- Coste total escolar más el mismo bloque de examen, no un horizonte elegido
  después del resultado. Tiempo, movimientos, CPU y memoria se reportan aparte.
- Error de calibración, cobertura, efecto de retirar/permutar el aprendizaje,
  influencia real en decisiones y parámetros idénticos antes/después del examen.
- Incertidumbre, multiplicidad y potencia declaradas prospectivamente.

Recompensa, coste primario y criterio de éxito son cosas distintas. No uses
la misma suma de recompensas como única prueba de eficiencia o seguridad.

## Plan B — transferencia de un modelo de ejecución

Si A no tiene margen útil o no consigue una ventaja, considera aprender una
propiedad reutilizable de la ejecución: ganancia, retardo o efecto de una
primitiva, mediante consecuencias observadas y el modelo existente.

Hipótesis: una calibración del modelo en A reduce correcciones, recomposiciones
o movimientos desperdiciados en salas nuevas, sin transferir geometría.

Mantén el coste de misión como resultado principal; no cambies de métrica
porque otra dé positivo. Conserva un scratch que pueda ejecutar las tareas con
su controlador nominal robusto. Mismos gates y límites de seguridad; no
construyas un escenario donde desconocer un dato arbitrario inmovilice al control.

Prueba primero que el modelo aprendido se identifica, cambia predicciones
correctamente y tiene un canal de influencia real. No basta con predecir mejor
si el comportamiento y el coste no mejoran. Usa ablationes y calibraciones
cruzadas, no sólo una comparación final agregado contra agregado.

## Plan C — transferencia de calibración perceptiva

Si el cuello está en percepción, prueba reutilizar una calibración sensorial
aprendida en A, usando la infraestructura de evidencia existente.

Hipótesis: con las mismas observaciones, una calibración congelada produce
creencias más útiles sin falsos hechos y permite completar misiones con menor
coste en geometrías nuevas.

Scratch conserva un adaptador nominal competente y los mismos sensores. La
calibración no puede convertir desconocidos en hechos por conveniencia, saltar
VERIFY ni llevar etiquetas del examen al agente. Si entrenarla requiere
referencias, documenta una fuente válida disponible en A y su coste; no
introduzcas un canal oracle disimulado. Si no puedes hacerlo dentro de los
contratos, descarta esa variante antes de implementarla.

## Cómo elegir y cambiar de plan

Los planes son hipótesis alternativas, no tres implementaciones obligatorias
en secuencia. Ejecuta primero la prueba mínima que más reduzca incertidumbre.
Tras un rojo distingue: bug, falta de identificabilidad, falta de influencia,
datos escolares insuficientes, representación inadecuada, ausencia de margen
económico o evidencia insuficiente. Un ensayo no descarta una familia entera.

Puedes proponer un plan D y siguientes dentro de la misma tesis y dominio,
pero cada cambio necesita contrato previo, control causal y prueba de
refutación. No encadenes ajustes sin hipótesis ni abras exámenes hasta lograr
uno favorable. Preserva la selección completa y la multiplicidad.

Antes de una revisión nueva, escribe un razonamiento auditable breve: evidencia,
supuestos, alternativas, prueba discriminante y decisión. No se pide una
transcripción de razonamiento interno, sino justificaciones comprobables.

## Condiciones que ningún plan elimina

Mismo ejecutable por brazo salvo parámetros/manipulación declarada; consumidor
aislado; cero mapas o identificadores del mundo transferidos; aprendizaje
congelado en B/C; geometrías independientes; éxito y seguridad antes de ahorro;
amortización explícita; artefactos completos y auditoría en proceso nuevo.

El contrato nuevo debe conciliar su métrica con `ECHO-3-ACCEPTANCE.md` antes de
ejecutar. Los umbrales históricos de movimientos no se reinterpretan como si
hubieran validado una tarea distinta. Nada autoriza rebajar el cierre superior.

Primero desarrollo y confirmación pública prospectiva; después campaña real
A→B→C con protocolo e inventarios comprometidos **antes de aprender A**.
Custodia fuera del acceso de ambos agentes. Si B falla, C no se abre.

**Persistir hasta obtener evidencia válida o encontrar un bloqueo real;
nunca convertir la persistencia en selección de un falso positivo.** No se
garantiza que exista una solución dentro del dominio y recursos disponibles.
