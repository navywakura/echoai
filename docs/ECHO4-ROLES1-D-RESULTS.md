# E4-ROLES-1 — D v1 **rojo**

2026-09-24. Examen preregistrado en el [contrato C/D](ECHO4-ROLES1-CD-DESIGN.md),
abierto con la aprobación de Roger tras una regresión ECHO-4 de 815/815.
Auditoría en proceso nuevo válida, cero hallazgos: **`criteria_passed=false`,
`roles1_green=false`**. Digest
`168e978b6c160b321c1a244d878c8971ffdbf1bb239b43cca9af20c572119462`.
[Informe](../lab/echo4/roles1-d-v1/report.json) ·
[Recibo](../lab/echo4/roles1-d-v1/audit-receipt.json).

## Resultado

| Criterio | Cohorte 264001..008 | Cohorte 264101..108 |
|---|---|---|
| 1. Neto ≥256/vida frente a cada brazo | sí (18015 frente a 11279) | sí (16836 frente a 10913) |
| 2. Recuperación ≤96/vida y < cumulative | sí (207 frente a 2115) | sí (477 frente a 2241) |
| 3. Último régimen ≥72/96 por vida | sí (742/768) | sí (677/768) |
| 4. **Ninguna vida por debajo de `static_role`** | sí | **no: semilla 264106, 908 frente a 1390** |
| 5. Integridad | sí | sí |

15 de 16 vidas: `competence` 2046–2380 frente a `static_role` 1024–1835, con
recuperación de 3–34 rondas tras cada deriva. La semilla 264106 se queda en
unos 32 aciertos por régimen desde el segundo (57/31/32) y no recupera nunca.

## Causa (diagnóstico posterior, sin tocar lo sellado)

Trampa de aprendizaje en la fila «la contraparte 1 falló en este tipo»:

- Q de esa fila = [−1, −1, −2]. Asignar otra vez a la contraparte 1 y asignar
  a la contraparte 2 empatan: el −1 de la segunda viene de un intento temprano fallido.
- El desempate elige la primera acción, así que el agente vuelve a asignar
  a quien acaba de fallar. Falla, cobra −1, su Q no cambia y la fila tampoco: **149 veces**.
- Con `evidence_greedy`, el agente nativo deja de explorar cuando agota el
  presupuesto de evidencia: 0 exploraciones tras el primer régimen. Nada rompe el ciclo.

No es mala suerte del umbral: es un defecto del diseño del tratamiento con el
agente nativo tal como está configurado. El criterio 4 existía precisamente
para detectar vidas así.

## Qué se conserva

El rojo queda publicado. Las fuentes, cohortes y evidencias de v1 no se
modifican. Esas cohortes ya no pueden servir como examen de una v2.
C (`ba7225c4…`) y el desarrollo A/B (`36b9cab3…`) siguen válidos en su ámbito.
ROLES-1 **no** está cerrada: siguen siendo 10/13 hitos software.

Una v2 debe corregir la causa en su origen (exploración o representación),
con desarrollo nuevo y cohortes nuevas, sin rebajar ningún umbral.

## v2 (2026-09-24): exploración periódica nativa — desarrollo **rojo**

[Contrato v2](ECHO4-ROLES1-V2-DESIGN.md). Único cambio: `evidence_greedy=False`
en el aprendiz de todos los brazos. Desarrollo sellado y auditado, válido:
`284b667751c9922fd70af260c5576a109f5e9391e7153acbd7f079dfa46a531c`,
`criteria_passed=false`. D v2 **no se abrió**.

| Semilla | competence | static_role | cumulative | Recuperación competence / static |
|---|---:|---:|---:|---|
| 311 | 2022 | **2028** | 1711 | 21 / 84 |
| 323 | 1753 | **1818** | 1522 | 30 / 130 |
| 347 | 1911 | 1678 | 1232 | 43 / 178 |

- La trampa de v1 desaparece: la semilla 264106 recupera (prueba de regresión).
- Pero la exploración periódica también deja que `static_role` se reajuste tras
  cada deriva. Por eso **gran parte de la ventaja de neto de v1 se debía a que
  los controles no podían explorar**.
- `competence` sigue **recuperando 3–5 veces más rápido** tras un cambio de
  competencia, pero paga la exploración y el primer régimen, y empata o pierde en neto.
- Los 9 testigos C pasan con v2; C0 confirma que el único cambio es la exploración.

Lectura honesta: en este mundo, seguir la competencia reciente acelera la
reasignación de roles, pero no da más neto que un reparto fijo que también
explora. ROLES-1 sigue **abierta y sin verde**. No se rebaja ningún umbral.
