# S6-B20: diagnóstico del micro y expediente para B21

6 de octubre de 2026. Análisis privado posterior a las mediciones del micro,
con auditoría remota todavía en marcha. Este documento no modifica el contrato,
las fuentes ni los resultados B20. No declara un resultado auditado final.

El micro terminó sus mediciones a las 11:55:56 de Madrid. Se registraron 144
intentos, distribuidos en ocho recorridos de 18. Ninguno pasó V3. Todos los
veredictos registrados son V3: no aparecen rechazos V1 por formato en esas
144 entradas. Esto no demuestra ausencia universal de errores del instrumento;
la auditoría completa y la revisión final siguen siendo necesarias.

| Resultado por intento | Número | Proporción |
|---|---:|---:|
| Alguna pérdida individual de niveles o puntuación | 85 | 59,03 % |
| Sin pérdidas, ganancia de niveles cero | 28 | 19,44 % |
| Sin pérdidas, ganancia de un nivel | 31 | 21,53 % |
| Ganancia de al menos dos niveles sin pérdidas | 0 | 0 % |

Las categorías son excluyentes. La categoría «sin ganancia de niveles» puede
incluir una mejora de puntuación. No equivale necesariamente a conducta inerte.
El porcentaje describe intentos de este recorrido, no una probabilidad de
éxito sobre hipótesis independientes ni una puntuación ARC oficial.

| Recorrido | Intentos | Con pérdidas | +1 sin pérdidas | Cero niveles sin pérdidas | Aceptados |
|---|---:|---:|---:|---:|---:|
| C0 | 18 | 3 | 7 | 8 | 0 |
| C1 | 18 | 10 | 6 | 2 | 0 |
| H0-820101 | 18 | 15 | 0 | 3 | 0 |
| H1-820101 | 18 | 9 | 6 | 3 | 0 |
| H0-820117 | 18 | 15 | 0 | 3 | 0 |
| H1-820117 | 18 | 9 | 6 | 3 | 0 |
| H0-820129 | 18 | 15 | 0 | 3 | 0 |
| H1-820129 | 18 | 9 | 6 | 3 | 0 |

H0 llegó a una ganancia neta de ocho niveles, acompañada de pérdidas
individuales. H1 llegó como máximo a un nivel sin pérdidas. C1 tampoco obtuvo
una ventaja sobre C0 en máximo de niveles conservador y tuvo más rechazos con
pérdidas. No hay evidencia de superioridad del controlador nuevo en este micro.

La condición compartía una generación inicial del LLM por cada par H0/H1:
tres llamadas físicas en total. Los siguientes candidatos procedían del
buscador. Dentro de H0 las tres semillas produjeron series idénticas de niveles,
ganancias, pérdidas, puntuación agregada y veredictos; ocurrió lo mismo dentro
de H1. Los logs parciales no permiten concluir todavía que todos sus JSON de
propuesta sean idénticos. Es incorrecto describir el ensayo como 144 ideas
independientes del modelo o como un LLM que critica 144 veces.

**Qué exige el juez.** Para cada caso emparejado i:

\[
\Delta L_i=L_i^{candidato}-L_i^{base},\qquad
\Delta S_i=S_i^{candidato}-S_i^{base}.
\]

\[
V3=\left(\sum_i\Delta L_i\geq2\right)
\land\left(\forall i:\Delta L_i\geq0\land\Delta S_i\geq-10^{-10}\right).
\]

La base del cribado de doce casos suma 52 niveles. Un +1 sería un aumento
del 1,92 % en ese total, pero no alcanza V3. Un +2 sería el 3,85 %. Estos
porcentajes corresponden al banco procedural dirigido, no al porcentaje de
tareas ARC resueltas. Dos candidatos +1 sobre el mismo caso no suman +2;
cualquier composición requiere medir sus interacciones.

**El control de capacidad confirmó una posibilidad, con ayuda humana.** La
ejecución local y su auditoría independiente registraron 2.448 partidas.
El control humano pasó en los 160 casos de desarrollo con +6 niveles y sin
pérdidas. El candidato ampliado seleccionado consiguió +3, pero perdió score
en dos casos nuevos de desarrollo: índices 144 y 154. En ellos conservó cinco
y cuatro niveles, respectivamente; el score pasó de 9,525841950237028 a
9,03593149859053 y de 0,15665521666195617 a 0,04821154908691343.
El juez lo rechazó por esas pérdidas, aunque su agregado mejorase.

El control humano aceptado empleó HOLD=1 bajo level>=1, pending_effect=0 y
world_events<=16. Su regla se documenta como control conocido y queda
excluida de prompts, memoria inicial, prioridades y respuestas del ensayo
autónomo. Que exista esta regla refuta un techo absoluto del lenguaje en este
desarrollo; no prueba que la búsqueda pueda descubrirla ni que transfiera a
una reserva nueva. Esa reserva no se abrió en el control de capacidad.

**Restricción verificable del buscador.** En
`echo_arc/s6b20_search.py`, `rank_new` selecciona initial=0 cuando no hay
objetivo, y usa values=[initial]. Por tanto, una exploración sin padre solo
examina HOLD=0. Los dos primeros descendientes conservan el valor del padre
y cambian condiciones. El tercero conserva su condición y prueba el siguiente
valor mayor. La gramática permite diez duraciones, pero el selector no las
recorre libremente.

Se reconstruyeron únicamente solicitudes con datos locales existentes, sin
ejecutar juegos ni modificar archivos congelados. Los inicializadores C0 y C1
coinciden en HOLD=0 con level<=80. La biblioteca inicial tenía 420.986 formas
sintácticas, 577 firmas observadas, 577 representantes retenidos y ningún
truncamiento por el límite de 2.048. La guarda del control humano era legal y
estaba entre esos representantes. Sin embargo, los ocho candidatos de la
shortlist inicial de ambos controladores usaban valor cero. Hay acceso
sintáctico a la solución y acceso práctico limitado por la selección del valor.

La primera propuesta C0 registrada produjo 52->49 niveles y pérdidas en
cinco casos. La restricción del selector explica una parte de la cobertura
insuficiente; todavía no atribuye causalmente los 144 rechazos. Faltan los
pasos completos y sus prioridades para comprobar cada linaje.

**Otros límites que deben separarse.** El ranking atribuye ganancias y
pérdidas de partidas a conjuntos de lecturas. Esa asociación no identifica
qué lectura causó el resultado tardío. El coste de reiniciar depende de la
historia de actividad y de efectos remotos, mientras las guardas usan un
contexto instantáneo. `pending_effect=0` solo refleja la variable registrada;
no demuestra que toda actividad iniciada anteriormente haya terminado.
La necesidad de una nueva memoria temporal es una hipótesis, no una
conclusión de este micro: el control humano funcionó con las features actuales.

Agrupar guardas por coincidencia en observaciones ayuda a ordenar búsqueda,
pero no garantiza igualdad en estados nuevos. B20 declara correctamente esa
limitación. La revisión final debe distinguir esta agrupación heurística de
los certificados concretos de equivalencia por consumos completos.

B20 modifica HOLD y una biblioteca de guardas. No mide una ablación de la guía
de 500.000 unidades ni modifica pesos del LLM. Estos resultados no atribuyen
el fallo al tamaño neuronal, a la cuantización ni a la falta de GPU. Los juegos
son trabajo CPU; la GPU aceleró las generaciones iniciales.

**Qué falta para completar el expediente.** El log en directo guarda métricas
y veredictos, pero no los JSON completos de cada regla. Al cierre deben
recogerse `steps/`, `calls/`, `micro.json`, `micro-audit.json`, `closed.json`,
las mediciones y el recibo aritmético; comprobar hashes y exportar una tabla
con propuesta, padre, ranking, duración, condiciones, ganancia y pérdidas.
Hasta entonces no se afirmará haber leído las otras 143 reglas exactas.
Las desconexiones recuperadas del lector de logs no deben confundirse con
fallos del proceso remoto. Un fallo de replay o de fuente bloquearía el
instrumento y no constituiría un resultado científico negativo.

Los documentos B20 originales conservan su contexto histórico. El prompt de
implementación describe el estado anterior al lanzamiento; el archivo de
resultados es un informe automático mutable. Este análisis y el paquete
adjunto son cortes de información disponibles, con fecha y hashes propios.

La siguiente propuesta está en [B21](ECHO45-S6-B21-PROPOSAL.md). No hay una
implementación B21 ni un ensayo B21 iniciado. S6 permanece abierto.
