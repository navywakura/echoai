# S6-B14 — memoria de experimentos, selección y diversidad verificable

Condición privada del 4 de octubre de 2026, posterior al piloto B13-R1. El
propietario pidió corregir los defectos identificados y mantener su auditoría
en marcha. B14 se prepara en un directorio distinto y espera al cierre válido
de esa auditoría antes de medir. Las fuentes, propuestas y resultados B13
permanecen intactos. Este documento se congela junto con el candidato antes
del primer juego B14; el resultado puede volver a ser negativo.

La pregunta es si el controlador de experimentos de ECHO, después de reparar
la pérdida de feedback, la selección sin señal y la repetición de fallos
equivalentes, supera a una petición genérica con los mismos recursos. B13 dio
1113 frente a 1125 de FIJO; esa observación orientó el diseño y no es evidencia
independiente de estas correcciones. Los parches ganadores anteriores no se
insertan en peticiones ni políticas. Todos los brazos comienzan con SEMILLA
vacía e historia vacía. No se modifica el ejecutor de juegos ni el verificador
para conceder una puntuación mejor.

`echo_arc/repair_memory.py` es el nuevo controlador de memoria y selección de
experimentos. Sus recibos son resultados observados. No constituyen un diario
de pensamientos ocultos ni entran en el bus de NEXUS-0. El núcleo NEXUS-0
continúa sin LLM. El modelo propone parches al componente de investigación;
los filtros conservan la autoridad de aceptar o rechazar.

**Memoria entregada al modelo.** Cada variante de contexto contiene el último
intento, con propuesta, veredicto, ganancia, número de pérdidas en A, indicador
booleano de rechazo protegido y equivalencias observadas. No existe una
variante que suprima ese recibo cuando hay historia. Si se refina, coexisten
el objetivo original y el último intento sobre ese objetivo. La política
aceptada se conserva completa en una codificación reversible por índices de
control, feature y operador, cuya leyenda aparece en todas las peticiones.

La reducción ocurre en este orden: tres antecedentes anteriores al último,
dos contrastes y dos oportunidades por control/caso; después un antecedente
y una oportunidad; después ningún antecedente opcional y un contraste; por
último se conservan los recibos obligatorios y resúmenes de casos, omitiendo
los contrastes y las oportunidades detalladas. Las omisiones son explícitas,
no un corte de texto. Se tokeniza cada variante con el GGUF y se elige la
primera que cabe en 3072 tokens. Si ninguna cabe, se detiene el instrumento.
FIJO recibe la misma reparación del formato y el mismo límite de contexto.

**Selección y aprendizaje de intentos.** El controlador mantiene separados el
registro completo de intentos y la caducidad de objetivos. CONTRADICTION exige
contradicciones registradas; WAIT exige consumo de HOLD o espera pendiente;
GENERALIZE exige oportunidades de algún control en desarrollo. Los mecanismos
disponibles sin probar reciben una llamada antes de seguir explotando otro.
Las reparaciones descendientes cuentan como intentos del mecanismo del objetivo
raíz; los rechazos con ganancia positiva no desaparecen de la contabilidad.

Después de esa exploración, un objetivo útil rechazado puede ocupar hasta tres
refinamientos en la misma base. Cambiar la base invalida sus objetivos. Los
descendientes de un objetivo agotado no reinician por sí solos otros tres
intentos. Sin objetivo disponible, se prioriza
`(ganancia_aceptada + 2) / (intentos + repeticiones + 1)`.
El término de repeticiones usa digests de comportamiento medidos, no una
opinión del LLM. Se conservan todos los intentos, incluidos sus costes reales.

Cuando dos variantes de un mismo control/valor, en la misma base, producen
el mismo comportamiento rechazado, esa combinación descansa durante la
siguiente propuesta. La pausa se aplica por igual a los tres brazos y no
vacía la gramática si no queda ninguna alternativa. También interrumpe una
serie de refinamiento que acaba de repetir el fallo. Es una heurística de
diversidad, no una demostración de que todas sus guardas fracasen; podría
aplazar una reparación válida. El recibo expone esa pausa al modelo.

La selección ordena casos con señal por niveles resueltos, intensidad de la
señal e índice estable. La rotación ocurre únicamente dentro de ese conjunto.
Se muestran hasta tres casos; si hay menos, no se rellenan con casos sin
relación con el foco. GENERALIZE puede consultar casos resueltos y fallidos;
REFINE conserva contrastes del objetivo. FIJO mantiene su instrucción genérica
y la selección por menor número de niveles, con el nuevo recibo obligatorio.
Ambos brazos tienen acceso a la misma gramática sobre A de su base actual.

**Exclusión conservadora de repeticiones.** Una firma calculada solo sobre las
oportunidades de la base no prueba equivalencia de candidatos; PROBE2 ya
mostró esa limitación. B14 utiliza, exclusivamente para un rechazo V3, todas
las decisiones de las 80 partidas A del candidato que acaba de ejecutarse.
El certificado registra sus features, identidad de casos, base, candidato,
cuenta de decisiones y hash de la gramática. Las features se agrupan en
intervalos que preservan exactamente el valor de verdad de todos los átomos
legales `eq/ge/le`; no se selecciona un subconjunto de decisiones.

Se excluye una alternativa únicamente si parte de la misma base, modifica
el mismo control al mismo valor y su guarda coincide con la guarda del
candidato fallido en cada decisión certificada. Bajo el ejecutor determinista
congelado, los dos programas producen los mismos controles en cada paso de
esas ejecuciones; por inducción reproducen ese fallo V3. El certificado se
reconstruye al auditar. Una discrepancia de origen, integridad, base o casos
detiene la condición. No se declara equivalencia fuera de esas ejecuciones.

Los rechazos V4 quedan fuera de esta exclusión por equivalencia de A: una
alternativa puede conservar el beneficio en A y cambiar su comportamiento
protegido. Las repeticiones textuales exactas siguen excluidas por la gramática
anterior. La prueba conservadora puede dejar pasar programas de comportamiento
idéntico que no tienen controles idénticos en cada paso. Esos programas se
miden normalmente y su equivalencia alimenta el recibo y el planificador.
No se promete eliminar toda redundancia sin ejecutar candidatos.

La regresión con cinco pares de programas de B13 que tuvieron igual
comportamiento mostró que ninguno permite esta exclusión conservadora:
sus controles sí difieren en algunas decisiones. Se conserva ese resultado
negativo. La pausa de diversidad atiende estos casos después de observar
la repetición, sin atribuirle una prueba semántica que no existe.

**Modelo y recursos.** Se conserva Qwen3-4B-Instruct-2507 Q4_K_M local, SHA-256
`2fde00ce69dd4899c70d020845e2638353015bba0fdf161b3eb965f2bca4464e`, y el runtime
CPU nativo b5904 registrado por B13-R1. Temperatura 0,6, top-k 40, top-p 0,95,
cuatro hilos, contexto 4096, entrada 3072, salida 160 tokens, guardia 1800 s.
Los pesos, las primitivas y los requisitos no cambian. No hay APIs ni gasto
de GPU. La preparación usa únicamente el tokenizador y datos ya existentes;
sus controles no cuentan como aciertos del agente ni llamadas de generación.

A conserva las 80 partidas de desarrollo gym v2/v3, semillas 0–39, repetición
0 y 2000 decisiones. Es desarrollo conocido. B es nuevo: semillas 27420–27439,
v2/v3, 40 partidas de 2000 decisiones. Sus detalles no llegan al controlador
ni al modelo. La reserva también es nueva: semillas 27500–27559, v2/v3 y tres
repeticiones, 360 partidas y 1800 niveles posibles por brazo. No se ejecuta
ni inspecciona la reserva durante la preparación o la búsqueda.

Piloto: seis rondas, una propuesta por brazo/ronda, tres semillas emparejadas
698001, 698017 y 698029. Son 36 llamadas de ECHO/FIJO y 18 propuestas RANDOM,
uniformes sobre la gramática legal restante de su propia historia. El piloto
requiere al menos una aceptación ECHO, más niveles agregados que FIJO, al
menos dos victorias y ninguna derrota entre los tres pares. RANDOM es un
control auxiliar informado, no reemplaza los cuatro brazos del examen.

Campaña: treinta rondas desde SEMILLA, historia vacía y semilla 708001, 60
llamadas. SIN FILTRO acumula las propuestas ECHO en orden tras seguridad y
ejecución/replay, omitiendo V3/V4. El total del experimento conserva el máximo
de 96 llamadas, 64.000 partidas programadas y cuatro workers. Toda propuesta
válida se mide y repite en A; las que pasan V3 se miden y repiten en B.
La gramática se vuelve a construir en cada auditoría a partir de sus propias
trayectorias y recibos. No se reutiliza la caché primaria como auditoría.

Las puertas se conservan: V3 pide al menos +2 niveles y ninguna pérdida
individual de niveles o score A; V4 exige retención individual B, con
tolerancia de score 1e-10. B1 requiere ECHO ≥105 % de SEMILLA en niveles y
score medio no inferior; B2, ECHO > FIJO; B3, ECHO > SIN FILTRO; B4, retención
en los ocho juegos oficiales de desarrollo, tres repeticiones; B5, auditorías,
procedencia, solver y replays válidos. Los criterios se importan del código
congelado anterior. Los resultados gym no se presentan como puntuaciones ARC.

El lanzador reutiliza las funciones científicas B13 y configura explícitamente
rutas, workers y subprocesos para B14. El proxy de subprocess incluye `STDOUT`.
Una prueba recorre el paso completo desde un piloto negativo guardado hasta
el lanzamiento de su auditoría y el cierre, sin ejecutar campaña ni examen.
Se comprueban también la memoria obligatoria, los límites reales de contexto
con 36 historiales, seis refinamientos forzados como regresión del instrumento,
una política de 32 reglas, el límite entre equivalencia de base y de candidato,
la separación de particiones y la integridad de los archivos anteriores.

El servicio en espera arranca solo tras `pilot-audit.json` válido y el cierre
`PILOT_NO_PROMOTION` de B13-R1. Antes de eso no juega, no llama al modelo y no
compite con la auditoría por workers. Después encadena preflight, piloto,
auditoría, campaña, auditoría y examen, condicionado a elegibilidad. Los fallos
de instrumento se detienen conservando evidencias. Las decisiones de desarrollo
se muestran con el observador existente; B y reserva permanecen sin observador.
La documentación y los recibos quedan privados.
