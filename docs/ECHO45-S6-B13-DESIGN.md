# S6-B13 — objetivo persistente y verificación secuencial

Condición nueva, privada, del 3 de octubre de 2026, posterior al rojo B12 y
a los controles dirigidos PROBE1/2. Se congela antes del primer juego B13.
El usuario ha pedido reanudar S6. Las fuentes anteriores permanecen intactas.
La reejecución independiente de PROBE2 reproduce 240 partidas: base 378,
variantes 28/33 383. Esos parches humanos no entran en los prompts ni en las
políticas iniciales de este experimento. No se presentan como autonomía.

La pregunta es si mantener una reparación prometedora como objetivo, mostrar
sus propios contrastes y devolver el resultado después de cada propuesta
permite que ECHO supere la solicitud genérica. B12 mezclaba lotes de cinco,
REFINE cambiaba otro operador y admitía valores ya vigentes. B13 conserva
la gramática y añade memoria de objetivo, límite de tres intentos sobre el
mismo objetivo/base, control del operador refinado y exclusión mecánica de
valores idénticos en todas las oportunidades observadas. No se codifica una
guarda, valor o partida favorable obtenidos en PROBE2. La exclusión no predice
utilidad y puede dejar propuestas de comportamiento idéntico, que se miden.

Modelo: Qwen3-4B-Instruct-2507 Q4_K_M local, SHA-256
`2fde00ce69dd4899c70d020845e2638353015bba0fdf161b3eb965f2bca4464e`.
Es distinto del Qwen2.5-Coder7B int8 de B12, por eso B13 se declara por separado.
Ambos brazos usan idénticos pesos, llama.cpp, cuatro hilos, temperatura 0,6,
top-k 40, top-p 0,95, semilla emparejada y máximo 160 tokens de salida.
Contexto 4096; entrada máxima 3072 tokens medidos con el tokenizador del GGUF.
Las variantes de compactación se eligen en orden: cuatro antecedentes, dos,
ninguno y después una oportunidad por operador/caso, con las features en
vectores numéricos y su orden de columnas explícito (representación sin pérdida).
Los contrastes del objetivo también usan esa representación en el último nivel.
Nunca se corta texto;
se conservan objetivo, contrastes del objetivo y programa vigente. Si no
caben, el experimento se detiene. Se guardan tokens, petición completa,
gramática, comando, stdout/stderr y respuesta. Límite 900 s por llamada.
Una llamada interrumpida cuenta y no se repite sin recuperación declarada.
No hay nube, gasto de API ni cambios del núcleo NEXUS-0.

Todos parten de SEMILLA vacía, el mismo ejecutor de B12. A son las 80 partidas
de desarrollo de las versiones gym 2/3, semillas 0–39, repetición 0 y 2000
decisiones. Es desarrollo conocido, no confirmación disjunta. B utiliza nuevas
semillas 26320–26339, mismas versiones/presupuesto. No se muestran sus datos:
el modelo solo recibe si su propuesta fue aceptada o rechazada por V4.
Reserva nueva: semillas 26400–26459, versiones 2/3, tres repeticiones, 360
partidas y 1800 niveles posibles por brazo. Los ocho juegos oficiales de
desarrollo, tres repeticiones, comprueban retención B4. Ningún resultado gym
equivale a una puntuación oficial ARC-AGI.

Piloto: seis rondas de una propuesta, tres semillas emparejadas
697001/697017/697029, brazos ECHO y FIJO, 36 llamadas. ECHO elige tres casos
con su política de solicitudes; FIJO recibe los tres fallos con menos niveles
y una solicitud genérica constante. Ambos disponen de la misma gramática
aplicable al conjunto A de su programa actual y del mismo formato de evidencia.
El control auxiliar RANDOM toma seis propuestas por semilla, uniformemente
entre todos los parches legales de esa misma gramática, sin LLM. Tiene igual
presupuesto máximo de propuestas/verificación; se informa su coste real,
que no es igual al de inferencia. No sustituye a los cuatro brazos finales.
El piloto exige al menos una aceptación ECHO, mayor suma de niveles que FIJO,
al menos dos victorias de tres y ninguna derrota. RANDOM se informa aparte.

Campaña: treinta rondas, una propuesta por brazo y ronda, semilla 707001.
Empieza de SEMILLA, con historia vacía, y exige aceptación ECHO y victoria
estricta frente a FIJO. Total máximo 96 llamadas del modelo, más una
calibración sintética de transporte fuera de las mediciones científicas.
Las respuestas de ECHO se acumulan en SIN FILTRO en el orden emitido, solo
con validación de seguridad/formato y ejecución determinista, sin V3/V4.
No se eligen retrospectivamente propuestas para fabricar este control.
Treinta propuestas respetan el límite de 32 reglas.

V1 exige el DSL acotado. V2 exige ejecución y replay idénticos. V3 mantiene
la ganancia mínima de dos niveles A y ninguna pérdida individual de nivel
ni score (tolerancia 1e-10). V4 mantiene todos los niveles y scores individuales
B. Se repite A completo para cada candidato válido y B para cada candidato
que llega a V4. Los fallos del instrumento, caché, contexto, fuentes o replay
detienen el proceso conservando evidencias; no son resultados negativos del
agente. Las cachés reutilizan mediciones idénticas dentro de cada espacio;
las auditorías usan cachés separadas y reconstruyen solicitudes/veredictos.

Presupuesto máximo: 64.000 partidas reservadas entre ejecución, replays,
auditorías y examen. Cuatro procesos CPU, reserva mínima de disco 12 GiB.
Cada resultado se guarda con digest antes de borrar su diario detallado
efímero. Se conserva la trayectoria resumida y la telemetría de tiempo/RSS.
El visor utiliza el diario S6 existente para peticiones/respuestas/veredictos;
el ejecutor A utiliza su Recorder/Journal congelado para las observaciones.
B y examen no llevan observador. No se publican resultados en la web.

La secuencia automática es paridad de SEMILLA y del observador → piloto →
auditoría independiente → campaña → auditoría independiente → congelación
de cuatro políticas → examen. El piloto/campaña no elegible cierra B13 rojo
y deja la reserva sin abrir. El examen no se usa para cambiar el candidato.

Solo será S6 verde si B1–B5 pasan conjuntamente: ECHO ≥105 % de los niveles
SEMILLA y score medio no inferior; niveles ECHO > FIJO; niveles ECHO > SIN
FILTRO; retención de niveles y score oficiales de desarrollo; y auditoría
válida de fuentes, peticiones, ejecución, solver del gym y replays. Estos
criterios se importan sin modificación de `seed/s6_precise_exam.py`.
Un +5 en desarrollo no basta por sí solo para ese cierre. El resultado puede
ser negativo; no hay una duración garantizada hasta obtener el primer verde.
