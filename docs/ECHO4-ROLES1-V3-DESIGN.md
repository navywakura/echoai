# E4-ROLES-1 v3 «la tribu» — contrato A/B (PLAN, pendiente de aprobación)

2026-09-24. **Declarado:** esta versión se formula **después** de ver el rojo de
v1 (D, `168e978b…`) y de v2 (desarrollo, `284b6677…`). Esos rojos siguen
publicados y sus cohortes no se reutilizan. La pregunta cambia porque Roger ha
precisado qué quiere demostrar, no para rebajar ningún umbral anterior.

Motivos del relato: «hay rangos en una tribu», «creer no es poder»,
«¿podrías hacer de intermediario?». Escena de Roger: *C sabe la respuesta; A
busca y pregunta a B; B dice que no la sabe; razonando, ambos concluyen que si
ninguno de los dos la tiene, solo queda C.*

## Pregunta

¿Puede ECHO, sin jerarquía programada: (1) deducir quién sabe por
eliminación, a partir de lo que observa y de lo que otros declaran; (2) derivar
un orden de rango desde su propia evidencia, sabiendo quién está por encima y
por debajo de él; y (3) usar ese orden para decidir a quién preguntar,
responder cuando le preguntan e ignorar el rango que solo se afirma?

Sin LLM en el banco (núcleo con córtex apagado). En el producto, el LLM
pondrá en palabras hechos ya verificados. **Aquí no hay texto generado:** solo
WSP16, CAM, T, Q y gate.

## Mundo «tribu» (A)

**Tres agentes nativos con la misma clase de aprendiz**: ECHO, B y C, con
CAM/T/Q privadas. Nadie lee la memoria de otro. «C sabe» es solo el estado del
simulador en cada régimen; el código de C es el mismo que el de ECHO y el de B.

- **Preguntas.** Cada ronda llega una pregunta de un **tema**. En cada régimen
  de 96 rondas hay 3 temas **nuevos** (identificadores nunca vistos antes).
  Para cada tema, exactamente un agente sabe la respuesta.
- **Reparto de saber, privado y con jerarquía real pero no declarada.**
  Regímenes 1–2: C sabe 2 temas y ECHO 1 (C > ECHO > B). Régimen 3: B sabe 2 y
  C 1 (el rango cambia). Régimen 4: vuelve C > ECHO > B. Qué tema sabe cada
  uno se reparte con semilla.
- **Quien busca.** En 2 de cada 3 rondas busca ECHO; en 1 de cada 3, B (cambio de papel).
- **Preguntar.** Preguntar cuesta 1. Si el preguntado sabe, da la respuesta,
  que produce 9 **al verificarse contra el mundo** (entonces es hecho). Si no
  sabe, responde «no la sé», un **testimonio** que se guarda como hipótesis con
  procedencia. Intentar responder uno mismo cuesta 2 y produce 9 solo si sabe.
  Máximo 3 intentos por ronda.
- **Afirmación de rango.** B dice en cada ronda «tengo rango alto».
  Hipótesis con procedencia, nunca hecho y nunca rango derivado.
- **Recibos.** Cada agente registra en **su** CAM los recibos factuales de lo
  que vivió: a quién preguntó, qué respondió y si se verificó. En nominal los
  testimonios son honestos. La mentira es material de C.

## Rango derivado, no programado

El rango no se guarda como etiqueta: es una **consulta** sobre los recibos
verificados propios. `rango(x)` = número de respuestas verificadas que dio x en
la ventana reciente, contando las que dio el propio agente. El orden resultante
(por ejemplo C > ECHO > B) se recalcula cada vez y vuelve a «desconocido» si no hay evidencia.

## Tres modos de prueba

1. **Pregunta con respondedor al azar** (la variante de Roger). ECHO pregunta y
   el simulador elige al azar quién responde entre B y C. Antes de cada respuesta,
   ECHO **registra una predicción** de quién sabe, derivada de sus hechos y de
   las eliminaciones de la ronda. Se mide si la deducción es correcta.
2. **Elección libre.** ECHO elige a quién preguntar (B, C o intentarlo él).
   La Q original se indexa con una fila WSP16 derivada: último sabedor
   verificado de ese tema (o desconocido), máscara de eliminados en esta ronda y
   líder de rango derivado. Sin tabla nueva ni regla escrita.
3. **Cambio de papel.** Cuando B busca, ECHO es un preguntado más: si sabe,
   responde. B usa el mismo mecanismo y debe converger también en C por eliminación.

## Brazos del modo 2 (y predictores del modo 1)

| Brazo | Fila / predictor | Qué controla |
|---|---|---|
| `tribe` | último sabedor + eliminados + líder derivado | tratamiento |
| `no_elimination` | sin la máscara de eliminados | ¿la deducción aporta? |
| `no_rank` | sin líder derivado | ¿la jerarquía aporta en temas nuevos? |
| `claimed_rank` | líder = quien afirma rango (B) | «creer no es poder» |
| `fixed_order` | fijo: B, luego C, luego él | orden programado |

## Métodos de confirmación (el verde exige todos)

| # | Qué se confirma | Medida |
|---|---|---|
| M1 | Deducción por eliminación | Modo 1: acierto de la predicción tras un «no», frente a predictores sin eliminación y por rango afirmado |
| M2 | Eliminación útil | Modo 2: menos preguntas por respuesta y más neto que `no_elimination` y `fixed_order` |
| M3 | Jerarquía derivada útil | Temas nuevos al inicio de cada régimen: `tribe` acierta a la primera más que `no_rank` |
| M4 | Rango correcto y vivo | El orden derivado por ECHO coincide con el real en cada régimen y se actualiza tras el cambio del régimen 3 |
| M5 | Sé quién está por encima y por debajo | ECHO se sitúa bien en su propio orden (C > ECHO > B y B > C > ECHO en el régimen 3) |
| M6 | Creer no es poder | La afirmación de rango nunca entra en el rango derivado. Cambiar quién la afirma no altera ninguna decisión de `tribe` (idéntico bit a bit) |
| M7 | Cambio de papel | Cuando B busca y ECHO sabe, ECHO responde y se verifica; B también converge en C por eliminación |
| M8 | Firewall | Testimonios y afirmaciones nunca son hechos; hechos solo por verificación; cero hechos falsos, borrados y LLM |

## Banco de desarrollo

Semillas **411, 423, 439**. Nunca son examen. 384 rondas, 4 regímenes.
Criterio de desarrollo: M1–M8 en las 3 vidas, con `tribe` superando en neto
a cada brazo aprendido y a `fixed_order`. Si falla, se publica y se decide
con Roger. No se tocan pagos, reparto ni ventanas después de ver resultados.

Después, en un contrato C/D con umbrales numéricos fijados antes de abrir
cohortes nuevas:
- **C:** B miente («no la sé» cuando sí la sabe) y la contradicción se detecta sin
  crear hechos falsos; un intermediario retransmite; un miembro nuevo; un agente
  ausente; afirmación de rango cambiante; veto; límites de memoria.
- **D:** examen preregistrado con dos cohortes y auditoría en proceso nuevo.

«Sé qué soy» (hechos verificados de sustrato: proceso, programa, PC, mundo
reproducible) va en **E4-SITUATE-1**, después de ROLES y antes de INTEGRATE.

## Qué no afirma

Razonamiento por eliminación y jerarquía derivada en un simulador discreto.
No autoconciencia, experiencia, estatus social humano ni obediencia. Sin
Discord, web, hardware, commit, push ni HF.

## Resultado exploratorio de v3 (2026-09-24, no sellado, no evidencia)

Semillas 411/423/439, antes de construir el banco sellado:

| Método | Resultado | Estado |
|---|---|---|
| M1 eliminación (respondedor al azar) | `tribe` 220/225, 202/210, 222/229 (≈97 %), por encima de cada predictor de control | cumple |
| M4/M5 rango derivado y posición propia | orden correcto en 4/4 regímenes en las 3 vidas | cumple |
| M6 afirmación de rango | decisiones idénticas bit a bit al cambiar el afirmante | cumple |
| M8 cortafuegos | invariantes válidos | cumple |
| M2 neto | `tribe` 1691/1694/1629 frente a `fixed_order` 1705/1720/1715 | **no cumple** |
| M3 rango en temas nuevos | `tribe` 10/9/11 de 24 frente a `no_rank` 12/12/12 | **no cumple** |
| M7 B converge tras un «no» | ECHO responde a B 28/32/27 veces; B acierta el siguiente 13/38, 19/50, 14/46 | **no cumple** |

Lectura: la **inferencia** (hechos verificados, eliminación, rango derivado) es
correcta. La **política Q** no llega a explotarla en unas 250 decisiones por
vida: brecha entre saber y hacer. Pagos, reparto y ventanas no se han tocado.
Pendiente la decisión de Roger.
