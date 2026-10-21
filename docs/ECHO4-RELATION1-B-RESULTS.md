# E4-RELATION-1 — RELATION-B implementada, desarrollo verde (no examen)

2026-09-23. [Contrato B](ECHO4-RELATION1-B-DESIGN.md), aprobado antes
de implementar. Auditoría de reconstrucción en proceso nuevo válida, cero
hallazgos. Digest `ea6f55c28a58582df934e259367bc6fa88ecbe256f1fc196e49da737e780239f`.
**`relation1_green=false`**: B es desarrollo; D (cohortes nuevas) sigue sin abrir.
RELATION-A intacta (`ce24ccaa…`, reverificada).

[Informe](../lab/echo4/relation1-b-dev-v1/report.json) ·
[Recibo](../lab/echo4/relation1-b-dev-v1/audit-receipt.json) ·
[Código](../echo4/relation_help.py) · [Banco](../echo4/relation_b_bench.py) ·
[Pruebas](../tests/test_echo4_relation1b.py).

## Qué se mide

Tarea B «petición de ayuda» (La fuga, 17:13: «necesito su ayuda pero no puedo
moverme»). La historia de encuentros A, guardada en la CAM propia del aprendiz,
indexa una fila WSP16 derivada (sin hecho, sin extract) que la Q original usa
en B. Las contrapartes tienen un perfil de reciprocidad **diseñado**: su
incentivo privado ±16 depende de sus tres últimos episodios A con el aprendiz,
leídos de **su** memoria. Ese incentivo se publica aparte y no cuenta como ganancia.

480 encuentros por vida: 288 solo A (formación heredada de INTERACTION) y 192 B+A.
En B, 96 encuentros con la exploración nativa por evidencia y 96 greedy.

## Resultado de desarrollo (semillas 151 / 163 / 179)

Neto B del aprendiz, 192 encuentros:

| Brazo | 151 | 163 | 179 |
|---|---:|---:|---:|
| **history** | **606** | **600** | **630** |
| other_only (identidad + OTHER) | 432 | 442 | 492 |
| shuffled (orden eliminado) | 426 | 426 | 450 |
| pooled (identidades agrupadas) | 184 | 182 | 172 |
| no_history | 184 | 168 | 178 |
| solo (fijo) | 192 | 192 | 192 |
| always_ask (fijo) | 234 | 224 | 274 |

Solo las 96 rondas greedy: history 342/336/354 frente a other_only 314/304/334
y shuffled 248/236/260. **La ventaja estable frente a identidad sola es pequeña:
+28/+32/+20 por vida.** La mayor parte del margen de 192 rondas (+174/+158/+138)
se obtiene en el aprendizaje de B: `history` tiene 3 filas y `other_only`, 24.
No se oculta: parte de la ventaja es de eficiencia de aprendizaje, no solo de
información. El sondeo previo al contrato estimaba ≈56 unidades por vida.

Neto B conjunto físico: history 387/384/399 frente a 252–297 del mejor control
aprendido; always_ask −9/−16/+19.

El orden importa: `shuffled` usa exactamente los mismos episodios y pierde
170–180 por vida. La identidad importa: `pooled` queda en el nivel de `no_history`.

Incentivo privado excluido, contraparte fiable/no fiable (history):
1168/64, 1152/64, 64/1232. Neto A idéntico en todos los brazos:
1793/1744/1771 para el aprendiz.

## Verificación

- Criterio de desarrollo cumplido en las 3 vidas: `history` supera a `other_only`,
  `shuffled`, `pooled`, `no_history` y `solo`.
- Paridad A entre los 7 brazos: acciones, costes, producción, recibos,
  predicciones y gates idénticos. Solo cambian los niveles de recursos,
  porque B gasta de los mismos libros; esos campos se excluyen del digest de paridad.
- Paridad de historia: digests RelationMemory idénticos entre brazos (B no escribe episodios).
- Orden inverso de ejecución A: trazas A y B idénticas.
- Replay B desde recibos propios: niveles, filas y liquidaciones reconstruidos (21/21 vidas-brazo).
- 23 pruebas nuevas; 148 heredadas (RELATION-A, INTERACTION A/BCD, OTHER) pasan.
- Cero hechos falsos, borrados y llamadas LLM; filas B sin hecho ni extract.

## Detalles de implementación no escritos en el contrato

- Acciones 1 y 2 de la contraparte significan «no ayudar».
- Pedir exige presupuesto ≥3 (peor coste posible); si no, es incapaz, sin coste.
- Contraparte vetada: su gate real bloquea (INHIBIT en su fila B) y responde esperar.
- Una segunda llamada B en el mismo encuentro se rechaza antes de ejecutar; no marca fallo.
- Hubo ejecuciones exploratorias del banco durante la implementación, antes de fijar
  fuentes. No son evidencia; la campaña sellada es la única que cuenta.

## Límites

Perfil de reciprocidad diseñado, no emergente. La contraparte y el aprendiz leen
la misma historia simétrica en el caso nominal; observaciones divergentes son
material de C. Tarea discreta de un paso. No acredita confianza, amistad,
conciencia ni transferencia a tareas no probadas.

## Siguiente: RELATION-C y D

C: ruptura y reencuentro, «VOLVÍ AL CUERPO DE K» (misma identidad, otra conducta),
historia incompleta o contradictoria, identidad nueva. D: cohortes nuevas con
márgenes fijados antes. Propuesta de margen a decidir en el contrato C/D.

Desde `RXos`:

```bash
python3 -m unittest echoai.tests.test_echo4_relation1b
python3 -m echoai.echo4.relation_b_bench verify echoai/lab/echo4/relation1-b-dev-v1
```
