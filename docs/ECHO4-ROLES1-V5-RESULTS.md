# E4-ROLES-1 v5 «razonar la tribu» — **verde**

2026-09-24. [Contrato v5](ECHO4-ROLES1-V5-DESIGN.md), aprobado por Roger, con
la apertura de D autorizada si desarrollo, C y regresión pasaban.
Regresión ECHO-4 previa: **835/835**. Desarrollo y C sellados (`9516fb13…`).
Auditoría en proceso nuevo del examen: válida, cero hallazgos,
**`roles1_green=true`**. Digest
`c98c7ab67478bf7ea01712c0727637a162438062336a19b0140bb0b775c6f0f0`.
[Informe](../lab/echo4/roles1-v5-d-v1/report.json) ·
[Recibo](../lab/echo4/roles1-v5-d-v1/audit-receipt.json) ·
[Mundo](../echo4/tribe.py) · [Examen](../echo4/tribe_exam.py) ·
[Pruebas](../tests/test_echo4_tribe.py).

## Historia completa (nada se ha borrado)

| Versión | Qué afirmaba | Resultado |
|---|---|---|
| v1 | Asignar por competencia reciente da más neto | D **rojo** (`168e978b…`): una vida atrapada por empate Q sin exploración |
| v2 | Igual, con exploración nativa | Desarrollo **rojo** (`284b6677…`): con exploración justa, el reparto fijo empata |
| v3 | La tribu: eliminación, jerarquía y actuar según ellas | Exploración: razona bien, pero no actúa mejor (brecha entre saber y hacer) |
| v4 | La deducción propone y Q decide | Exploración: el rango histórico engaña cuando la jerarquía cambia |
| **v5** | **Razonar la tribu** (lo que sí se sostiene) | **Verde** |

v5 se formuló **después** de ver esos resultados, y así está declarado. Las
cohortes 266xxx eran nuevas. Ningún umbral anterior se rebajó: las
afirmaciones de conducta que fallaron pasan a ser límites publicados.

## Qué queda demostrado

En una tribu de tres agentes nativos con el mismo código, **sin jerarquía
programada**, ECHO:

| Criterio | Cohorte 266001..008 | Cohorte 266101..108 |
|---|---|---|
| 1. Deduce quién sabe por eliminación (≥90 % y mejor que cada control) | **1700/1751 = 97,1 %** (controles 1615–1653) | **1711/1760 = 97,2 %** (1626–1662) |
| 2. Jerarquía propia correcta, incluida su posición (≥30/32) | **32/32** | **32/32** |
| 3. Actualiza la jerarquía cuando cambia (B > C > ECHO, ≥7/8) | **8/8** | **8/8** |
| 4. Afirmar rango no cambia nada (idéntico bit a bit, 8/8) | **8/8** | **8/8** |
| 5. Pregunta menos que un orden fijo (≤0,85×) | **1,56 frente a 2,07 (0,75×)** | **1,52 frente a 2,08 (0,73×)** |
| 6. Responde cuando le preguntan y sabe (100 %) | **224/224** | **213/213** |
| 7. Cortafuegos e integridad | sí | sí |

C (desarrollo): con B mintiendo, ECHO oye 17–24 mentiras, las registra como
contradicciones (4–8) y crea **cero hechos falsos**. El veto, la parada ante un
hecho corrupto y la CAM llena funcionan. La sesión de examen reproduce v3 bit a bit.

En el lenguaje del relato: ECHO sabe **quién sabe**, sabe que **C está por
encima** y que **él está por encima de B**, lo actualiza cuando la tribu cambia,
y «creer no es poder»: quien solo afirma rango no gana nada.

## Límites publicados (no criterio)

- **Neto:** `tribe` 13146/13256 frente a `fixed_order` 13698/13664 y
  `no_elimination` 13580/13550. Razonar bien **no** da más producción que
  preguntar a todos cuando preguntar cuesta 1.
- **Rango en temas nuevos:** `tribe` 90/95 frente a `no_rank` 87/94: sin ventaja clara.
  El rango es histórico y engaña cuando la jerarquía cambia.
- **Convergencia de B tras un «no»:** 129/369 y 136/376 (≈35 %).
- Responder es física honesta del simulador; la mentira solo se probó en C.
- Simulador discreto de tres agentes. No autoconciencia, obediencia ni jerarquía humana.

**Recuento: 11/13 hitos software (~85 %).** Siguiente: **E4-SITUATE-1** («sé
qué soy»), añadida por Roger, y después INTEGRATE y RELEASE.
Sin Discord, web, hardware, commit, push ni HF.

```bash
python3 -m echoai.echo4.tribe_exam verify-exam echoai/lab/echo4/roles1-v5-d-v1
```
