# E4-RELATION-1 — D verde; RELATION cerrada en su perfil

2026-09-24. Examen preregistrado en el [contrato C/D](ECHO4-RELATION1-CD-DESIGN.md),
abierto tras la aprobación de Roger para congelar y una regresión ECHO-4 de
790/790. Auditoría reconstructiva en proceso nuevo: válida, cero hallazgos,
**`relation1_green=true`** en el recibo. Digest
`42a6efc51d7bbbe413d104fdb099039cf02f5b670e2a8e6245fd8f2526c48345`.
Custodia de A (`ce24ccaa…`), desarrollo B (`ea6f55c2…`) y C (`ac7a1aab…`)
comprobada. [Informe](../lab/echo4/relation1-d-v1/report.json) ·
[Recibo](../lab/echo4/relation1-d-v1/audit-receipt.json) ·
[Código D](../echo4/relation_d.py).

## Pregunta y respuesta en este dominio

¿La historia de encuentros de la tarea A, guardada en la CAM propia, mejora
decisiones aprendidas en otra tarea (B, petición de ayuda) más allá de conocer
la identidad y predecir la conducta A de la contraparte? **Sí, en este perfil
discreto con reciprocidad diseñada.** El orden y la identidad son causales:
barajar la historia o mezclar identidades destruye gran parte de la ventaja.

## Cohortes nuevas (8 vidas cada una)

Neto B del aprendiz, 192 rondas por vida, suma de la cohorte:

| Brazo | 263001..008 | 263101..108 |
|---|---:|---:|
| **history** | **4920** | **4812** |
| other_only | 3556 | 3382 |
| shuffled | 3244 | 3260 |
| no_history | 1834 | 1572 |
| pooled | 1448 | 1478 |
| solo | 1536 | 1536 |
| always_ask | 1992 | 1812 |

| Criterio | Umbral | Cohorte 1 | Cohorte 2 |
|---|---|---|---|
| 1. Neto B frente a cada brazo aprendido y solo | ≥512 | peor: +1364 (other_only) | peor: +1430 (other_only) |
| 2. Ventaja greedy (96 rondas) frente a other_only / shuffled | ≥64 | +220 / +810 | +298 / +838 |
| 3. Neto B conjunto físico frente a cada aprendido | ≥256 | +950 (shuffled) | +904 (shuffled) |
| 4. Ninguna vida por debajo de solo | 0 vidas | 0 (mín. +390) | 0 (mín. +396) |
| 5. Paridad A e historia, orden inverso, replay B, invariantes | todas | sí | sí |

Por vida, frente a `other_only`: neto B +156..+212; greedy +12..+62.
**La ventaja estable sigue siendo pequeña.** La peor vida (+12) supera por
poco el umbral medio de 8. La mayor parte del margen de 192 rondas se debe a
un aprendizaje más eficiente de B (3 filas frente a 24), como en desarrollo.

## Publicado, no criterio

- Neto de la vida completa A+B del aprendiz: history 19014/18874, other_only
  17650/17444, solo en B 15630/15598. El neto A es idéntico entre brazos.
  La amortización frente a «actuar solo toda la vida» (el rojo de INTERACTION)
  **no se ha medido en estas cohortes**: haría falta el brazo solo de A con
  estas semillas. Queda abierta, no se afirma.
- Incentivo privado de las contrapartes (excluido de toda ganancia), history:
  5040/5008 y 6000/3760.
- 67 pruebas RELATION A/B/C dentro de la campaña, todas pasan.

## Límites que se conservan

- Reciprocidad **diseñada** y publicada; no emergente.
- C2: un impostor que imita la conducta A engaña 4 veces y además contamina la
  decisión con la contraparte fiable. La reputación no es garantía.
- C4: con recibos ausentes, el cubo del aprendiz baja y cuesta neto.
- Tarea discreta de un paso, dos contrapartes, simulador. No confianza sentida,
  amistad ni conciencia. Sin integración con MAINTAIN/CONTINUITY (INTEGRATE).

Recuento: **10/13 hitos software (~77 %)**, no porcentaje de esfuerzo.
Siguiente: **E4-ROLES-1** («la humanidad es una tribu, hay rangos»,
«creer no es poder, poder no es deber»). Después INTEGRATE y RELEASE.
Sin Discord, web, hardware, commit, push ni HF.

Desde `RXos`:

```bash
python3 -m echoai.echo4.relation_d verify echoai/lab/echo4/relation1-d-v1
```
