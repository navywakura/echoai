# TRANSFER-3 ARCH-1 — me equivoqué: el compromiso es inerte y B1 midió dilución

> ## Corrección posterior (B2) — leer antes de la sección 2
>
> La sección 2 afirma que, con salas alineadas, «el oráculo gana»: 21/24 metas
> frente a 17/24 con ganancia 2. **Esa ventaja no era admisible: se compraba
> violando la reserva, y este filtro nunca la midió.** No llevaba juez de
> reserva independiente, que es exactamente lo que A2 y A3 sí llevaban.
>
> [B2](TRANSFER3-PLAN-B2-RESULTS.md) reprodujo el efecto con aprendizaje real
> —21/24 y 20/24— y lo auditó: **38 y 48 violaciones de reserva** en los brazos
> aprendidos de ganancia 2 y 3, frente a cero del nominal. Con la estimación de
> regreso reparada, la ventaja desaparece: **51/72 frente a 52/72 nominal**.
> [B3](TRANSFER3-PLAN-B3-RESULTS.md), modelando además el frenado, queda igual.
>
> Lo que sigue en pie de este informe: que el compromiso de plan es inerte
> (sección 1) y que B1 midió dilución por rotación. Lo que se retira: la lectura
> de que Plan B tenía una ventaja real pendiente de confirmar. La tenía sólo
> porque el filtro no miraba la seguridad. Lección para cualquier filtro previo:
> **un margen sin juez de reserva no es margen.**

2026-09-18. **Desarrollo público. TRANSFER-3 no cerrado.** Filtro previo, no
campaña. Contrato: [ARCH-1](TRANSFER3-ARCH1-DESIGN.md), fijado antes de
ejecutar, incluida la regla de retractación que este informe aplica.

Dos resultados, y ninguno es el que predije.

## 1. La explicación arquitectónica queda refutada

Predicción registrada: *la ventaja del oráculo es cero con compromiso 1 y crece
con el compromiso.*

| Condición | Ventaja en metas por compromiso 1 / 2 / 3 / 4 / 6 |
|---|---|
| `flat` (1,1,1,1) | 0 · 0 · 0 · 0 · 0 |
| `gain2` (2,1,1,1) | **4 · 4 · 4 · 4 · 4** |
| `gain3` (3,1,1,1) | **1 · 1 · 1 · 1 · 1** |

Plana. Y la energía es **idéntica dígito a dígito** en los cinco niveles: 2400
frente a 2236 en `gain2` con compromiso 1, 2, 3, 4 y 6.

No es que el mecanismo no funcione. Funciona y está medido: el brazo nominal
descarrila **56–67** planes por condición, el oráculo **ninguno**, y se conservan
entre 105 y 151 compromisos. Lo que ocurre es que **el plan recomprometido
produce la misma acción que la replanificación habría producido**: las creencias
apenas cambian entre pasos contiguos, así que la búsqueda vuelve a derivar el
mismo plan. El compromiso es **conductualmente inerte**.

`commitment_helps = false`. Por la regla escrita antes de ejecutar:

> **Se retira la explicación arquitectónica** de los informes de Plan A y Plan B,
> donde figuraba como interpretación y no como hecho medido. El fracaso de Plan
> A y el de Plan B **se quedan sin causa común demostrada**.

Lo que sí queda medido, y se conserva: en Plan A la precisión no entra porque el
canal es un desempate por orden. Eso fue una medición, no una interpretación, y
sigue en pie. Lo que se retira es la generalización a Plan B y la tesis de que
la replanificación paso a paso sea la causa.

## 2. El veredicto de Plan B estaba mal, y el defecto es mío

Construyendo este filtro apareció un defecto de diseño que afecta a B1: **las
salas están rotadas y la ganancia está fija en la acción 0**. Las acciones son de
marco mundo, así que en unas tres cuartas partes de las salas el agente nunca usa
la acción con ganancia: no hay error de modelo que corregir, mientras que la
desventaja del oráculo —la ráfaga gruesa, que se pasa de los huecos de una
celda— actúa en todas.

Con las salas **alineadas**, mismo cuerpo, mismo planificador y `commitment = 1`
—estructuralmente idéntico al histórico—:

| Condición | Oráculo | Nominal | B1 (salas rotadas) |
|---|---:|---:|---|
| `gain2` | **21/24** | 17/24 | 17 vs 18 |
| `gain3` | **20/24** | 19/24 | 17 vs 19 |
| `flat` | 16/24 | 16/24 | 17 vs 17 |

**El signo del efecto se invierte.** B1 concluyó que el modelo perfecto es peor
que el equivocado; lo que midió fue dilución por rotación, no el mecanismo.
La alineación conserva la forma canónica de cada sala —verificado— así que es la
misma geometría, sólo orientada.

Esa conclusión de B1 queda **corregida**, no borrada: su artefacto y sus números
siguen siendo válidos para el régimen rotado en que se tomaron.

### Lo que esto no autoriza

El oráculo gasta **más** energía (2400 frente a 2236) porque completa más
misiones, y una misión abandonada pronto gasta poco. Comparar energía entre
conjuntos de misiones distintos es exactamente la trampa que A2 dejó
documentada. **Aquí no se afirma ninguna ventaja de energía**, sólo de metas, y
sobre 24 salas sin prueba estadística: es un filtro, no una confirmación.

Tampoco hay aprendizaje todavía: el oráculo recibe las ganancias servidas. Que
exista margen no dice que una escuela pueda encontrarlo ni que sobreviva a una
confirmación prospectiva.

## Razonamiento auditable

- **Hipótesis.** El compromiso de plan es lo que falta para que la precisión
  pague.
- **Evidencia.** Ventaja plana en cinco niveles de compromiso y energía idéntica,
  con el mecanismo demostrablemente activo (descarrilamientos y compromisos
  conservados distintos de cero).
- **Explicación rival.** Que el compromiso no llegara a ejercitarse.
  **Descartada** por esos mismos contadores.
- **Autorrevisión.** Escribí la regla de retractación antes de ver los números
  precisamente porque la explicación era mía. También encontré, sólo al
  construir esto, que mi propio filtro B1 estaba mal planteado: exigí a Plan A
  «comprobar que el planificador puede usar la precisión» y luego monté un banco
  donde el mecanismo no se ejercitaba. El filtro necesita su propio filtro.
- **Actualización.** Abandono la tesis arquitectónica. Recupero Plan B como línea
  viva, en régimen alineado, sin candidato y sin ninguna afirmación de ventaja
  confirmada.
- **Decisión.** No se abre campaña. Lo que procede es un Plan B honesto:
  escuela real que aprenda la ganancia desde consecuencias observadas, jaula,
  salas frescas, criterio de metas fijado antes y confirmación prospectiva. Con
  su propia comprobación previa de que el mecanismo se ejercita.

## Verificación

Artefacto: `lab/transfer3/arch1-filter.json`, hash canónico
`fac999480422b4930777111cb5aa2a7ceb4dcbd322c0a91d5be1dd379311e8f4`.
Auditoría completa en proceso nuevo: `replay_valid=true`, exit 0, mismo hash.
12 tests ARCH-1 nuevos, entre ellos la equivalencia estructural de
`commitment = 1` con el planificador histórico, traza a traza.

```sh
env PYTHONPATH=.. python3 -m unittest tests.test_transfer3_arch1 -q
env PYTHONPATH=.. python3 -m echoai.nexus0.transfer3.filter_arch1 audit lab/transfer3/arch1-filter.json
```

TRANSFER-3 sigue en rojo. Sin candidato, sin campaña, custodia intacta.
ECHO-3 permanece en 13/15.
