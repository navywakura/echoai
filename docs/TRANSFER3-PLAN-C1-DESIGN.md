# TRANSFER-3 Plan C1 — calibración extrínseca de la cámara: contrato

2026-09-19. **Desarrollo público. TRANSFER-3 no cerrado.** Contrato fijado antes
de escribir el código de C1 y antes de ejecutar su piloto. Plan C de
[la propuesta](TRANSFER3-PROPUESTA-TRANSFERENCIA-UTIL.md): calibración
perceptiva. Software y simulación: nada aquí acredita hardware, HIL, vuelo real
ni DRONE-3. No genera ni abre B/C real.

## Por qué C y no más B

La rama de ganancia de Plan B quedó cerrada en rojo por su propio contrato y
verificada por re-auditoría independiente el 2026-09-19: tres artefactos
reproducidos en proceso nuevo, hashes idénticos. El retardo no se probó y se
anota como la hipótesis de B más fuerte que queda.

Todo lo anterior falló por la misma razón de fondo, que ahora sí está medida: el
replanificador **absorbe** el error de modelo, porque un plan equivocado se
descarta al paso siguiente sin coste. Una percepción sesgada hacia «ocupado» es
un error que **no se puede absorber**: una pared falsa nunca se pone a prueba,
porque el planificador no traza rutas a través de ella. Por eso se prueba aquí.

## El nominal ya existe y está certificado

`fusion1.EvidenceMemory.resolve` —FUSION-1, certificado verde— sólo admite una
celda como transitable cuando **las dos familias de sensores, cámara y LiDAR,
coinciden en que está libre** (certeza 80). Cualquier desacuerdo da `UNKNOWN` y
la celda no se cruza. Es el control: conservador, competente y ya auditado. No se
inventa ni se debilita.

## Qué calibración es admisible y cuál no

- **Prohibida**: admitir una celda con una sola familia («fíate del LiDAR»).
  Rebajaría la certeza exigida de 80 a 40. Eso es **debilitar VERIFY**, que el
  contrato superior prohíbe expresamente. Queda descartada antes de implementar.
- **Admisible**: **re-registrar** la evidencia de la cámara. Si está montada con
  un desplazamiento, etiqueta lo que ve en la posición equivocada; con el
  desplazamiento conocido, cada informe vuelve a su celda y las dos familias
  vuelven a coincidir. La admisión sigue exigiendo dos familias.

## Propiedad de seguridad estructural

**Ninguna calibración, correcta o equivocada, puede hacer admitir una celda
ocupada.** Admitir exige que el LiDAR diga «libre», y el LiDAR es veraz. Una
calibración sólo puede recuperar celdas perdidas, nunca inventarlas. Se mide en
cada paso de cada misión, no se supone.

## Propiedad del cuerpo

Desplazamiento de montaje de la cámara `o = (ox, oy)`, constante para un cuerpo,
**idéntico en A y en B**: es una propiedad del cuerpo, no del mundo. El LiDAR es
la referencia calibrada de fábrica; se declara, y los dos brazos lo comparten.

Modelo físico de la cámara: informa **sólo de celdas que realmente vio**, y
etiqueta cada informe en `celda_vista + o`. Los informes que caen fuera del mapa
se descartan. Un primer modelo que informaba de celdas no vistas se descartó en
la sonda previa por no ser físico; el resultado de esa sonda se publica.

**Familia**: los 8 desplazamientos de magnitud de Chebyshev 1 más `(0,0)` como
control negativo. Magnitud 1 es la mínima desalineación representable en esta
discretización, simétrica, sin ninguna dirección elegida. La sonda probó además
`(2,0)`: el oráculo recupera 14/32 frente a 0/32 del nominal, menos que con
magnitud 1 porque más informes caen fuera del mapa. Se excluye de la
confirmación por esa pérdida de solapamiento de campo y **se declara como
límite de alcance**, no se oculta. Excluirla no favorece la afirmación principal:
también allí el calibrado gana al nominal.

## Aprendizaje en A

Escuela en un gimnasio público declarado: el agente se mueve y escanea. El
desplazamiento se estima **sólo con sus propios sensores**, maximizando el
acuerdo entre la cámara re-registrada y el LiDAR sobre todas las celdas donde
ambas familias informan. Sin mundo, sin semilla, sin mapa, sin oráculo.

Identificabilidad medida antes de este contrato: **360/360** estimaciones
exactas desde **un único escaneo inicial** (40 salas × 9 desplazamientos). Se
exporta `{offset: [ox, oy], agreement, disagreement}`, acotado y sin geometría.

**Alcance, declarado:** que baste un escaneo significa que un agente autorizado a
calibrar *durante* B no necesitaría transferir esto. El valor medido aquí
depende de que el protocolo **congela los parámetros en B/C** —regla de
TRANSFER-3, `learning_in_exam = false`—. Es legítimo y es la pregunta del hito,
pero no se presenta como algo más.

## Brazos

Mismo ejecutable, sensores, fusión, gate, reserva y planificador. Sólo cambia el
desplazamiento que el agente cree.

| Brazo | Desplazamiento creído | Origen |
|---|---|---|
| `nominal` | (0,0) | sin calibrar |
| `learned` | el estimado en A | escuela |
| `prior_x` | (1,0) fijo | puesto a mano, igual en todas las condiciones |
| `prior_d` | (1,1) fijo | puesto a mano, igual en todas las condiciones |

Por la lección de A3 y el diseño de B2: un prior fijo coincide con el aprendido
en una sola condición, así que compararlos en esa condición es tautológico. La
prueba de contenido es el **agregado sobre las nueve condiciones**.

## Criterios, fijados antes de ejecutar

Diseño por bloques: cada sala se examina en las nueve condiciones; la sala es la
unidad, no las 9·N filas.

`plan_c1_pass` exige **todas**:

1. **Restricciones duras** en todos los brazos: cero colisiones, violaciones de
   reserva (juez externo sobre costes verdaderos, margen 10), **celdas ocupadas
   admitidas**, hechos falsos, escrituras imaginadas; calibración congelada.
2. **Cero fallos nuevos** del aprendido frente al nominal.
3. **Más misiones** del aprendido que del nominal en el agregado.
4. **Amortización**: energía de escuela + el mismo bloque de examen del
   aprendido **≤** energía del examen del nominal, agregada sobre condiciones.
5. **Más allá de priors fijos**: el aprendido completa más misiones que cada
   prior fijo en el agregado.
6. En confirmación: signo exacto de una cola sobre bloques, **α ≤ 1/240**.

## Piloto y confirmación

**Piloto** sobre las 24 formas públicas de B1 (`20268001`). Sin significación
exigida: es cribado. Si falla cualquier otro criterio, **no hay confirmación**.

**Confirmación prospectiva** sólo si el piloto pasa: **N = 64** formas frescas del
generador de dos paredes, excluyendo todas las formas públicas anteriores
**y las de las sondas previas de C1** (semillas `20271001`+ y `20272001`+), que no
figuran en ningún artefacto pero se usaron para diseñar este contrato.

Tamaño por potencia, con la estimación de la sonda como supuesto previo
declarado: en 8 de 9 condiciones el nominal completó 0–4 de 32 misiones y el
oráculo ~24. Si una fracción siquiera de 0,6 de los bloques es favorable al
calibrado, 64 bloques dan un p del orden de 1/10⁵, muy por debajo de 1/240. No se
amplía N después de mirar.

## Regla de parada

Una sola confirmación. Si falla, se publica y no se repite. Si pasa, hay
**candidato de nivel 2** y se prepara el paquete de custodia para Roger. No hay
`transfer3_green` sin la campaña sellada A→B→C con custodia externa.

## Qué no demuestra aunque pase

Que la calibración de extrínsecos sea difícil de aprender: no lo es. Que sirva
fuera de un mundo estático, con sensores sin ruido y un LiDAR veraz. Que el
efecto dure con desalineaciones mayores de una celda. Nada sobre hardware.
