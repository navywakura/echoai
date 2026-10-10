# ECHO-4.5 · S6-B24 · contrato de ejecución

9 de octubre de 2026. Diagnóstico privado, una semilla de investigación.
El propietario autoriza terminar B24 y cerrar después ECHO-4.5 aun cuando
S6 siga pendiente o resulte negativo. El cierre de versión no cambia el
criterio de S6 ni convierte este micro en un examen aprobado.

Este contrato concreta `ECHO45-S6-B24-CONDITIONAL-PLAN.md`. El actor, sus
features, gramática y juez conservan las fuentes de B23-R4. La intervención
es el investigador y su interfaz de selección. No se entrenan pesos.

## Condiciones y presupuesto

La semilla de investigación es 824101. La permutación de brazos usa
`random.Random(824000).sample` sobre `[R4-REF,B24-G,B24-S,B24-I,B24-C]`;
su orden resultante es R4-REF, B24-G, B24-C, B24-I, B24-S. Cada brazo tiene
18 plazas y se detiene en su primer pase auditado. Ningún brazo recibe
resultados de otro. Los datos iniciales son las 14 partidas de desarrollo
conocido de R4; la base debe reproducir exactamente su comportamiento y
sus 61 niveles. La cohorte completa y los parámetros constan en `config()`.

R4-REF conserva el prompt y la gramática JSON de R4, usando su 7B. G aplica
el constructor nuevo y selección determinista sin modelo. S usa un único
investigador corregido. I tiene tres investigadores con archivos privados.
C tiene tres investigadores que comparten recibos al terminar cada ronda.
I/C tienen tres rondas de seis plazas, dos por investigador. El orden y los
límites individuales se derivan de la semilla, sin utilizar resultados.
Los tres investigadores lógicos comparten una instancia de pesos por turnos.

S/I/C usan la misma interfaz, constructor, límites y semántica. Los contrastes
son S/R4 (paquete de corrección), S/G (valor de selección con LLM), C/I
(intercambio) e I/S (partición de contextos). Una semilla no permite afirmar
superioridad estadística general. Se publicarán costes realizados y techos,
sin presentar como idénticos los gastos de brazos que usaron menos intentos.

Máximos: 3.990 partidas físicas de micro; 2.880 de desarrollo amplio; 1.440
de conservación. Total condicionado 8.310. Cada evaluación incluye ejecución,
replay y auditoría en proceso y caché separados. Hasta 72 llamadas científicas
más ocho de formato. G no llama al modelo. El límite por partida sigue siendo
2.000 acciones, con timeout del instrumento de 240 segundos y cuatro workers.

## Modelo y mensajes

Qwen2.5-Coder-7B-Instruct-GGUF, revisión
`13fb94bfda8c8cf22497dc57b78f391a9acb426a`, Q4_K_M, SHA256
`509287f78cb4d4cf6b3843734733b914b2c158e43e22a7f4bf5e963800894d3c`.
llama.cpp `79e0b68c178656bb0632cb8602d2940b755077f8`; dos T4, capas GPU 99,
partición 1,1. Python 3.12.13, numpy 2.3.2, arcengine 0.9.3.
La primera preparación congela hashes de los ejecutables y tokenizer;
las reanudaciones reutilizan sus bytes, sin recompilar otro perfil.

Se conserva ChatML explícito, temperatura 0,6, top-k 40, top-p 0,95,
8.192 tokens de entrada, 768 de salida y ventana 9.216. No hay recorte
silencioso, segundo intento gratuito ni reparación semántica del JSON.
La gramática de S/I/C solo permite un `candidate_id` del catálogo exacto.
Se conserva el menú, su orden, hashes, salida y política reconstruida.
El preflight ejecuta cuatro instrucciones sintéticas del protocolo R4 y
cuatro de selección por ID. No contiene observaciones del mundo ni soluciones
científicas, y mantiene un contador separado de ocho llamadas reales.

## Investigación y aislamiento

El constructor inspecciona hasta 2.048 candidatos por plaza y ofrece como
máximo 64. Su distribución, semillas y desempates quedan congelados en
`echo_arc/s6b24_search.py` y `search.config()`. Los candidatos provienen de
la gramática existente y de ediciones de una condición del padre; no se
importan ganadores humanos. Los investigadores comparten un catálogo de sintaxis, no resultados entre brazos.
Se contabilizan inspecciones, duplicados,
inactividad, truncamiento y tiempo CPU. La selección del LLM no ejecuta
código arbitrario ni accede a ficheros del custodio.

Una inactividad se certifica contra todos los consumos HOLD de la base
observada: esa intervención única no cambiaría ningún valor consumido.
El certificado no se extrapola a otra base o a otro mundo. Las firmas
parciales coincidentes no eliminan candidatos activos. La exclusión de
duplicados se limita a los recibos visibles para ese investigador.

El máximo de reparaciones es ocho por brazo; I/C distribuyen [3,3,2] por
permutación sembrada. Hay como máximo dos hijos por nodo y cuatro
reparaciones por linaje. Una reparación conserva el HOLD del padre y cambia
una condición. Las ramas con ganancia positiva pueden orientar investigación;
no sustituyen la política estable. Cada hijo debe obtener sus propios
resultados. El consumo ineficaz más reciente no borra un padre prometedor.

El dossier conserva efectos de todos los casos, rangos numéricos completos
y ejemplos conjuntos realmente observados. La relación entre un consumo y
una pérdida posterior se presenta como asociación, sin atribución causal
ficticia. El prompt explica HOLD por defecto 40, dónde se consume, las
guardas y el score. Si lo esencial no cabe en el contexto, se detiene el
instrumento. Los inputs serializados de I solo contienen historia propia;
C incorpora historia ajena únicamente tras la barrera de ronda.

## Verificación, selección y conservación

El juez conserva ganancia neta de al menos dos niveles, ninguna pérdida
individual de niveles o score, tolerancia 1e-10 y reproducción exacta. La
suma de scores no compensa pérdidas individuales. Un fallo de formato,
transporte, paridad, custodia, replay o contabilidad detiene el instrumento
sin contabilizarse como resultado científico negativo.

La política ganadora de cada brazo se congela antes de medir las 160 partidas
de desarrollo amplio, que ya son conocidas. Solo los ganadores que conservan
el criterio allí abren las 80 partidas de conservación bajo un permiso de
política exacta. La revisión de exposición registrada procede de B23 y se
complementa con sus cierres R3/R4 sin apertura de conservación; no acredita
la ausencia de exposiciones externas no registradas. No se devuelven pérdidas
de conservación al investigador ni se elige otro ganador tras verlas.

El paquete incorpora las fuentes congeladas previas y los ficheros B24
nombrados expresamente. Excluye autopsias, CSV de propuestas, controles humanos
y diarios de reservas. El investigador recibe exclusivamente la base permitida
y su archivo autorizado. El auditor reconstruye mensajes, política y feedback desde
esos bytes y las trayectorias medidas; recalcula score, pérdidas y presupuesto.
Cada fila de cada medición se enlaza con su caso, política, caché y recibo
de ejecución física. La identidad de caché incluye el intento: dos
investigadores aislados que proponen lo mismo pagan sus respectivas ternas.
Solo la reanudación del mismo intento reutiliza sus mediciones, además de
la base común declarada en desarrollo amplio y conservación.

## Cuota y continuidad

Kaggle dispone de cuota GPU variable; el corte de transporte se fija antes
de las partidas. Cada sesión solicita una ventana de 7.200 segundos desde
el inicio del notebook. Al alcanzar ese plazo se pausa antes de la siguiente
medición, sin interrumpir una que esté en curso. Una terna parcialmente
completada conserva sus recibos para continuarse. Una llamada o partida
realmente interrumpida exige recuperación declarada y nunca un reintento
silencioso. El corte puede sobrepasar el plazo por la medición en curso.

Se exportan resultados y ejecutables nativos. La continuación conserva ruta,
manifest, fuentes, pesos, semillas, presupuestos e historial. Suponiendo cuota
disponible se reanuda desde el siguiente trabajo pendiente; de lo contrario
queda en espera hasta la renovación. No cambia el resultado de los brazos
por tiempo, ni se trasvasan reservas. El tiempo de pared por sesión y la espera
por cuota se informan separados del coste medido de investigación. Los tiempos
de cada intento se acumulan en segmentos persistentes, incluyendo los cortes
y la reconstrucción al reanudar; no se reinician al guardar la última fase.

El micro y las fases condicionales concluyen con una revisión completa.
`closed.json` mantendrá `s6_green=false`, examen sin abrir, campaña y
confirmación sin ejecutar. B24 puede acreditar un mecanismo acotado de
búsqueda o transferencia; S6 requeriría su protocolo desde SEMILLA y B1–B5.
La posterior evaluación ARC y el cierre de ECHO-4.5 serán artefactos separados.
