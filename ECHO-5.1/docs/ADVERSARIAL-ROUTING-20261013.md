# PCWORLD-1 · protocolo de sondeo adversarial adaptativo

Estado: protocolo de desarrollo para comparar mecanismos; no es un examen
confirmatorio ni un benchmark oficial. El piloto `repair-v1` permanece
congelado y sin cambios.

## Pregunta y diagnóstico

El piloto inicial obtuvo 2/6 en S, I2, F y E. No encontró una ventaja, pero
tampoco ejercitó la hipótesis adaptativa: el brazo E llamó al coordinador con
E[6] vacío y su política no seleccionó categorías a partir del código ni de
CAM. El crítico produjo 15 entradas válidas pero no discriminantes y tres
entradas de rutas fuera de dominio. Como el protocolo aceptaba el ejemplo
público y paraba tras una crítica sin refutación, CAM no recibió contraejemplos
y no hubo una oportunidad de reparación en la comparación.

La iteración añade sondeos por categorías, validación del contenido real de
cada sondeo, reintento acotado ante esquema/dominio/duplicados y una condición
de aceptación que requiere dos categorías distintas con pruebas ejecutadas
contra la versión final del candidato. No se cambia el verificador ni el
oráculo privado.

## Brazos y controles

| Brazo | Intervención |
|---|---|
| S | Una propuesta y autorrevisión; sin crítico adaptativo. |
| I2 | Dos propuestas independientes, elegidas mediante el ejemplo público. |
| F | Crítico con orden de categorías fijo, preregistrado por familia. |
| E | Mismo crítico y límites; elige categoría según señales explícitas del código y evita categorías ya cubiertas según CAM. |

La selección de E en esta versión es una heurística simbólica fija, no una
política aprendida ni una red neuronal. F y E tienen la misma exigencia de dos
sondeos válidos, distintos y ejecutados. Cada sondeo admite hasta dos reintentos
por respuesta fuera de esquema/dominio, duplicada o que no corresponda a la
categoría pedida. Se contabilizan todos. El techo es seis llamadas de crítico
por episodio; los demás límites por episodio siguen siendo 25.000 tokens,
50 herramientas, 300 s de CPU de candidato, 300 s de pared y 12 llamadas LLM.
La consulta a CAM y su trabajo también se cuentan.

El orden de los cuatro brazos rota entre tareas. Los cuatro usan el mismo
Qwen2.5-Coder-7B-Instruct Q4_K_M, configuración, runtime hermético, oráculos,
presupuesto y variantes. No se expone al agente el conjunto oculto ni sus
resultados.

## Muestra y límites de interpretación

`repair-v2` crea con semilla 41 dos variantes por cada una de las seis familias
ya conocidas: intervalos, registros, rutas, CSV, paginación y dependencias
(12 tareas; 48 episodios). Las variantes cambian valores y ejemplos, pero
conservan el mismo contrato y estructura de defectos de `repair-v1`. Por tanto,
esto calibra la selección y reparación de contraejemplos dentro de dominios
conocidos; no es transferencia a seis familias independientes nuevas.

Resultado primario: aceptación correcta de todas las pruebas finitas reservadas
de cada tarea. Secundarios: refutaciones válidas retenidas, reparaciones
aceptadas, rechazos de dominio/categoría, llamadas, tokens, herramientas,
trabajo CAM, CPU y tiempo de pared. Se comparan E−F y E−S por la misma tarea,
además de las tasas por familia. Toda aceptación se contrasta con el evaluador
independiente; una falsa aceptación invalida cualquier alegación de ventaja.

Con solo dos variantes por familia, cualquier diferencia es descriptiva y muy
incierta. Se considerará «señal prometedora para replicar» únicamente si E
supera a F y S en el resultado emparejado, conserva cero falsas aceptaciones y
el coste adicional queda explícito. Un empate, regresión o resultado dominado
significa que la ventaja no quedó demostrada. No se cambiarán tareas, reglas ni
umbrales después de observar resultados. Una confirmación necesitará familias
y semillas nuevas, tamaño de muestra previamente dimensionado y auditoría
independiente.

## Criterios de integridad

- Código, contrato, semillas, modelo, runtime y configuración se congelan antes
  de ejecutar los episodios con el modelo.
- Cada respuesta del proveedor, reintento, prueba, cambio y abstención queda en
  recibos auditables; no se descartan ejecuciones fallidas.
- Se exige auditoría válida, cero cambios en fuentes congeladas, cero
  aceptaciones falsas y `destroyed == 0`.
- Las conclusiones se limitan a esta muestra y a este Qwen local. El diagnóstico
  sembrado y el piloto `repair-v1` no se mezclan con `repair-v2`.
- S6 sigue aplazado. El verde de infraestructura no implica superioridad
  científica.

## Resultado del piloto preregistrado

La ejecución completa de 48 episodios y su resultado están documentados en
[ADVERSARIAL-ROUTING-RESULTS-20261013.md](ADVERSARIAL-ROUTING-RESULTS-20261013.md).
E y F aceptaron 2/12 tareas cada uno; S e I2, 4/12 cada uno. E produjo seis
contraejemplos verificados frente a dos de F, pero no convirtió esa detección
en más reparaciones aceptadas. La ventaja de ECHO no quedó demostrada. La
auditoría autenticó 2.049 recibos; el piloto registró siete fallos de plazo del
proveedor, todos contabilizados como fallos. Estos resultados son descriptivos
de seis familias conocidas y no constituyen confirmación ni transferencia a
dominios nuevos.
