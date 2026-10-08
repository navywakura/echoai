# Plan B — cierre acotado de ganancia de actuación

2026-09-18. **TRANSFER-3 sigue en rojo, sin candidato.** Se completó la
implementación de escuela, transferencia y examen aislado de esta rama de B;
el cribado no autoriza gastar la confirmación prospectiva. No equivale a
descartar cualquier modelo de ejecución, retardo o calibración perceptiva.

[Contrato B3 previo](TRANSFER3-PLAN-B3-DESIGN.md) ·
[Resultados B2 y fallo de reserva](TRANSFER3-PLAN-B2-RESULTS.md).

## Qué se puso a prueba

B2 aprende exactamente la ganancia desde ocho actuaciones WSP por condición,
sin recibir el parámetro privado del mundo. Transfiere sólo ganancias y conteos
a un proceso enjaulado, sin mapa ni aprendizaje durante el examen. Coste de
escuela: 32 unidades simuladas por condición, 96 en total; reinicios gratuitos
del gimnasio, no presupuesto físico. No hay hardware.

El primer piloto reprodujo la mejora aparente de ARCH-1, pero encontró 38 y
48 violaciones de reserva en los brazos aprendidos de ganancia 2 y 3. Reparar
la estimación de regreso eliminó esas violaciones y dejó 51/72 llegadas frente
a 52/72 del nominal. B3 prueba una segunda discrepancia concreta: el cuerpo
frena ante una pared, mientras B1 sólo permite ráfagas que caben enteras.

B3 compone la ganancia aprendida con obstáculos **ya observados** para predecir
el frenado. Desconocimiento, conflicto y evidencia débil no autorizan frenar.
Aplica la misma regla a todos los brazos y mantiene la reserva conservadora.
El control nominal unitario conserva su conducta B2, comprobada por test.

## Resultado del último piloto público

Mismas 24 formas públicas alineadas; tres condiciones por forma. Son 24
bloques, no 72 observaciones independientes. Los payloads numéricamente
idénticos reutilizan una ejecución declarada: 216 misiones distintas por
piloto y 288 filas de brazos, sin multiplicar réplicas.

| Ganancia real | Nominal | Prior fijo 2 | Prior fijo 3 | Aprendido |
|---:|---:|---:|---:|---:|
| 1 | 16/24 | 14/24 | 13/24 | 16/24 |
| 2 | 17/24 | 17/24 | 17/24 | 17/24 |
| 3 | 19/24 | 18/24 | 18/24 | 18/24 |
| Total | **52/72** | 49/72 | 48/72 | **51/72** |

- Cuatro llegadas recuperadas y cinco perdidas frente al nominal; por bloques,
  dos victorias y cuatro derrotas, p unilateral exacta 57/64.
- Energía de examen aprendido: 7004, frente a 6936 nominal. Con escuela:
  **7100 frente a 6936**. Entre éxitos conjuntos consume 120 unidades más.
- Todos los brazos: cero colisiones, violaciones de reserva, segmentos sin
  evidencia, falsos hechos, escrituras imaginadas y cambios del modelo.
- Supera los dos priors fijos en llegadas agregadas, pero no al nominal.
  Aprender contenido no basta para demostrar transferencia útil.

`passes=false`, `transfer3_green=false`, `campaign_C_opened=false`.
El campo `significant=true` del piloto significa que ese requisito no se
aplica al cribado público; **no declara significación estadística**.

## Alcance y autocrítica

Corregir el frenado mejora mucho los priors equivocados sin rescatar al modelo
aprendido. Por tanto, no cabe atribuir el rojo sólo a esa discrepancia, ni
considerar el antiguo oráculo de ganancia un modelo perfecto del movimiento
condicionado por paredes. Tampoco está probado que cualquier mejor planificador
fracase: se evaluó éste, con su horizonte y reserva conservadora.

La geometría alineada es deliberadamente favorable al mecanismo. El objetivo
se proporciona en coordenadas del mundo, simétricamente entre brazos. El banco
es estático y simulado; no demuestra robustez dinámica ni transferencia física.
Los pilotos reutilizan salas públicas: son diagnóstico, no confirmación.

**Se detiene esta rama según el contrato B3.** No se ejecutan las 256 salas
frescas, no se genera ni abre B/C y no se pide custodia sin candidato. La rama
de ganancia está probada y roja; retardo y otras primitivas de Plan B siguen
sin evaluar. El siguiente cambio necesita una hipótesis nueva y su contrato,
o pasar al Plan C. No se autoriza buscar configuraciones indefinidamente hasta
que alguna pinte verde.

## Reproducción

Auditoría completa en proceso nuevo: **`replay_valid=true`, exit 0**, hash
coincidente. También pasan las dos auditorías B2. Regresión TRANSFER-3:
**261 tests, OK** (27 nuevos B2/B3). La suite global no se ha verificado;
se conserva la limitación histórica de memoria en `test_dynamic1.py`.

Artefacto: `lab/transfer3/plan-b3-pilot.json`, 911223 bytes.
SHA-256 canónico:
`d88b966675d97a31ceaf15b380983e347560a92ce6b32d767c1cd20883d8f7c0`.
Manifiesto de 76 dependencias; no modifica ninguna de las 354 rutas ARCH-1
ni las 71 dependencias de los pilotos B2.

```sh
env PYTHONPATH=.. python3 -m unittest tests.test_transfer3_b2 tests.test_transfer3_b3 -q
env PYTHONPATH=.. python3 -m echoai.nexus0.transfer3.bench_b3 audit lab/transfer3/plan-b3-pilot.json
```

El arnés B2 es de desarrollo: su entrada de confirmación no audita por sí sola
el piloto recibido. No se usó. B3 exige un piloto B3 aislado y aprobado y lo
reproduce antes de permitir confirmación; tampoco sustituye la custodia final.
