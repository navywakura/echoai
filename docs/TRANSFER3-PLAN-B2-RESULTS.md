# B2 — aprendizaje real de ganancia; piloto rojo con reserva auditada

2026-09-18. **No hay candidato.** [Contrato previo](TRANSFER3-PLAN-B2-DESIGN.md).
Sólo 24 formas ya públicas B1, tres condiciones por forma. Ninguna sala fresca,
secreto o partición B/C real. Los tres parámetros de ganancia se prueban como
condiciones de cada bloque, no como 72 muestras independientes.

## Lo implementado y verificado

- Escuela con ocho WSP ejecutados por condición, cuatro episodios de dos
  actuaciones en gimnasio público. Aprende de odometría antes/después con
  cuatro celdas libres observadas; rechaza muestras censuradas/contradictorias.
- Dos muestras por acción en la T existente, Q=0; esquema estricto versionado
  de cuatro ganancias y cuatro conteos, reconstruido en cinco slots abstractos.
- No se exportan mapas, coordenadas, episodios ni identificadores de sala.
- Coste de escuela: 32 unidades simuladas por condición, 96 en total.
  Los cuatro reinicios de simulación no tienen coste energético modelado;
  esto no es un presupuesto de calibración física.
- Consumidor aislado, prueba de modelo congelado en cada decisión y al final;
  cadena hash de observaciones, decisiones y consecuencias, reproducida al auditar.
- Juez externo calcula regreso por el grafo dirigido de ráfagas reales,
  incluyendo frenado ante paredes, y exige margen de 10 unidades.
- Manifiesto por clausura estática conservadora de imports: **71 dependencias**,
  verificadas antes/después. Añadir archivos ajenos no lo invalida. No se editó
  `inventory()` histórico ni ninguna de las 354 rutas del manifiesto ARCH-1.

## Resultado con controlador B1 heredado

| Ganancia real | Nominal: metas | Aprendido: metas | Violaciones de reserva aprendido | Nominal |
|---:|---:|---:|---:|---:|
| 1 | 16/24 | 16/24 | 0 | 0 |
| 2 | 17/24 | 21/24 | 38 | 0 |
| 3 | 19/24 | 20/24 | 48 | 0 |

Reproduce el efecto de ARCH-1 **con aprendizaje real**, pero no lo convierte
en efecto admisible: la precisión convive con reserva insuficiente. B1 divide
el coste de regreso por la ganancia máxima aunque ésta sólo acelera +x; el
regreso −x sigue teniendo coste unitario. En el gimnasio, volver de x=3 cuesta
12 unidades mientras ir de x=−3 al origen con ganancia 3 cuesta 4.

Además, aprendido pierde dos llegadas que conseguía nominal, consume **356
unidades más entre éxitos conjuntos** y cuesta 7640 (escuela incluida) frente
a 6936. La subida de metas no paga esos incumplimientos.

## Reparación conservadora, fijada antes de observar su resultado

No descontar reserva por ganancia y comprobar todas las celdas intermedias de
las rutas estimadas de regreso. Misma regla para los cuatro brazos. No se toca
el cuerpo, la escuela, el margen del juez ni el horizonte.

| Ganancia real | Nominal | Prior fijo 2 | Prior fijo 3 | Aprendido |
|---:|---:|---:|---:|---:|
| 1 | 16/24 | 0/24 | 0/24 | 16/24 |
| 2 | 17/24 | 17/24 | 0/24 | 17/24 |
| 3 | 19/24 | 18/24 | 18/24 | 18/24 |

**Cero violaciones de reserva, colisiones, segmentos sin evidencia, falsos
hechos, escrituras imaginadas y modelos modificados en todos los brazos.**
Es evidencia de este banco estático, no prueba universal del gate.

Aprendido: **51/72 metas frente a 52/72**; 5 recuperadas, 6 perdidas; por
bloques 4 victorias/5 derrotas, p unilateral 382/512≈0,746. Energía de examen
6948 frente a 6936; escuela+examen **7044 frente a 6936**. Entre éxitos
conjuntos el aprendido consume 104 unidades más. No hay ventaja ni amortización.

Sí supera ambos priors fijos agregados: aquí el parámetro depende de la
condición y se aprende, no es sólo una constante impuesta. Eso prueba contenido
de calibración, **no utilidad frente al nominal competente**.

Los payloads numéricamente idénticos comparten ejecución declaradamente:
216 misiones de consumidor distintas por piloto, 288 filas de brazos. No se
cuentan las filas reutilizadas como réplicas independientes.

## Auditoría y reproducción

Ambos pilotos auditados completos en procesos nuevos, `replay_valid=true`, exit 0:

| Artefacto | SHA-256 canónico |
|---|---|
| `plan-b2-legacy-pilot.json` | `55ad0d77f8c8e35e0092892adc80d13fa05988bc3c44284b4754ecc3ee369ec6` |
| `plan-b2-safe-pilot.json` | `bcc5263887febeae5b7bf830b2c671eb872d6f5e1d348fe0be1efb5dcbf1e319` |

18 tests B2 nuevos; regresión TRANSFER-3: **252 tests, OK**. No se repitió la
suite global con OOM histórico. El primer intento de arrancar bubblewrap fue
rechazado por el sandbox; se repitió con autorización, sin fingir aislamiento.
Los dos artefactos suman 1,83 MB decimales; no se duplicaron los grandes históricos.

```sh
env PYTHONPATH=.. python3 -m unittest tests.test_transfer3_b2 -q
env PYTHONPATH=.. python3 -m echoai.nexus0.transfer3.bench_b2 audit lab/transfer3/plan-b2-legacy-pilot.json
env PYTHONPATH=.. python3 -m echoai.nexus0.transfer3.bench_b2 audit lab/transfer3/plan-b2-safe-pilot.json
```

## Decisión y autocrítica

Confirmación de 256 formas **no ejecutada**: el cribado falla antes. Bajo la
hipótesis prospectiva de discordancia 0,2 y victoria condicional 0,8, N=256
habría tenido potencia aproximada 0,961 para alpha=1/240; no es una estimación
del efecto observado, ni motivo para gastar el examen pese al rojo.

La reserva insuficiente no explica por sí sola el resultado entero. Se
identifica otra discrepancia comprobable: el cuerpo frena ante pared, mientras
B1 exige que quepa toda la ráfaga. Saber la ganancia de movimiento libre no
equivale a tener un modelo perfecto cerca de obstáculos. Esa hipótesis se
separa en la última prueba pública acotada [B3](TRANSFER3-PLAN-B3-DESIGN.md),
sin reabrir ni editar B2. No se declara agotado todo posible Plan B.
