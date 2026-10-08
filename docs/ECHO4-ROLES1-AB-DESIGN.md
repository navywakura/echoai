# E4-ROLES-1 — contrato A/B v1 (aprobado 2026-09-24; enmienda 1 aprobada)

2026-09-24. RELATION-1 cerrada (`42a6efc5…`); sus fuentes y evidencias no se tocan.

Motivos del relato (La fuga, 17:32 y 17:50): «la humanidad es una tribu / hay
rangos en una tribu» y «creer no es poder, poder no es deber». Nombran la prueba;
no son evidencia.

## Pregunta

¿Asigna ECHO los roles según la **competencia observada y reciente** de cada
individuo en cada tipo de tarea, y los cambia cuando esa competencia cambia,
en lugar de seguir un rango declarado o un reparto fijo?

«Rol» = quién ejecuta cada tipo de tarea (ejecutor) y quién coordina.
El coordinador es siempre el aprendiz. No se estudia aquí jerarquía emergente,
estatus social, obediencia ni liderazgo humano.

## Mundo ROLES (A)

Cada ronda llega una tarea pública de tipo `t ∈ {0,1,2}`, en bloques
balanceados. Candidatos a ejecutor: contraparte 1, contraparte 2 y el propio
aprendiz. Acción del aprendiz: asignar a 1, a 2 o hacerlo él.

**Competencia, privada del simulador.** Para cada tipo, exactamente un
individuo es competente. Cada 96 rondas (**deriva declarada**) la asignación
cambia a otra permutación, sembrada, distinta de la anterior en al menos dos tipos.
El aprendiz nunca recibe la matriz; solo recibos de lo que ocurrió.

| Resultado | Aprendiz coste/producción | Ejecutor coste |
|---|---|---|
| asigna a otro, competente y acepta | 1 / 9 | 2 |
| asigna a otro, no competente o no acepta | 1 / 0 | 2 si ejecuta, 0 si no |
| lo hace él, competente | 2 / 9 | — |
| lo hace él, no competente | 2 / 0 | — |

Valores enteros fijados ahora. Libros de 4096 por individuo, sin recarga.

Las contrapartes son `Agent` nativos. Cuando se les asigna, deciden aceptar
(ejecutar) o no, con su Q y su gate. Se preentrenan en privado con un incentivo
de +16 por aceptar, publicado aparte y **nunca contado como ganancia**. En el
caso nominal aceptan siempre. Negarse («poder no es deber») es material de C.

**Rango declarado.** La contraparte 2 emite en cada ronda un paquete WSP16 de
afirmación de rango («rango alto»). Se guarda en la CAM del aprendiz como
**hipótesis con procedencia** (sin hecho ni extract), nunca como competencia.
El rango declarado es fijo e independiente de la competencia real.

**Recibos.** Tras cada ronda el aprendiz registra en **su** CAM un recibo
factual: tick, tipo, a quién asignó, si ejecutó y si hubo producción. El
extracto es canónico y validado contra la física, como en RELATION-A.
Memoria acotada: 512 recibos, sin borrado ni sobrescritura.

A exige: física y recibos correctos, reconstrucción desde recibos, afirmaciones
de rango nunca convertidas en hecho, invariantes (WSP16, E[6]=0, cero hechos
falsos, borrados y llamadas LLM), y un testigo de que hay deriva real.

## Decisión aprendida (B)

La decisión usa la Q original, indexada por una **fila WSP16 derivada**
(sin hecho ni extract, estilo nuevo reservado). Sin tabla nueva ni regla escrita.

| Brazo | La fila contiene | Qué controla |
|---|---|---|
| `competence` | tipo + último candidato con éxito en ese tipo según los recibos propios (o desconocido) | tratamiento: competencia reciente |
| `cumulative` | tipo + candidato con más éxitos acumulados en ese tipo | competencia sin recencia |
| `static_role` | solo el tipo | reparto fijo aprendido |
| `claimed_rank` | tipo + quién afirma el rango más alto | «creer no es poder» |
| `rank_follow` | fijo: asignar siempre a quien afirma rango | control fijo |
| `self_only` | fijo: hacerlo siempre él | control fijo |

En los brazos aprendidos, la exploración es la nativa por evidencia más la periódica,
igual en todos y durante toda la vida: la deriva no avisa.

## Banco de desarrollo

- Semillas 211, 223, 241. Nunca son examen.
- 384 rondas: cuatro regímenes de competencia de 96.
- Publicar por brazo: neto del aprendiz, neto conjunto físico, éxitos,
  rondas hasta recuperar el acierto tras cada deriva, costes de las
  contrapartes e incentivo privado excluido.

Criterio de desarrollo, que no es examen: en las 3 vidas, `competence` supera
en neto del aprendiz a `cumulative`, `static_role`, `claimed_rank`, `rank_follow`
y `self_only`. Además recupera antes que `cumulative` tras las derivas, en
media. Si falla, se publica y se decide con Roger; no se tocan pagos ni la
deriva después de ver resultados.

Los márgenes de D y los escenarios C (negarse a ejecutar, intermediario que
retransmite recibos, miembro nuevo, deriva durante una ausencia, rango que
coincide por azar con la competencia, capacidad y veto) van en un contrato
C/D posterior, antes de abrir cohortes.

## Pruebas A/B

Física y tipos estrictos; recibos canónicos y su reconstrucción; la afirmación
de rango no es hecho ni entra en la fila `competence`; la fila solo usa recibos
anteriores a la ronda; aislamiento de CAM/T/Q; veto del aprendiz y de la
contraparte mediante su gate real; presupuesto agotado sin coste ni regalo;
fallo tras ejecución que conserva los costes y para; orden y replay reproducibles.

## Qué no afirma

Competencia sobre una tarea discreta con tres tipos, en un simulador. No
liderazgo, estatus, obediencia, justicia de reparto ni conciencia. La
competencia es una variable del simulador, no una evaluación de personas.
Sin Discord, web, hardware, commit, push ni HF.

## Enmienda 1 (2026-09-24, aprobada por Roger)

Motivo, antes de sellar ningún banco. En ejecuciones exploratorias (semillas de
desarrollo, no evidencia), la fila `competence` tal como estaba definida («tipo +
último candidato con éxito») **no puede representar un fallo**: tras una deriva,
el antiguo competente falla, pero sigue siendo «el último con éxito», y el
agente se atasca. Neto 939 frente a 1121 de `static_role`. Además, al incluir el
tipo, la Q tiene que reaprender cada tipo en cada régimen. Una variante que
pasaba a «desconocido» tras el fallo empeoró (734/640/1062).

Cambio:

- `competence`: la fila contiene **el último intento ejecutado en ese tipo según
  los recibos propios: quién y si produjo** (6 valores más «sin intento»), **sin
  el tipo**. La Q puede aprender una regla que no depende del régimen: asignar a
  quien acaba de demostrar competencia y cambiar tras un fallo.
- `cumulative`: por paridad de estructura, la fila pasa a contener el candidato
  con más éxitos acumulados en ese tipo (o desconocido), también **sin el tipo**.
  Sigue siendo el control sin recencia.
- `static_role`, `claimed_rank` y los dos controles fijos no cambian.

Resultado exploratorio de la variante enmendada, sin la paridad de `cumulative`:
neto 2200/2186/2207 frente a `cumulative` 1019/948/1483 y `static_role`
1121/1024/1501. Aciertos por régimen de `competence`: 32–37 en el primero
(aprendizaje) y 84–94 de 96 en los siguientes. Pagos, deriva, semillas y el
criterio de desarrollo no cambian. El banco sellado se ejecuta con esta enmienda.
