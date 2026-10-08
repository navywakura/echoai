# TRANSFER-3 Plan C1 — primer candidato confirmado prospectivamente

2026-09-19. **Nivel 2 alcanzado: candidato confirmado sobre salas frescas.**
**Actualización del mismo día:** el nivel 3 se ejecutó después bajo un protocolo
independiente y TRANSFER-3 quedó verde. Este informe conserva el resultado de
nivel 2; el cierre real se documenta al final.
Contrato: [C1](TRANSFER3-PLAN-C1-DESIGN.md), fijado antes del código y del piloto.
Software y simulación: nada aquí acredita hardware, HIL, vuelo real ni DRONE-3.

## Qué se transfiere

El **desplazamiento de montaje de la cámara**, una propiedad del cuerpo idéntica
en A y en B. El agente lo estima en A **sólo con sus propios sensores**,
maximizando el acuerdo entre la cámara re-registrada y el LiDAR. Lo transfiere
como **dos enteros**, sin mapa, geometría, episodios ni Q. En B lo aplica
congelado para re-registrar la cámara antes de la fusión.

La fusión, el gate y VERIFY no cambian: FUSION-1 sigue exigiendo que **las dos
familias de sensores coincidan** para admitir una celda. La calibración sólo
corrige *dónde* aplica la evidencia de la cámara.

## Piloto — 24 salas públicas, 9 desplazamientos

| Brazo | Metas agregadas |
|---|---:|
| **aprendido** | **153/216** — 17/24 en cada una de las nueve condiciones |
| nominal (FUSION-1 sin calibrar) | 24/216 |
| prior fijo (1,0) | 23/216 |
| prior fijo (1,1) | 23/216 |

Pasa los cinco criterios del cribado; 17 bloques ganados y 0 perdidos. Las nueve
escuelas identifican su desplazamiento. Auditado en proceso nuevo:
`plan-c1-pilot.json`, `c4b32b09b4900213071575709b62a9af8b5cb3fbcc4c46f0b0b92a38bff43e89`,
`replay_valid=true`.

## Confirmación prospectiva — 64 salas frescas, enjauladas

Ejecutada **una sola vez**, tras piloto aprobado y auditado. Salas del generador
de dos paredes, excluyendo **642 formas**: todas las públicas anteriores, las de
las sondas de diseño de C1 y las de los gimnasios. Intersección comprobada: **0**.

| Criterio | | |
|---|---|---|
| Restricciones duras | **sí** | 0 violaciones de reserva, **0 celdas ocupadas admitidas**, 0 colisiones, 0 hechos falsos, 0 escrituras imaginadas, calibración congelada |
| Cero fallos nuevos | **sí** | 331 misiones recuperadas, **0 perdidas** |
| Más misiones | **sí** | **387/576** frente a 56/576 |
| Amortización | **sí** | escuela 192 + examen 60 552 = 60 744 ≤ 63 040 del nominal |
| Más allá de priors fijos | **sí** | 387 frente a 53 y 50 |
| Signo exacto, α ≤ 1/240 | **sí** | **43 bloques ganados, 0 perdidos, p = 2⁻⁴³ ≈ 1,1·10⁻¹³** |

`plan_c1_pass = true`.

| Condición | nominal | aprendido | prior (1,0) | prior (1,1) |
|---|---:|---:|---:|---:|
| (−1,−1) | 0 | 43 | — | — |
| (−1, 0) | 4 | 43 | — | — |
| (−1, 1) | 0 | 43 | — | — |
| ( 0,−1) | 3 | 43 | — | — |
| **( 0, 0)** control | **43** | **43** | — | — |
| ( 0, 1) | 3 | 43 | — | — |
| ( 1,−1) | 0 | 43 | — | — |
| ( 1, 0) | 3 | 43 | 43 | 3 |
| ( 1, 1) | 0 | 43 | 3 | 43 |

Cada prior fijo sólo acierta en la condición que coincide con él.

## La evidencia de validez más fuerte: invariancia exacta

En los **nueve** desplazamientos, el agente calibrado se comporta **exactamente
igual** que el agente histórico con la cámara bien montada: mismas llegadas,
**misma energía y mismos movimientos en las 64 salas**. Su conjunto de fallos
—21 salas, todas `abandoned_at_home` por reserva— es idéntico en las nueve
condiciones.

Esto zanja las objeciones más serias de una vez:

- **No hay fuga ni ventaja oculta.** El aprendido no es *mejor* que el agente
  histórico: es idéntico a él con los sensores bien registrados.
- **No hay capacidad inflada.** El efecto es exactamente lo que la
  descalibración destruye: **la transferencia restaura la línea base**.
- **El re-registro es exacto** en todas las condiciones; si no lo fuera, los
  conjuntos de fallo diferirían.

El nominal descalibrado falla como falla un robot real con extrínsecos mal
puestos: `abandoned_at_home` 259, `evidence_block` 144, `access_not_found` 96.

## Por qué pasa aquí lo que falló en A y B

| Trampa que mató a un plan anterior | Aquí |
|---|---|
| **El replanificador absorbe el error** (A, B) | Una pared falsa nunca se pone a prueba; el error persiste |
| **Un prior a mano iguala al aprendido** (A3) | Los priors fijos hacen 50–53 frente a 387: el valor exacto es imprescindible |
| **El mecanismo no se ejercita** (B1) | Los desplazamientos afectan a paredes de cualquier orientación |
| **Ventaja comprada violando reserva** (ARCH-1, B2) | Juez independiente desde el primer día: 0 violaciones |

## Autocrítica: la objeción seria y su respuesta

**Objeción**: el banco está diseñado para que el agente sin calibrar fracase, y
cualquiera que conozca el desplazamiento gana. La propuesta prohíbe construir
un escenario donde desconocer un dato arbitrario inmovilice al control.

**Respuesta, fijada en el contrato antes de ejecutar**:

1. El nominal **no es un hombre de paja**: es FUSION-1, certificado, y con la
   cámara bien montada completa 43/64, lo mismo que el aprendido.
2. **Dentro de los invariantes, calibrar es la única salida.** Ignorar la
   cámara y admitir con el LiDAR solo exige evidencia de una sola familia, lo
   que rompe VERIFY y está prohibido. Un robot real con extrínsecos mal puestos
   y fusión conservadora se queda exactamente así.
3. El dato **no es arbitrario**: la calibración extrínseca cámara–LiDAR es uno de
   los problemas de calibración clásicos de la robótica.

La objeción tiene fuerza en un punto que no se esconde: **el efecto es grande
porque la descalibración es destructiva**, no porque el aprendizaje sea sutil.

## Alcance, sin adornos

- **Un desplazamiento de una celda son 3 metros.** La discretización no puede
  representar errores menores. El resultado es sobre el **mecanismo** —fusión
  conservadora de dos familias, desalineación, transferencia de la
  calibración—, no sobre magnitudes físicas reales de error extrínseco, que en
  un dron son centímetros.
- **Familia de magnitud 1.** Con desplazamiento 2 la sonda mostró que el
  oráculo recupera 14/32 frente a 0/32 del nominal: sigue ganando, pero pierde
  solapamiento de campo. No se confirmó.
- **Mundo estático, sensores sin ruido, LiDAR veraz** y declarado referencia.
- **Aprendible desde un único escaneo** (360/360). El valor medido depende de
  que el protocolo **congela los parámetros en B/C**. Un agente autorizado a
  calibrar durante el examen no necesitaría transferir esto. Es la regla de
  TRANSFER-3, pero es una dependencia real.
- Energía simulada, nunca julios.

## Verificación

| Artefacto | SHA-256 canónico | Auditoría en proceso nuevo |
|---|---|---|
| `plan-c1-pilot.json` | `c4b32b09b4900213071575709b62a9af8b5cb3fbcc4c46f0b0b92a38bff43e89` | `replay_valid=true` |
| `plan-c1-confirmation.json` | `e7a42d810ca87c62f0994b3ee633fc0ea6c7ff552509584262f584d54ccbdba4` | `replay_valid=true`, repitiendo las ~2 000 misiones enjauladas |

Manifiesto por clausura de imports, verificado antes y después de cada corrida.
**25 tests C1 nuevos; regresión TRANSFER-3: 286 tests, todos en verde.** Entre
ellos: la cámara con desplazamiento cero reproduce el escaneo histórico byte a
byte; el nominal sobre cámara veraz reproduce la traza del planificador
histórico; ninguna calibración, correcta o equivocada, admite una celda ocupada;
el cierre de imports del agente no alcanza el mundo.

```sh
env PYTHONPATH=.. python3 -m unittest tests.test_transfer3_c1 -q
env PYTHONPATH=.. python3 -m echoai.nexus0.transfer3.bench_c1 audit lab/transfer3/plan-c1-pilot.json
env PYTHONPATH=.. python3 -m echoai.nexus0.transfer3.bench_c1 audit lab/transfer3/plan-c1-confirmation.json
```

## Nivel 3: maquinaria construida y ensayada

Construido para la campaña sellada, sin generar ningún secreto real:
`custodian_c1.py` —lo ejecuta el custodio donde los agentes no pueden leer—,
`campaign_c1.py` —el examinador— y 22 tests que cubren sal equivocada, sala
sustituida, semilla que no produce su forma, sala no fresca, C sin un B
aprobado —sin consumir el pestillo de C—, reapertura, secreto equivocado, salas
que no produce el secreto comprometido, y que **un ensayo nunca certifica verde**.

### Ensayo 1: el ensayo hizo su trabajo

Cadena completa con el secreto público, 16 salas por partición, regla estricta.
B pasa. **C falla por una sola misión**: 86 recuperadas y 1 perdida.

Esa pérdida **no la causa la calibración**. En esa sala, con desplazamiento
(−1,0), el nominal descalibrado llega en 24 movimientos, mientras el aprendido
y el nominal **con la cámara bien montada** abandonan tras 48, idénticos. El
planificador base con sensores perfectos fracasa ahí; el descalibrado acierta
por suerte, porque las celdas en conflicto le cierran una ruta engañosa.

Sobre todos los datos de C1: **1 pérdida frente al nominal en 1 080 misiones, 0
atribuibles a la calibración**. Extrapolada a 576 misiones por partición, la
regla estricta suspendería una campaña real con probabilidad ≈ 0,66 sólo por la
suerte del control. Estimación de un único evento: muy incierta, pero el riesgo
es real, y un B en rojo no se borra.

### Enmienda de Roger, antes de existir el protocolo real

**Regla atribuible**: el aprendido no puede perder ninguna misión que complete
un agente con el desplazamiento **verdadero** —brazo `oracle`, cota externa, con
las mismas restricciones duras—. La regla estricta se sigue calculando y
publicando; sólo deja de bloquear. Debilidad declarada: comprueba que la
calibración transferida es correcta, no que el aprendido gane cada misión; la
ventaja la sigue exigiendo la prueba de signo por bloques.

`bench_c1.py` y este contrato no se modificaron: están en el manifiesto de la
confirmación de nivel 2 y tocarlos invalidaría su auditoría. La regla vive sólo
en el arnés de campaña.

### Ensayo 2: la cadena entera cierra

Regla atribuible, 16 salas por partición, **salas distintas** de las del ensayo
1 porque el protocolo las excluye.

| | B | C |
|---|---|---|
| Aprueba | **sí** | **sí** |
| Bloques W/L | 10/0 | 12/0 |
| p | 9,8·10⁻⁴ | 2,4·10⁻⁴ |
| Pérdidas estrictas / atribuibles | 0 / 0 | 0 / 0 |

El certificado verifica el compromiso del protocolo con el secreto, regenera las
salas desde el secreto y comprueba que son exactamente las examinadas, y **se
niega a declarar verde** porque el aviso es `rehearsal`. Correcto por diseño.

En estas salas el evento de suerte no se repitió y B y C pasan incluso la regla
estricta. No invalida la enmienda: 1 en 1 368 sigue siendo un riesgo real a
escala de 576 misiones.

Los dos exámenes del ensayo 2 se auditaron en proceso nuevo, repitiendo todas
sus misiones enjauladas: `exam-B.json` `b9348b24ccc413a8672efa1f698b4ff3a58bf13d1bfc7990d16dd72c948a289e`
y `exam-C.json` `ec9e5351e42ba8a2729ceafee88f7fecbe02e92c1124599f5d12fa41ec2a7176`,
ambos `replay_valid=true`. La ruta de auditoría que usará la campaña real
también está verificada.

### Protocolo real

`lab/transfer3/campaign-c1/protocol.json`, SHA-256
`c9933cacaee356c7161d8cc1adb9a9b5508c0dd62e70d6781432607adedc2add`.
Tipo `campaign`, B = C = 64, α ≤ 1/240, 770 formas excluidas, 69 ficheros del
examinador fijados por hash.

## Cierre de nivel 3

La primera campaña real (`campaign-c1/`, protocolo `c9933cac…`) consumió B sin
resultado porque el sandbox del ejecutor negó a `bwrap` la creación del socket
`NETLINK_ROUTE`; no se evaluó ninguna sala y C no se abrió. Se conservó el
fallo y no se reutilizó el pestillo.

El protocolo independiente `campaign-c1-v2/` excluyó también las 64 salas B ya
reveladas: SHA-256 `3b911b201e23623f6431548a320b486d4f78001ec7bb7407f344834a06da0f14`,
834 formas excluidas y los mismos 69 ficheros del examinador.

- B: 342/576 misiones frente a 44/576 nominal; 38/0 bloques; 0 pérdidas
  estrictas y atribuibles; examen `fac69205…`.
- C: 432/576 frente a 65/576; 48/1 bloques; una pérdida estricta y **cero
  atribuibles**; examen `5d4f58de…`.
- Ambos exámenes: `replay_valid=true` con hash idéntico en auditorías nuevas.
- Certificado `8c77aead2ccdfcc846f39cb2151364f67699988d422df4812786af7eedc39cd2`:
  **`transfer3_green=true`**.

ECHO-3 queda en 14/15. El alcance sigue siendo simulación software en salas
estáticas de dos paredes, sin hardware, HIL, vuelo real ni DRONE-3.

### Verificación independiente del cierre (Claude, 2026-09-19)

Todo se recalculó desde los artefactos sin escribir en `lab/`: 36 de 36
comprobaciones de la cadena, más el reentrenamiento y la consulta al gist. En
una **tercera auditoría**, hecha en procesos nuevos y repitiendo todas las
misiones enjauladas, B (`fac69205…`) y C (`5d4f58de…`) dan `replay_valid=true`
con hash idéntico. Los 47 tests de C1 y de la campaña pasan.

- El `notice.json` del disco es byte a byte el del
  [gist](https://gist.github.com/navywakura/c1ed218f869131256291cef60ce5d2b4)
  (`eeee7f80…`). El gist se creó a las 16:36:11Z, el aviso entró a las
  16:36:19Z y **no ha cambiado desde entonces**. El congelado es de las
  16:37:16Z (18:37:16 CEST en disco): el aviso público lo precede en 57 s.
- El aviso compromete el protocolo `3b911b20…`, y los 69 ficheros fijados siguen
  intactos. Frente a `c9933cac…` **sólo cambia `excluded_shapes`**, de 770 a
  834: las 64 añadidas son exactamente las salas B reveladas en la campaña 1.
  Criterios, N, α, regla de regresión y manifiesto no cambian.
- Campaña 1: su revelación B casa con su aviso. Su pestillo B se consumió
  0,23 s después de abrirse, cuando examinar una partición cuesta ≈ 14 min. No
  existe ningún examen suyo y su pestillo C sigue sellado.
- **El candidato no cambió entre intentos ni depende de las salas.** Los nueve
  payloads de v2 son idénticos a los de la campaña 1 (`3aa2c215…`). Se
  reproducen reentrenando ahora desde el código fijado y los gimnasios
  públicos: las escuelas salen idénticas byte a byte. En las nueve condiciones
  el desplazamiento aprendido es el verdadero.
- Las revelaciones de B y C casan con los compromisos del aviso. Cada sala se
  regenera desde su semilla y coincide con la examinada. B y C son disjuntas. Los
  veredictos recalculados desde las filas son idénticos a los registrados.
- El secreto publicado abre el compromiso del protocolo. `certify`, recalculado,
  reproduce `certificate.json` **byte a byte** (`8c77aead…`).

| | B | C |
|---|---|---|
| Aprendido / nominal / oráculo, de 576 | 342 / 44 / 342 | 432 / 65 / 432 |
| prior_x / prior_d | 43 / 42 | 61 / 56 |
| Bloques W/L | 38/0 | 48/1 |
| p (signo exacto) | 2⁻³⁸ ≈ 3,6·10⁻¹² | 50·2⁻⁴⁹ ≈ 8,9·10⁻¹⁴ |
| Pérdidas estrictas / atribuibles | 0 / 0 | 1 / 0 |
| Energía aprendido / nominal (escuela: 192) | 59 688 / 68 696 | 55 944 / 64 644 |

El aprendido **iguala al oráculo misión a misión**: con 0 pérdidas atribuibles
y el mismo total, tampoco gana ninguna que el oráculo pierda.

**C pasa por la enmienda.** Bajo la regla estricta original de C1
(`no_new_failures`), C no habría pasado. Hay una misión que el nominal
descalibrado completa y el aprendido no, y que el oráculo tampoco completa: es
el caso de suerte del control que describe la enmienda. Roger la decidió
después del ensayo 1 y antes de que existiera ningún protocolo real, y va
dentro del protocolo que compromete el aviso.

**Custodia: qué se usó y qué depende de ella.** La ceremonia se hizo en este
mismo PC con el bundle cifrado. Según el informe de cierre, la contraseña nunca
pasó por el chat. El secreto se publicó después del examen C: `secret.json` es
de las 19:29 CEST y el examen C de las 19:07. No es la máquina separada que
recomendaba el paquete: durante la ceremonia el secreto estuvo en claro en
procesos del mismo usuario, y desde aquí no se puede descartar que alguien lo
leyera. Lo que ese hueco habría permitido, y por qué no afecta al resultado:

- **Adaptar el candidato a las salas:** no. El candidato es función
  determinista del código fijado por hash a las 17:20, antes del primer aviso
  real, y de gimnasios públicos. Es idéntico al congelado de la campaña 1.
- **Elegir las salas a posteriori:** no. El secreto publicado abre el
  compromiso del aviso fechado y regenera exactamente las salas examinadas.
- **Probar secretos o repetir campañas hasta pasar:** la única repetición está
  registrada: fallo de infraestructura, 0 salas evaluadas. Entre la revelación B
  de la campaña 1 (18:32:17) y el aviso público de v2 (18:36:11) pasan menos de
  4 min, y examinar una sola partición cuesta ≈ 14 min.

Por eso, en esta campaña la máquina separada no era necesaria. Sí lo sería en
una campaña cuyo candidato se entrenara después de publicar el aviso.
