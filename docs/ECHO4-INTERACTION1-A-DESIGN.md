# E4-INTERACTION-1 — inicio oficial e INTERACTION-A

2026-09-22. Autorizado tras OTHER-1. Este contrato precede al banco A.
Las 99 fuentes y la evidencia sellada de OTHER permanecen intactas.

## Pregunta del conjunto y etapas

¿Aprende el agente cuándo y con quién coordinar acciones mejora un resultado
neto, usando observaciones e historia propias, sin leer la mente del otro?
Predecir bien al otro (OTHER) no demuestra todavía que resulte útil actuar
con él. Los beneficios y costes deben proceder del entorno, no de una
etiqueta de «buena interacción» escrita por el evaluador.

1. **INTERACTION-A, esta entrega:** física conjunta costeada, ejecución real
   por dos Agent originales, separación de memoria, veto/parada y contabilidad.
   Testigos mecánicos frente a una línea base Q nativa. No cierre conductual.
2. **INTERACTION-B, pendiente:** conectar historia/representación observable
   del otro a una decisión aprendida de coordinación; comparar con actuar
   solo, colaborar siempre, no distinguir contraparte y no usar su historia.
   Medir también cada utilidad individual, no solo la suma.
3. **INTERACTION-C, pendiente:** contraparte nueva, incumplimiento, ausencia,
   visibilidad parcial, coste elevado, agotamiento, conflicto y veto. Una
   intención/mensaje no prueba ejecución. Silencio no significa aceptación.
4. **INTERACTION-D, pendiente:** fijar fuentes, escenarios nuevos y umbrales
   cuantitativos antes de abrir examen; exigir ganancia neta por cohorte frente
   a controles y costes equivalentes, ausencia de hechos falsos y auditoría.

El umbral de ganancia de D se definirá con el dominio B, antes de sus exámenes;
no se adelanta un «verde» con la ganancia de guiones de A. RELATION conserva
historia compartida transferible y ROLES adaptación de competencia como fases
posteriores. Integración térmica, DREAM y continuidad conjunta: INTEGRATE.

## Física A: una tarea compartida, tres acciones

Dos individuos tienen presupuestos enteros finitos, sin recarga. Cada ronda
consume tiempo para ambos incluso si esperan. Acciones originales:

- `0 / UNIR`: intentar un trabajo conjunto; cuesta aunque el otro no participe.
- `1 / TEMER`: retirarse de la opción conjunta y realizar trabajo individual.
- `2 / OBSERVAR`: esperar, sin producción ni gasto de recurso.

Son affordances declaradas de este mundo discreto, no nuevas marchas ni una
afirmación sobre el significado universal de esos verbos.

| Contexto público | Coste UNIR por individuo | Producción conjunta por individuo | Trabajo individual: producción/coste |
|---|---:|---:|---:|
| 0, oportunidad | 3 | 10 | 5 / 1 |
| 1, fricción alta | 5 | 6 | 5 / 1 |
| 2, instalación bloqueada | 3 | 0 | 5 / 1 |

Solo hay producción conjunta si **ambos** ejecutan UNIR y pagan el coste.
Recompensa individual = producción propia − coste propio; utilidad conjunta
= suma. No crédito por propuestas, predicciones, intenciones ni llamadas al
córtex. Si no alcanza el presupuesto, no se cobra parcialmente ni se produce:
se registra el intento sin capacidad. Recursos nunca negativos, sin rescates.

Testigos de una ronda con presupuesto suficiente:
UNIR/UNIR obtiene neto 14, 2 y −6 en contextos 0, 1 y 2; solo/solo da 8.
UNIR frente a solo paga sin colaboración; esperar no acepta una oferta.
Estos números son leyes diseñadas, no habilidades descubiertas por el agente.

## Adaptación al núcleo sin otro bucle cognitivo

Se importan `Agent.turn`, CAM/T/Q, gate y `OtherModel` sin editarlos.
Dos puertos físicos pertenecen al mismo mundo; las memorias son privadas.
Se congelan ambas observaciones antes de actuar. El primer `env.step` recoge
su acción ya vetada y deja ejecutar el `Agent.turn` del otro; el segundo
`env.step` resuelve atómicamente las dos acciones. Ambos reciben después su
propia recompensa y sucesor, **una sola actualización Q/T por turno**.
Anidación acotada a dos agentes; sin hilos, servidor ni barreras bloqueantes.
Invertir el orden de ejecución debe producir la misma traza indexada por actor.
No se comparte Q ni se entrega al segundo la propuesta o acción aún pendiente
del primero. Un fallo parcial bloquea continuar; no se promete rollback.

Observación nativa: celda/contexto con encoder original. Observación del otro:
paquetes canónicos WSP16 del módulo OTHER, con predicción anterior a resultados
y aprendizaje posterior. No nuevo bus, layout o tabla predictiva paralela.
En A esa predicción se registra **pero aún no modifica la política**; Q empieza
a cero y usa la recompensa física conjunta. No se llaman «políticas sociales
aprendidas» a los guiones del banco.
La línea base A es simétrica: ambas Q empiezan igual y ven el mismo contexto.
Coincidir en acciones no acredita negociación ni utilización de OTHER. El
sensor A no expone el presupuesto restante: las insuficiencias se registran
como límites, no se ocultan ni se atribuye autorregulación ya implementada.

A no modela conversación, negociación o mensajes de oferta: UNIR es una acción
física concurrente. No tiene coste de comunicación porque no hay tal canal.
Si B necesita mensajes, deberá añadir costes, procedencia y comprobación de
ejecución en su propio contrato, sin usar prosa como prueba.

## Banco A y requisitos

1. Censo de 3 contextos × 9 pares de acciones × 9 pares de recursos (0, 2, 8):
   243 transiciones. Cálculo independiente de contabilidad y simetría por actor.
2. Testigos de 12 rondas: colaborar siempre, actuar solo y esperar; publicar
   ganancias y pérdidas en los tres contextos, identificados como guiones.
3. Línea base nativa: semillas de desarrollo 17, 31, 59; 144 rondas, presupuesto
   inicial 256 por actor. Publicar primeras/últimas 72, costes, intentos sin
   capacidad y utilidad por individuo; guiones emparejados de colaborar siempre,
   actuar solo y esperar en las mismas secuencias. No umbral de ganancia autónoma en A.
4. Comparar orden directo/inverso y reconstruir observación pública de OTHER
   sin ejecutar el mundo. Pruebas de veto, parada, límites y entradas inválidas.
5. Congelar fuentes antes de campaña A; reconstrucción íntegra en proceso nuevo
   con los mismos resultados y custodia de OTHER. No se reejecuta su examen.

Máximo 512 rondas, secuencias acotadas, tipos enteros estrictos. Córtex apagado,
sin borrados de CAM ni modificación de fuentes selladas. A válida no concede
`interaction1_green`: ese campo queda **false**, también en el recibo.
Esto no acredita conciencia, empatía, cooperación emergente ni agente integrado.
No Discord, hardware, web o Hugging Face en este incremento. METAVERSE-1 último.
