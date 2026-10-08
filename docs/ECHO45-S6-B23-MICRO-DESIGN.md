# Micro B23 para separar búsqueda y neocórtex

Condición privada del 7 de octubre de 2026, posterior al cierre y la
[investigación B22](ECHO45-S6-B22-FORENSICS-20261007.md). Estado:
**IMPLEMENTED, R3_PREFLIGHT; micro NOT_RUN**. El selector, transporte,
ejecutor, replays y auditoría están implementados. El manifiesto experimental
se congelará al disponer de los pesos 7B/14B y el ejecutor verificados. La
conexión privada a Kaggle funciona. R2 descargó los pesos oficiales y quedó
bloqueado por las plantillas embebidas; véase la enmienda R3 abajo. El GGUF
local identificado es 4B y no sustituye a 7B/14B. La comprobación del
instrumento usa un directorio separado y no aporta resultados al micro.

La pregunta inicial es si corregir la asignación de reparaciones o dar al
neocórtex los fallos propios permite encontrar una propuesta que satisfaga
el mismo juez. B22 demuestra que el lenguaje puede expresar al menos un
control humano conservador en desarrollo amplio, pero el investigador no lo
descubre. Sus 288 intentos no acreditan agotamiento de la gramática.

Se proponen cinco brazos porque hace falta distinguir el efecto del selector
del efecto del modelo:

| Brazo | Qué produce las propuestas | Comparación que permite |
|---|---|---|
| R22 | Muestreo original B22 | Control aleatorio |
| M22 | Buscador original B22, reparaciones incluidas | Referencia del algoritmo que acaba de fallar |
| M23 | Selector nuevo con detección de inactividad y continuidad de ramas | Efecto de corregir el buscador sin LLM |
| N7 | Qwen2.5-Coder-7B-Instruct, Q4_K_M, con resultados propios | Aportación de un neocórtex pequeño |
| N14 | Qwen2.5-Coder-14B-Instruct, Q4_K_M, con resultados propios | Efecto del tamaño con la misma interfaz |

Los cinco reciben la misma base B14, lenguaje HOLD y observaciones iniciales.
Cada uno empieza con historia propia vacía. R22 sigue sin usar sus resultados
para cambiar el muestreo. M22 conserva el algoritmo original. La información
de los controles humanos, propuestas B21/B22, este informe y sus CSV no
forma parte de ninguna entrada del investigador o de los LLM.

La cohorte de desarrollo propuesta tiene las doce partidas del micro B22 más
los casos amplios 144 y 154: `(3,62004,0,2000)` y `(3,62014,0,2000)`.
Estas incorporaciones se declaran posteriores a observar las regresiones.
No se presentan como casos nuevos. La base esperada es 61 niveles
(52+5+4); se verifica por paridad de acciones y score con los artefactos
anteriores antes de recibir propuestas. La instrumentación nueva solo
produce observaciones de este desarrollo y registra su coste temporal.

El primer micro usa una semilla de investigación nueva, `823101`, dieciocho
plazas por brazo, cuatro workers para juegos y orden de brazos barajado con
`823000`. Es un diagnóstico de mecanismos de un recorrido por brazo;
no demuestra superioridad estadística ni reemplaza la confirmación S.
No se añaden semillas después de ver resultados para buscar un pase.

Cada propuesta usa una duración de la lista B22 y una guarda de una a tres
features distintas con los mismos átomos. El actor, el score, el límite de
2.000 acciones y el juez se conservan. Aceptación del micro y desarrollo
amplio: **ganancia neta ≥2 y ninguna pérdida individual de niveles o score,
con tolerancia `1e-10`**, replay exacto y auditoría independiente. Conservación
reservada: ninguna pérdida individual, sin exigir otras dos ganancias.
Permitir investigar descendientes de una rama de +1 no permite aceptarla.

M23 implementa cuatro cambios medibles:

1. Reconocer candidatos cuya guarda no coincide con ninguna lectura efectiva
   de la base. Esto solo prueba inactividad sobre esas trayectorias y esa
   intervención; no elimina guardas por compartir una firma observacional.
   La selección interna puede evitar esos candidatos, registrando candidatos
   inspeccionados, tiempo CPU y motivo. Una propuesta final inválida o
   repetida sigue consumiendo su plaza; no hay generaciones ni simulaciones
   adicionales gratuitas.
2. Conservar para investigación las ramas de +1 sin pérdidas y los
   descendientes que reducen pérdidas manteniendo una ganancia útil. Su
   prioridad es: menos reparaciones servidas a su linaje, menos partidas con
   pérdidas, mayor ganancia neta y, en empate, descendiente más reciente.
   Cada nodo admite como máximo dos hijos y cada linaje cuatro reparaciones.
   Los resultados de un padre nunca se atribuyen al hijo.
3. Reconsiderar el mejor descendiente después de cada resultado. Eliminar la
   obligación de probar un segundo hijo distante del padre anterior cuando
   existe un descendiente más prometedor. Mantener hasta ocho reparaciones
   y al menos diez exploraciones globales si se agotan las dieciocho plazas.
4. Distribuir las reparaciones entre candidatos con distintos compromisos de
   cobertura de ganancias y exposición a contextos de pérdidas. El ranking
   no convierte solapamientos en garantías. Las ocho plazas alternan tres
   órdenes: menor exposición a pérdidas; mayor cobertura de ganancias; y
   menor diferencia exposición−cobertura. Los empates se deshacen por hash
   de semilla/plaza/propuesta. Una asociación desconocida usa exposición 1
   o cobertura 0 para ordenar, manteniendo el resultado real como desconocido.
   Este micro mide el cambio conjunto; no separa los cuatro efectos.

En exploración global, M23 inspecciona como máximo 64 muestras de la
distribución B22 por plaza, registra cada descarte y entrega la primera
activa y no repetida. Si agota las 64, entrega la última y consume la plaza.
El recorrido global usa índices `global_index*64 + draw`. El coste de estas
inspecciones se conserva; R22/M22 mantienen su corriente original. Las
reparaciones enumeran los vecinos legales de una edición del padre,
conservan HOLD y excluyen solo duplicados exactos e inactividad demostrable
sobre la base. No se importan guardas ganadoras del historial humano.

Para N7 y N14, una llamada por plaza recibe la gramática, los valores por
defecto, un resumen común de la base y feedback propio validado. Debe incluir
los efectos por partida de todos sus intentos. En el último intento medido,
detalla las acciones por nivel y hasta dos lecturas HOLD de las dos mayores
pérdidas y la mayor ganancia de niveles. Las lecturas se ordenan por extremos
numéricos de features variables; el resto usa orden canónico. Las listas
compactas declaran sus columnas y cuántas lecturas omiten; un diccionario
evita repetir los mismos vectores. Los cambios de nivel y los indicadores
de pérdida individual son exactos. Los scores mostrados usan cuatro cifras
significativas; el juez y el recibo conservan su precisión completa. Ninguna
pérdida se elimina de la tabla de resultados por esta compresión. El resumen
conserva el último intento medido aunque después haya respuestas inválidas.
Los IDs
del resumen son locales y no se admiten en la gramática ejecutable.

Los dos modelos usan la misma familia, variante Instruct, cuantización,
backend, plantilla, temperatura y límites de entrada/salida. Deben fijarse
repositorio, revisión, hashes reales de pesos, tokenizer y ejecutor. No se
mezcla el Qwen3-4B de B20 con un supuesto control 7B. Los nombres de producto
no sustituyen a la comprobación del archivo. El tamaño se comprueba sumando
las dimensiones de los tensores GGUF; el formato Q4_K_M y la arquitectura se
comprueban en sus metadatos. Los repositorios oficiales consultados son
[7B](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct-GGUF) y
[14B](https://huggingface.co/Qwen/Qwen2.5-Coder-14B-Instruct-GGUF). Las revisiones
de pesos son commits concretos, pendientes de registrar con sus hashes.

Enmienda de instrumento R3, 8 de octubre de 2026, anterior al micro:
«misma plantilla» significa el ChatML efectivo generado por `chat()` y
enviado mediante `--no-conversation --no-escape`. Las plantillas Jinja
embebidas de los GGUF oficiales difieren; R2 se detuvo al compararlas, antes
de preparar el manifiesto, generar propuestas o jugar partidas. Se conservan
ambos hashes y su comprobación individual de integridad. R3 sustituye la
igualdad entre esos hashes por una comprobación con los tokenizadores reales:
delimitadores distintos de un token, tres inicios y dos finales de mensaje,
misma secuencia tokenizada para un mensaje de diagnóstico fijo y ausencia de
tokens automáticos adicionales respecto al contador de presupuesto. El recibo
`prompt_protocol` queda incluido en el registro congelado y se recalcula
al verificarlo. El diagnóstico no genera texto ni contiene soluciones del
experimento. La familia, pesos, cuantización, propuestas, semillas, juez y
presupuestos científicos se conservan. No se atribuyen resultados a R2.

Se propone un máximo común de 8.192 tokens de entrada y 768 de salida por
llamada, treinta y seis llamadas en total. El prompt semántico completo debe
caber en ambos tokenizadores; de lo contrario se detiene la preparación.
Los fallos de parseo consumen su llamada y su plaza, y pueden recibir feedback
en la siguiente plaza. Las llamadas fallidas, respuestas sin propuesta y
duplicados conservan su coste. El evaluador registra la respuesta original,
los bytes exactos del prompt, su parseo y el programa finalmente ejecutado.

El modelo solo propone JSON. No puede modificar el verificador ni ejecutar
herramientas. El resultado propio se proporciona entre llamadas; no se
solicita un monólogo interno. La mini terminal muestra observaciones,
propuesta, motivo breve declarado y veredicto medido. Los textos del visor no
se reinyectan al actor. La auditoría repite el programa propuesto; no exige
que una inferencia GPU reproduzca el mismo muestreo palabra por palabra.

Los presupuestos de propuestas y partidas son iguales entre brazos; los
límites de tokens son iguales entre N7 y N14. Esto no iguala los FLOPs ni el
tiempo de GPU de tamaños diferentes. Se reportan por separado GPU-segundos,
tokens, tiempo de búsqueda, partidas y coste por candidato válido. No se
presenta una ventaja a igual número de llamadas como ventaja a igual coste
total de cómputo.

| Fase propuesta | Partidas físicas máximas |
|---|---:|
| Micro: 5 brazos × (base + 18 propuestas) × 14 casos × 3 ejecuciones | 3.990 |
| Desarrollo amplio: base común + hasta 5 finalistas, 160 casos × 3 | 2.880 |
| Conservación: base común + hasta 5 finalistas, 80 casos × 3 | 1.440 |
| Máximo condicionado de las tres fases | 8.310 |

Las tres ejecuciones son medición, replay y auditoría con caché separada.
La base común de las fases posteriores se comparte mediante un recibo exacto
con el mismo actor, política, casos, observación y runtime. Todos los costes
quedan contabilizados. No se transfieren sobras de presupuesto a generar
más propuestas. No se abren APIs de pago, instancias de pago ni publicaciones.

Cada brazo detiene la búsqueda en su primer pase auditado. Los cinco
finalistas, incluidos los ausentes, se congelan conjuntamente antes del
desarrollo amplio. Los fallos amplios se informan sin sustituir al finalista.
Solo los que conserven la mejora pasan a los 80 casos reservados; antes se
revisa su historial de exposición por identidad de mundo/semilla. Las
cohortes B22 sin abrir no se convierten automáticamente en desarrollo.

La campaña y el examen B1–B5 requieren una condición posterior desde
SEMILLA, confirmación dimensionada y controles de aportación del LLM. Este
micro no distingue aún el beneficio de más muestreo del beneficio de recibir
feedback: esa ablación necesitará un brazo genérico sin resultados propios
en la confirmación B22-N. Tampoco demuestra automejora recursiva.

Si M23 mejora frente a M22 y N7/N14 no lo mejoran, priorizaremos el selector.
Si un neocórtex encuentra candidatos conservadores que sobreviven al
desarrollo amplio y a conservación, justificará el piloto posterior. Si
ninguno encuentra un pase, la distribución de inactividad, cobertura,
descendientes y pérdidas permitirá determinar qué mecanismo volver a
investigar. Con un único recorrido por brazo no se concluirá que un modelo
o algoritmo es generalmente superior.

La conservación se reserva a 80 casos de mundos v2/v3 con semillas
67000–67039. El registro de exposición comprueba identidades en manifiestos
históricos; no certifica ejecuciones externas no registradas. La calibración
experimental es la primera base de 14 casos con replay y auditoría: 42
partidas incluidas en las 3.990 del micro y reutilizadas al reanudar.

La duración se estimará tras una calibración registrada del ejecutor y los
modelos reales. El ritmo de B22, con doce casos y cero inferencias, no basta
para prometer una hora de cierre de B23.
