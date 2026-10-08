# ECHO-4.5 · integración relacional V3, condición privada

3 octubre 2026. El propietario autoriza medir utilidad también fuera de ARC.
Este contrato amplía el alcance de los módulos; no transforma los resultados
ARC negativos anteriores en positivos. S6 y el examen final quedan aplazados.

REL-DSL-1 añade escenas, relaciones, ligadura de roles, edición de objetos y
renderizado. La gramática es finita, con ambigüedades explícitas. Se enumeran
hipótesis y se verifican contra todas las demostraciones. Ni el ejecutor ni el
selector reciben respuestas de test, semillas, familias o programas generadores.
Las fuentes de V1/V2 y los contratos anteriores se conservan por hash.

ARC-3E-POLICY-1 transfiere el mecanismo de retornos diferidos de village3 a dos
acciones nuevas: consultar recibos primero o buscar primero. Usa los recibos
3E existentes, contextos observables de rejillas y un horizonte de 64 tareas.
Las tablas de la aldea no se reciclan: las acciones tienen otro significado.
`begin` abre crédito; un contador separado impone presupuesto; `charge` registra
trabajo; `mature` aprende del retorno observado a edad comparable. Costes
tardíos se atribuyen al ticket original. Las decisiones pendientes se conservan
al reiniciar. La política se congela durante confirmación entre tareas.

Desarrollo: semillas 47000–47015; ajuste de política 47100–47355. Confirmación:
48000–48031, fijadas antes de medir. Auditoría: segunda ejecución en otro
proceso. Las semillas y fuentes se sellan en profile.json después de depurar
el instrumento y antes de abrir la confirmación. Un error instrumental bloquea
la condición; una recuperación requiere recibo explícito y nueva raíz.

Comparaciones con igual tope de trabajo lógico por tarea y mismas entradas:

| Puerta | Comparación y requisito previo |
|---|---|
| REL | DSL geométrico/relacional × orden fijo/aprendido. Relacional añade aciertos en composiciones con cambios de tamaño, color y posición; conserva las familias simples |
| MEM | Política adaptativa conserva aciertos del orden fijo, reduce ≥10% el trabajo; retirar recuerdos pertinentes aumenta trabajo más que retirar otros; estado se reproduce entre procesos |
| SYN | Refinamiento de profundidad dos supera profundidad uno en composiciones; conserva tareas de una operación |
| VIEW | Ocho marcos vs marco original con igual presupuesto: más aciertos en orientaciones nuevas, sin pérdidas en las tareas canónicas del banco |
| CONS | Entre hipótesis que pasan demostraciones, detectar desacuerdo y abstenerse elimina compromisos erróneos en el banco ambiguo; conserva respuestas en controles inequívocos. Se declara la pérdida de cobertura; no se interpreta como más aciertos ARC |
| GUIDE | Además de CAP-STRESS-1, comprobar recuperación de programas ejecutables a carga alta con consulta de motivos transformados. 500k supera a 65k y sin guía; programas elegidos pasan verificación exacta y el juez comprueba consultas aparte |

Los generadores construyen puzzles de objetos con reglas explícitas. Un juez
independiente del ejecutor produce las salidas. La transferencia medida es a
instancias, orientaciones y combinaciones reservadas de una gramática declarada;
no es un resultado oficial ARC ni adquisición de operaciones desconocidas.
La prueba de guía es recuperación de asociaciones adquiridas, no generalización
de etiquetas arbitrarias a motivos nunca vistos. Datos de ajuste y coste de
adquisición se reportan aparte; no se atribuye gratis ese trabajo.

Una unidad lógica contabiliza visitas de celdas, pares de objetos, consultas de
hash y comparaciones del verificador. CPU, memoria, candidatos y llamadas de
operaciones se informan aparte. El mismo límite no obliga a consumirlo completo.
El orden aprendido puede ahorrar trabajo sin aumentar los aciertos. La
consistencia expresa incertidumbre de la búsqueda realizada; acuerdo finito
no constituye prueba de una regla única entre todos los programas posibles.

No hay llamadas al modelo, GPU, publicación web ni reapertura de reservas ARC.
Se usa el Journal existente y observe.py para las observaciones, propuestas,
costes y resultados reales. Una puerta permanece roja si su contraste falla.

Adenda de diseño antes de la confirmación: el piloto 47000–47003 encontró
ahorro de planificación pequeño en la mezcla completa, dominada por búsquedas
fallidas de orientación. El contraste primario MEM se concreta en dos regímenes
equilibrados: rotación directa barata y composición reutilizable (32 de cada
uno). Debe ahorrar ≥10% frente al mejor de AMBOS órdenes fijos, conservando
aciertos en la batería completa. Se publica también el ahorro global de seis
familias aunque sea pequeño. Este cambio de población se declara a partir de
desarrollo; no se presenta como una confirmación del primer borrador amplio.
Los tests de consulta incluyen tres destinos donde las demostraciones tenían
dos. SYN mide composición de primitivas conocidas; no inventa primitivas.

GUIDE usa ocho semillas 49100–49107, 16.384 motivos binarios de 7×7 y 32
programas (ocho simetrías × recorte sí/no × escala 1/2). Cada asociación se
verifica antes de aprender y se observa dos veces. Las 512 consultas por
semilla cambian color y margen espacial conservando el motivo. Los brazos
sin guía/65k/500k tienen una propuesta verificable y 100.000 unidades de trabajo;
un control de búsqueda de los 32 programas informa el coste de recuperar todo
sin guía. La puerta pide ventaja media ≥5 puntos de 500k sobre ambos brazos,
signos favorables en las ocho semillas y ninguna respuesta comprometida errónea.
Se informa coste de hashing, ajuste, memoria y consulta. La limitación de una
propuesta es parte del experimento; no acredita ventaja con búsqueda ilimitada.
