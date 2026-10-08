# S6-B18 — búsqueda acotada de guardas con inferencia GPU

Condición privada nueva, 5 de octubre de 2026, posterior al cierre negativo
auditado de B17. El propietario solicita implementar el prototipo corregido,
ejecutarlo en Kaggle y comprobar si supera el juez. Los resultados B17 y sus
fuentes permanecen intactos. Este contrato se congela antes del primer juego
o propuesta científica B18. La calibración CUDA neutral es separada.

Se conserva Qwen3-4B-Instruct-2507 Q4_K_M, SHA256
`2fde00ce69dd4899c70d020845e2638353015bba0fdf161b3eb965f2bca4464e`, y el
commit llama.cpp `79e0b68c178656bb0632cb8602d2940b755077f8`. La inferencia
pasa de CPU a CUDA en una T4 de Kaggle; no se atribuirá una mejora de calidad
al hardware sin una comparación específica. Los dos brazos con LLM usan
el mismo backend, pesos, temperatura 0,6, top-k 40, top-p 0,95, contexto de
4096, límite de entrada 3072 y salida 160. No se contrata cómputo de pago.

El micro tiene tres brazos, como máximo ocho propuestas por brazo y las
mismas 80 partidas A, con 2000 acciones por partida. La base es el programa
aceptado B14 de 378 niveles. El paquete contiene únicamente ese programa,
su recibo aceptado y el digest de las trayectorias; no incluye los ganadores
PROBE, los fracasos B17 ni sus análisis. El diseño humano sí conoce esos
antecedentes y se declara dirigido. Esta condición es de desarrollo.

| Brazo | Mecanismo | Selección de guardas |
| --- | --- | --- |
| llm_selector | LLM, controlador B17 | El LLM escoge la propuesta en cada llamada |
| synth | Sin LLM | Orden determinista con evidencia de candidatos |
| hybrid | Primera propuesta del LLM | ECHO prueba el primer candidato legal del ranking actualizado |

La primera solicitud y respuesta del LLM se comparten entre llm_selector e
hybrid para fijar el mecanismo inicial. Cuenta como una oportunidad lógica
en ambos brazos y una llamada física. La semilla es 770101 + 1000 por ronda.
Después, hybrid ejecuta búsqueda finita en el núcleo. No se describirá como
un descubrimiento exclusivo del LLM una guarda calculada por el núcleo.
Cada brazo se detiene al primer pase V3 A; no se reutilizan sus oportunidades
restantes. Se informa de oportunidades, llamadas y partidas físicas por separado.

El ranking incorpora los consumos observados de los propios candidatos que
perdieron, incluidos estados ausentes de la base. Conserva los contraejemplos
del linaje y cuenta la frecuencia máxima por caso y vector observado para
evitar sobreponderar repeticiones. El orden sigue siendo cobertura de
ganancias, carga de lecturas en pérdidas, número de condiciones y orden
canónico. Los umbrales y el lenguaje permitido no cambian.

Para HOLD se descartan equivalencias certificables sobre las lecturas reales
de una trayectoria completa de un candidato propio con la misma base y valor.
La prueba se restringe al único sitio donde se consume HOLD: igualdad de
valores consumidos conserva la trayectoria por inducción bajo el entorno
determinista. Los contadores de activación del parche son telemetría. No se
aplica este criterio a otros controles, a bases diferentes ni a firmas de la
base solamente. Los tests incluyen un estado tardío que rompe una falsa
equivalencia, otras features/valores y evidencias incompletas o protegidas.

Cada propuesta ejecutable se mide en todas las partidas A y se repite por
completo. Pasa V3 A si gana al menos dos niveles y no pierde niveles ni score
en ninguna partida (tolerancia de score 1e-10). La instrumentación debe
reproducir exactamente las trayectorias base B14, digest
`4458a4c2e5f4d8ac6c46547fcbc62785e0aca93bd0bdecb6d23d7456d63c2d2c`.
Después, otro proceso y una caché nueva reconstruyen todas las solicitudes,
respuestas guardadas, ejecuciones y veredictos. No se remuestrea el LLM en
una auditoría. Una discrepancia detiene el instrumento; no cuenta como rojo
científico ni se oculta mediante un segundo intento.

Si hybrid pasa el micro y la auditoría, el juez mide la conservación del
primer candidato aceptable, congelado, en B nuevo: versiones 2 y 3, semillas
28020–28039, repetición 0 y 2000 acciones. Son 40 partidas protegidas sin
diario visible. Se evalúan base, hybrid y, si existe, el primer candidato de
synth. Se exige cero pérdidas individuales, replay completo y nueva ejecución
independiente. Ningún resultado B vuelve al generador ni sirve para escoger
otra guarda. El registro conserva tanto pases como rechazos.

Cuatro procesos de juegos, Python 3.12.13, numpy 2.3.2 y arcengine 0.9.3.
Los juegos siguen siendo CPU; la GPU acelera las propuestas. Presupuesto
máximo 6500 partidas físicas: hasta 4000 primarias A, 2000 de auditoría A y
360 para conservación y su auditoría, con margen para comprobaciones
declaradas. No se convierte ahorro de tokens en más propuestas. La caché
solo comparte ejecuciones idénticas dentro de la misma fase, con cargo lógico
por oportunidad. Fuente y manifiesto se verifican antes de cada medición.

Los diarios de A usan el canal observable existente. El resultado durable,
que conserva consumos, acciones y hashes, se escribe antes de eliminar el
diario efímero. Se conservan respuestas, comandos, tokens, stdout/stderr,
hashes y costes. El notebook y sus datos son privados.

Superar este juez acredita reparación autónoma acotada y conservación en
este banco. Permite diseñar el piloto principal con varios emparejamientos;
no demuestra todavía ventaja sobre FIJO, SEMILLA y SIN FILTRO en el examen.
El piloto, la campaña y B1–B5 siguen siendo necesarios. Este paquete no
contiene ni autoriza el examen reservado y nunca escribe `s6_green=true`.
El control sin LLM se mantiene aunque empate o supere al híbrido.
