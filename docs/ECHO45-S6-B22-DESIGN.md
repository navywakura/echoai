# S6-B22 — validación independiente y reparación de condiciones

Contrato privado del 6 de octubre de 2026, posterior al cierre B21-A.
Implementa la primera etapa del informe `B22-investigacion-20261006.pdf`
entregado por el propietario. El PDF completo está disponible localmente;
el ZIP citado no estaba en Descargas. El manifiesto fija el hash del PDF,
de este contrato, del código, pruebas, runtime, entradas y cohortes antes
de jugar. B21 conserva `CLOSED_NO_PROMOTION` y todas sus fuentes originales.

El alcance ejecutable es B22-V más el piloto B22-S y validación de hasta dos
finalistas. La confirmación estadística S, B22-N y B22-E se dimensionan con
contratos posteriores, como indica el informe. Ninguna salida de esta etapa
puede poner S6 en verde. No se utilizan APIs de pago ni GPU: el trabajo inicial
es simulación determinista CPU, cuatro procesos y cero generaciones LLM.

B22-V importa el objeto serializado exacto del segundo intento
`random-821117` de B21 y su base, orden de reglas, hashes y recibos. El
supervisor compara su composición con la propuesta guardada y exige el cierre
auditado y revisión aritmética B21 válidos. El investigador S no recibe esa
política ni los intentos rechazados/ganadores B21, el PDF o controles humanos.

V repite base y candidato en las doce partidas del micro: exige igualdad
completa de filas con B21, incluida la traza instrumental de desarrollo.
Después mide ambos en las 160 partidas de desarrollo de B20. Exige ganancia
≥2 y ninguna pérdida individual de niveles o score, tolerancia original
1e-10. Solo si pasa, conserva ese candidato exacto para medirlo en 80 casos
nuevos: mundos v2/v3, semillas 65000–65039, réplica 0, 2.000 acciones.
Allí exige conservación individual; no otras dos ganancias nuevas.

La cohorte S de transferencia es distinta: v2/v3, semillas 66000–66039,
misma réplica y límite de acciones. Se revisan manifiestos, perfiles,
particiones y aperturas históricos por identidad mundo/semilla, ignorando
diferencias de réplica o presupuesto al detectar exposición. La revisión
conserva inventario y hashes; su alcance es el laboratorio registrado, no
supuestas ejecuciones externas desconocidas. Las dos antiguas pérdidas B18
ya son desarrollo y no se presentan como casos nuevos.

El orden de ejecución es V micro/amplio, S micro completo, congelación
conjunta de finalistas, conservación V, desarrollo amplio y conservación S.
Esto evita abrir resultados nuevos antes de congelar los candidatos S. Un
fracaso científico de V no impide medir S. Una discrepancia de instrumento
detiene todo como INVALID. No se instrumentan las cohortes protegidas ni el
desarrollo amplio: se registran acciones reales y puntuación del ejecutor
congelado, sin agregar sensores al actor. La cantidad exacta de activaciones
de HOLD en esas cohortes queda desconocida; se reportan cambios de acciones
como evidencia parcial, sin equipararlos con activaciones de la regla.

S compara R22 y M22 en ocho pares. Semillas, en orden neutral de prioridad:
822101, 822117, 822129, 822143, 822157, 822173, 822191, 822211. El orden de
ejecución de las dieciséis celdas se baraja con 822000 y se guarda en el
manifiesto. Cada recorrido empieza desde la base aceptada B14 usada en B21,
con historia de investigación vacía, hasta 18 propuestas y parada en el
primer pase auditado. No es el ensayo desde SEMILLA.

El universo común contiene un único parche HOLD con valores
0,1,2,4,8,12,16,20,24,32 y conjunciones de una a tres condiciones de features
distintas, usando los átomos B20. No hay semillas, IDs de tarea ni coordenadas
privadas en el lenguaje. Cada intento global elige HOLD uniformemente; para
la guarda, mezcla 1/2 muestreo general de sintaxis y 1/2 elección uniforme
entre guardas de la biblioteca ampliada B20 calculada solo sobre la base.
Sin biblioteca activa usa el muestreo general. Este elige uniformemente
longitud 1/2/3, subconjunto de features y átomo legal por feature. Todas las
guardas legales tienen soporte, aunque sean inactivas. La mezcla no es
uniforme sobre AST y no se llama equivalente al aleatorio histórico B21.

R22 no utiliza resultados ni lecturas de sus intentos para cambiar el muestreo.
Los intentos globales M22 usan exactamente la misma distribución y corriente
sembrada, indexada por número de exploración global, no por slot. Las semillas
del mundo y las corrientes de duración, modo, guarda, reparación y desempate
están separadas. La finalización de workers no interviene en la selección.
Duplicados e inactivos consumen su plaza lógica; no se vuelve a sortear gratis.

M22 reserva bloques de dos reparaciones cuando hay padre con ganancia neta
≥2 y alguna pérdida, dos plazas disponibles y presupuesto de reparación.
Se ordenan padres por menos casos con pérdida, más ganancia neta y menor ID.
Cada padre recibe un solo bloque. Un hijo medido puede convertirse en padre.
El segundo hijo completa el bloque antes de cambiar de rama, salvo pase
temprano. Hay hasta ocho reparaciones; un recorrido agotado conserva al menos
diez exploraciones globales. Si no hay dos vecinos inéditos legales se
devuelven esas plazas a exploración y se registra el motivo. También se
registran ramas sin reparar por falta de presupuesto o fin del recorrido.

Los hijos mantienen la duración del padre. Su vecindario permite una única
edición de literal: cambiar átomo, sustituir feature, añadir o quitar una
condición respetando una a tres features distintas. El primer hijo prioriza
menor `loss_context_overlap` y mayor `gain_context_overlap`. Se calcula la
fracción de contextos efectivos distintos cubiertos en cada caso y después
la media entre casos, para no premiar repeticiones o partidas largas. Sin
contextos suficientes el campo es desconocido. El segundo hijo prioriza
distancia observacional respecto al primero, después los solapamientos y
desempate sembrado. Son asociaciones y no predicciones de niveles ni de
ausencia de riesgo. El resultado del hijo empieza como desconocido, incluso
manteniendo HOLD. Otra duración solo aparece por exploración global.

No se eliminan guardas del universo por equivalencia en una traza. El filtro
local solo evita volver a medir el mismo AST de propuesta dentro del
vecindario; la exploración global mantiene su soporte. El archivo conserva
las 18 hipótesis como máximo, con padre, propuesta, vector de efectos,
consumos y estado auditado. El juez recibe la política ejecutada y vuelve a
medir todas las doce partidas del micro en cada intento.

Cada medición tiene replay y después ejecución en otro proceso/caché. Antes
de auditar un candidato S se reconstruye la solicitud desde los bytes exactos
del investigador y se compara la política que realmente va a ejecutarse.
Las discrepancias no se contabilizan como resultado científico negativo.
El supervisor solo usa recibos auditados para detener al primer pase.

| Reserva | Límite de partidas físicas |
|---|---:|
| V: (12+160+80) × 2 políticas × 3 ejecuciones | 1.512 |
| S: 8 pares × 2 brazos × (base+18 propuestas) × 12 × 3 | 10.944 |
| Primer finalista R22: (160+80) × 2 políticas × 3 | 1.440 |
| Primer finalista M22: (160+80) × 2 políticas × 3 | 1.440 |
| Total asignado | 15.336 |

Las 664 partidas hasta 16.000 quedan sin asignar; no habilitan nuevas
hipótesis ni reintentos automáticos. No se transfiere presupuesto entre
reservas. El libro distingue reserva, inicio, finalización y fallo mediante
recibos por trabajo. Se reserva antes de jugar; una ejecución iniciada sin
recibo completo requiere recuperación explícita. No se devuelve su coste.
La caché solo reutiliza políticas exactas dentro del mismo recorrido/fase,
con hash y recibo completos; replay y auditoría tienen cachés distintas.
Los registros completos se guardan antes de borrar diarios efímeros.

El primer recorrido con pase de cada brazo, siguiendo la lista neutral de
semillas, aporta su primer candidato auditado. Ambos finalistas se congelan
antes de abrir transferencia, independientemente del brazo que haya ganado.
Se validan en 160 casos y, si pasan, en los mismos 80 S nuevos. No se
selecciona un sustituto tras una regresión. Otros ganadores del micro quedan
con transferencia no medida. Un R22 elegible avanza aunque M22 no lo sea.

La unidad estadística es el par de recorridos, nunca cada propuesta ni cada
replay. Se informan ambos/solo M/solo R/ninguno, diferencia de proporciones,
McNemar exacta bilateral al 5 % con dirección favorable a M, y rango hasta
primer pase, asignando 19 a fracaso tras 18 como descripción censurada.
Se incluye un intervalo conservador Hoeffding al 95 % para variables de par
en [-1,1], condicionado a corrientes independientes en este banco fijo.
El informe registra coste físico, CPU y búsqueda por separado. Incluso un
piloto significativo mantiene la confirmación general S pendiente: harán
falta versión congelada, efecto mínimo relevante, potencia y paneles nuevos
prerregistrados. No se aumenta n después de mirar el p-valor.

Los estados científicos V/S/N/E son independientes. V puede pasar o fallar
con instrumento válido. El piloto S publica sus resultados y mantiene
INCONCLUSIVE para la afirmación general pendiente de confirmación. N y E
siguen NOT_RUN. Un fallo de integridad se etiqueta INVALID, con motivo.

El runtime es una copia mínima enumerada por hash, sin documentos, PDF,
tests ni módulos de controles humanos. El investigador es una función sobre
JSON permitido sin archivos, red, herramientas ni evaluación directa. El
supervisor conserva entradas privilegiadas para V, pero no las incorpora a
los bytes del investigador. Esto es aislamiento de datos, no un sandbox
adversarial de Python. Se usa Python 3.12.13, numpy 2.3.2 y arcengine 0.9.3,
con el actor/juez anterior sin cambios y límite de 240 s por partida.

Las decisiones de desarrollo se registran en el diario existente
`live/journal.jsonl` compatible con `observe.py`. No se crea otro bus ni se
genera un monólogo. La fuente del PDF, las pruebas, resultados y estado
permanecen privados; este contrato no autoriza publicación web.

Después: N comparará N0/NF/NA con las tres plazas LLM y controles del informe,
presupuesto propio y modelo/tokenizador congelados. E recuperará el contrato
completo desde SEMILLA, mecanismos pertinentes, FIJO/ECHO/SIN FILTRO, piloto,
campaña y examen nuevo B1–B5. La regla B21 no se preinstalará como si hubiera
sido descubierta desde SEMILLA. Los resultados S6 siguen sin equivaler a
puntuaciones ARC oficiales.
