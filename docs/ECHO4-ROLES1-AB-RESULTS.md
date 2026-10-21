# E4-ROLES-1 — A/B implementadas, desarrollo verde (no examen)

2026-09-24. [Contrato A/B con enmienda 1](ECHO4-ROLES1-AB-DESIGN.md), aprobado
por Nav. Auditoría en proceso nuevo válida, cero hallazgos. Digest
`36b9cab337eb10dfab37557f2a4a42d12a08e08dbdf65d2642652b9523c257a6`.
`roles1_green=false`: C/D sin abrir. Custodia de RELATION-D (`42a6efc5…`) comprobada.

[Informe](../lab/echo4/roles1-ab-dev-v2/report.json) · [Código](../echo4/roles.py) ·
[Banco](../echo4/roles_bench.py) · [Pruebas](../tests/test_echo4_roles1.py).

`lab/echo4/roles1-ab-dev-v1` se conserva sin tocar: su auditoría falló porque
el informe llevaba medias en coma flotante, que el lector del laboratorio
rechaza. Los resultados eran los mismos. v2 usa totales enteros.

## Qué se mide

Tres tipos de tarea. En cada tipo hay un único competente (una de las dos
contrapartes o el propio aprendiz). La competencia cambia cada 96 rondas sin
aviso. El aprendiz decide quién ejecuta, usando solo sus propios recibos
factuales. La contraparte 2 afirma «rango alto» en cada ronda: se guarda como
hipótesis con procedencia, sin hecho, y nunca entra en la fila de competencia.

**Enmienda 1**, hecha antes de sellar pero después de ver ejecuciones
exploratorias: la fila del tratamiento es «el último intento ejecutado en ese
tipo: quién y si produjo», sin el tipo. La definición original no podía
representar un fallo y se atascaba (939 frente a 1121). Queda registrado.

## Resultado de desarrollo (semillas 211 / 223 / 241, 384 rondas)

| Brazo | Neto aprendiz | Aciertos por régimen (de 96) | Recuperación total* |
|---|---|---|---|
| **competence** | **2200 / 2186 / 2207** | 32·84·91·93 / 32·86·90·93 / 37·87·94·84 | 49 / 32 / 57 |
| cumulative | 1085 / 1024 / 1483 | 68·51·21·32 / … | 288 / 288 / 224 |
| static_role | 1121 / 1024 / 1501 | 72·51·21·32 / … | 288 / 288 / 224 |
| claimed_rank | 1121 / 1024 / 1501 | idéntico a static_role | 288 / 288 / 224 |
| rank_follow (fijo) | 768 | 32 en todos | 288 |
| self_only (fijo) | 384 | 32 en todos | 288 |

\* Suma, en las tres derivas, de las rondas hasta encadenar 6 aciertos (tope 96 por deriva).

- **Tras cada cambio de competencia**, `competence` recupera en 3–38 rondas.
  Los controles aprendidos casi nunca recuperan dentro del régimen.
- **Coste inicial publicado:** en el primer régimen `competence` rinde peor
  (32–37 frente a 68–72), mientras aprende la regla. La ventaja aparece a partir
  de la primera deriva.
- **«Creer no es poder»:** con la afirmación de rango en la fila,
  `claimed_rank` da exactamente lo mismo que `static_role`. La afirmación no
  añade información. Seguir el rango (`rank_follow`) da 768 y neto conjunto 0.
- Incentivo privado de aceptar (excluido): competence 2224/2064, 1968/1952, 2096/2016.

## Verificación

- 18 pruebas nuevas; replay de filas y liquidaciones desde los recibos en las 18
  vidas-brazo; deriva real (≥2 tipos cambian); determinismo; invariantes; cero
  hechos falsos, borrados y llamadas LLM; afirmaciones de rango nunca hechos.
- Límite declarado: la validación de recibos es estructural. Un recibo falsificado
  que sea canónico y físicamente posible (producción 9 → 0) **no se detecta**.
  No hay autenticación criptográfica, igual que en RELATION.

## Límites

Tres tipos, un competente por tipo, deriva declarada y periódica. Contrapartes
entrenadas para aceptar siempre (no se negaron en el banco). Coordinador fijo.
No liderazgo, jerarquía emergente, obediencia ni conciencia.

Siguiente: contrato C/D de ROLES.
