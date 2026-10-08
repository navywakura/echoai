# E4-INTERACTION-1 — primer incremento A y siguientes pasos

2026-09-22. **Inicio oficial; INTERACTION-A implementada y verificada.**
El entorno conjunto y su conexión al núcleo son válidos; la fase completa
sigue abierta: `interaction1_green=false`, también en el recibo del auditor.

Reconstrucción íntegra en proceso nuevo válida, sin hallazgos; `phase_a_valid=true`.
104 fuentes fijadas, incluidas las 99 de OTHER sin cambios. Digest:
`da8cc00befb52ac1abc9942bae1aa8eacf3fbe2049501dfebd26c2a1ed57c1c3`.
[Informe](../lab/echo4/interaction1-a-v1/report.json) ·
[Recibo](../lab/echo4/interaction1-a-v1/audit-receipt.json).

## Implementación y pregunta

OTHER acreditó predicción observable, no beneficio de coordinarse. INTERACTION
pregunta cuándo y con quién actuar conjuntamente mejora el resultado neto.
Esta primera entrega implementa el experimento donde se podrá medirlo:

- `interaction_world.py`: tarea conjunta, producción y costes enteros,
  presupuesto finito, insuficiencia, espera y parada, sin recargas.
- `interaction_session.py`: dos `Agent.turn` originales, memorias privadas,
  acciones confirmadas por el gate antes de resolver el resultado conjunto.
- `interaction_bench.py`: censo, testigos mecánicos, Q nativa sin guion,
  controles emparejados, fuentes fijadas y reconstrucción.

No se duplica el bucle cognitivo. El primer paso de entorno deja ejecutarse
al segundo Agent; al confirmar ambas acciones se resuelve una sola ronda.
Cada Q recibe exactamente una recompensa propia y una actualización por turno.
El orden inverso reproduce la misma traza. Una interrupción parcial bloquea
continuar, sin afirmar que se hayan revertido memorias.

Se reutiliza OTHER en la misma CAM/T de cada individuo. Las predicciones se
comprometen antes de ejecutar; las acciones se observan después. **En A aún
no se usan esas predicciones para decidir.** Las Q empiezan a cero, ven el
mismo contexto y pueden coincidir por simetría: no es negociación emergente.
No hay mensajes de oferta o prosa; UNIR es una acción física del simulador.

## Resultados

**243/243 transiciones** concuerdan con el cálculo independiente de recursos,
producción y utilidad; su intercambio de actores también coincide. Nueve
testigos de doce rondas conservan que colaborar a ciegas no siempre conviene.

| Contexto | Neto conjunto: colaborar siempre | Neto conjunto: actuar solo |
|---|---:|---:|
| Oportunidad | 168 | 96 |
| Fricción alta | 24 | 96 |
| Instalación bloqueada | −72 | 96 |

Son **guiones mecánicos**, no agentes que hayan descubierto la estrategia.
Intentar colaborar sin la acción del otro consume recursos sin producir un
beneficio conjunto. Un veto convierte la acción ejecutada en WAIT; la
propuesta de colaborar no genera producción. Sin presupuesto suficiente no
hay aportación parcial ni crédito ficticio.

Tres líneas base nativas: 144 rondas por semilla, primeras 72 exploratorias y
últimas 72 greedy; Q sigue aprendiendo. Presupuesto inicial 256 por individuo,
mismas secuencias y presupuesto para los controles guionizados.

| Semilla | Neto de cada agente nativo | Siempre solo, cada uno | Siempre colaborar, cada uno | Recurso restante nativo |
|---|---:|---:|---:|---:|
| 17 | 485 | 576 | 88 | 76 |
| 31 | 690 | 576 | 203 | 5 |
| 59 | 668 | 576 | 100 | 8 |

Ambos agentes obtienen iguales resultados en este perfil simétrico, sin
compartir memoria. Neto conjunto nativo 3686 frente a 3456 del control solo;
**pierde en la semilla 17**. La suma favorable no prueba ganancia robusta ni
beneficio de OTHER: todavía no interviene en la selección. No se cambia la
semilla ni se declara un cierre por ese agregado.

Costes nativos, sumando ambos individuos en las tres secuencias: 1358 unidades
gastadas, 5044 producidas y cero intentos sin capacidad. El control de
colaborar siempre tiene 434 intentos individuales sin capacidad. El sensor
de A no expone el presupuesto restante, una limitación para B.

El banco ejecuta 432 rondas nativas (864 `Agent.turn`) más otras 432 al
invertir el orden. Añade 243 transiciones del censo y 243 simétricas, 108 rondas
de testigos y 1296 rondas de controles guionizados emparejados. No contar esas
acciones guionizadas como aprendizaje autónomo. La auditoría repite la misma
evidencia, no constituye otro examen ni un holdout nuevo.

## Verificación y límites

**35 pruebas nuevas; 108 con regresiones seleccionadas, todas aprobadas.**
Incluyen Q inicialmente cero, una actualización tras ambas ejecuciones,
independencia de memorias, paridad al invertir el orden, doble recibo,
presupuesto, parada entre ejecuciones, veto, ausencia de observación, replay
público sin ejecutar física y rechazo de un artefacto alterado.
Las regresiones abarcan OTHER, Q y clases de T/inverso/encoder/gate del núcleo;
no se afirma haber repetido toda la suite histórica de ECHO-4.

El replay público reconstruye solo el observador OTHER. La auditoría nativa
reconstruye INTERACTION-A completa y coteja custodia de OTHER; no repite su
examen ni reabre MAINTAIN, DREAM o CONT. WSP16, CAM/T/Q/gate originales,
córtex apagado y CAM sin borrados. No prueba de aislamiento ante código host
malicioso, continuidad conjunta, cuerpo térmico o conciencia subjetiva.

## Siguiente: INTERACTION-B

Conectar representación observable de la contraparte a decisiones aprendidas,
sin convertir predicciones en hechos. Contrastar cuándo y con quién colaborar,
con contraparte diferenciada y costes/recursos observables legítimamente.
Controles: actuar solo, colaborar siempre, quitar identidad y quitar historia;
publicar beneficios y pérdidas individuales. C cubrirá fallos y D necesitará
un contrato cuantitativo congelado y exámenes nuevos. Nada de eso está cerrado
por la integridad de A. RELATION, ROLES, INTEGRATE y RELEASE siguen después.

## Reproducción

Desde `echoai/`, con Python del sistema, sin LLM:

```bash
PYTHONPATH=.. python3 -m unittest tests.test_echo4_interaction1a -q
PYTHONPATH=.. python3 -m echoai.echo4.interaction_bench verify lab/echo4/interaction1-a-v1
```

`campaign` requiere un directorio inexistente; no sobrescribir evidencias.
No Discord, hardware, web, commit/push o publicación HF en esta entrega.
[Contrato y etapas](ECHO4-INTERACTION1-A-DESIGN.md) · [Roadmap](ROADMAP.md).
