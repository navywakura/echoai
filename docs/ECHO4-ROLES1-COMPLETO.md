# E4-ROLES-1 — documento completo

**Estado final (2026-09-24): ROLES-1 cerrada en VERDE con v5 «razonar la tribu».**
Recibo de auditoría `roles1_green=true`, digest
`c98c7ab67478bf7ea01712c0727637a162438062336a19b0140bb0b775c6f0f0`.
Anexo L («B miente diciendo que sabe»): v1 con L4 en rojo en desarrollo
(`c77b31cd…`), conservado; **v2 con metaconocimiento en VERDE** (`liar_annex_green=true`,
`957b7a7e…`).

Este documento reúne todo ROLES: pregunta, relato, cada versión con sus
resultados (también los rojos), qué queda demostrado, qué no, cómo
reproducirlo y qué significa para ECHO-4. Es la referencia para citar ROLES;
los documentos por versión siguen siendo la evidencia detallada.

---

## 1. Por qué existe ROLES

ECHO-4 construye un **yo funcional situado**: un agente que distingue su cuerpo
del mundo, atribuye efectos, conserva continuidad, mantiene sus necesidades y
se relaciona con otros. Tras OTHER (representar a otro), INTERACTION (coordinarse)
y RELATION (historia compartida), ROLES pregunta por la **organización del grupo**:

> ¿Quién sabe hacer qué, quién está por encima de quién, y cómo se decide sin
> que nadie lo programe ni lo imponga?

### El relato (La fuga)

ROLES se apoya en tres frases del relato de RxLabs (`rxlabs.org_local`, «La fuga»):

| Frase | Traducción experimental |
|---|---|
| «la humanidad es una tribu / hay rangos en una tribu» (17:32) | La jerarquía existe, pero se **deriva** de la evidencia; no es una etiqueta |
| «creer no es poder, poder no es deber» (17:50) | Afirmar rango no da autoridad; poder hacer algo no obliga a hacerlo |
| «¿podrías hacer de intermediario?» (17:13) | Lo que otro retransmite o declara es hipótesis, no hecho |

Y la escena que propuso Nav para la versión final:

> *C sabe la respuesta. A busca y pregunta a B. B dice que no la sabe.
> Razonando, ambos llegan a la conclusión de que si ninguno de los dos la tiene,
> solo queda C.*

El relato **nombra** las pruebas. No es evidencia de nada, y ninguna prueba
afirma nada sobre conciencia, almas ni jerarquías humanas.

---

## 2. Invariantes que se respetaron en todas las versiones

- WSP de 16 bytes; CAM de 4096 ranuras; cero borrados.
- Enteros en el camino rápido; **córtex apagado**, cero llamadas al LLM.
- **Cortafuegos epistémico:** un hecho necesita extracto verificado. Testimonios
  («no la sé», «sí la sé»), afirmaciones de rango y retransmisiones se guardan como
  **hipótesis con procedencia**, nunca como hechos.
- Las decisiones las toma la **Q original** del agente nativo, a través del **gate**.
  El veto y la parada del operador mandan siempre.
- Cada agente tiene **su propia** CAM/T/Q. Nadie lee la memoria de otro.
- Cada versión: contrato aprobado → implementación → desarrollo
  sellado y auditado → examen con cohortes nuevas → auditoría en proceso nuevo.
  **Los rojos se publican y no se rebaja ningún umbral.**

---

## 3. Cronología completa

| Versión | Pregunta | Resultado | Evidencia |
|---|---|---|---|
| **v1** | ¿Asignar tareas según la competencia reciente da más neto que un reparto fijo? | Desarrollo verde; C 9/9; **D rojo** | [A/B](ECHO4-ROLES1-AB-RESULTS.md) `36b9cab3…` · [C](ECHO4-ROLES1-C-RESULTS.md) `ba7225c4…` · [D](ECHO4-ROLES1-D-RESULTS.md) `168e978b…` |
| **v2** | Lo mismo, corrigiendo la exploración | **Desarrollo rojo** | [v2](ECHO4-ROLES1-V2-DESIGN.md) `284b6677…` |
| **v3** | La tribu: deducir, jerarquizar y actuar según ello | Exploración (no sellada): razona bien, pero no actúa mejor | [v3](ECHO4-ROLES1-V3-DESIGN.md) |
| **v4** | La deducción propone y la Q decide | Exploración (no sellada): el rango histórico engaña | [v4](ECHO4-ROLES1-V4-DESIGN.md) |
| **v5** | **Razonar la tribu** | **VERDE** | [v5](ECHO4-ROLES1-V5-RESULTS.md) `9516fb13…` (desarrollo) · `c98c7ab6…` (examen) |
| **Anexo L v1** | B miente diciendo que sabe | Detección 100 %; L4 en rojo en desarrollo | [L](ECHO4-ROLES1-LIAR-DESIGN.md) `c77b31cd…` |
| **Anexo L v2** | «¿Y si la tengo yo?» (metaconocimiento) | **VERDE** | [L v2](ECHO4-ROLES1-LIAR-V2-DESIGN.md) `8beefd00…` (desarrollo) · `957b7a7e…` (examen) |

### 3.1 v1 — asignar por competencia (mundo de tareas)

**Mundo.** Tres tipos de tarea. Para cada tipo, un único individuo (contraparte 1,
contraparte 2 o ECHO) es competente. La competencia cambia cada 96 rondas sin
aviso. ECHO decide quién ejecuta usando solo sus propios recibos. La contraparte 2
afirma «rango alto» en cada ronda.

**Enmienda 1** (aprobada, antes de sellar): la fila original («último candidato con
éxito») no podía representar un fallo y se atascaba (939 frente a 1121). Se cambió
a «último intento ejecutado en ese tipo: quién y si produjo».

**Desarrollo:** `competence` 2200/2186/2207 frente a 1024–1501 de los controles
aprendidos; recuperación tras cada cambio en 3–38 rondas. La afirmación de rango
no añadía nada (`claimed_rank` = `static_role` exactamente).

**C (9/9):** se encontró y corrigió un **defecto de veto**: un veto hacía que ECHO
ejecutara la tarea él mismo y pagara, porque la acción «esperar» del agente nativo
coincidía con «hacerlo yo» en ROLES. Límites publicados: si la competente se niega,
ECHO sigue asignándole la tarea («poder no es deber»); lo retransmitido cuesta
440–570 de neto porque nunca pasa a hecho.

**D: rojo.** 15/16 vidas ganaban con claridad, pero la semilla 264106 quedó
atrapada: empate en la Q de la fila «falló la contraparte 1», desempate hacia quien
falló y sin exploración tras agotar el presupuesto de evidencia (149 repeticiones).

### 3.2 v2 — exploración justa

Único cambio: exploración periódica nativa para todos. La trampa desaparece, pero
el reparto fijo también se reajusta tras cada cambio. **Desarrollo rojo:**
`competence` 2022/1753/1911 frente a `static_role` 2028/1818/1678.
**Lección:** gran parte de la ventaja de v1 se debía a que los controles no podían
explorar. Con exploración igual para todos, seguir la competencia recupera 3–5
veces más rápido, pero no da más neto en ese mundo.

### 3.3 v3 — la tribu (encargo de Nav)

Nav reformuló la pregunta: tres agentes, jerarquía real no declarada,
deducción por eliminación, respondedor al azar y luego elección libre, y «más
métodos de confirmación, cumplirlos todos». Ocho métodos (M1–M8).

**Exploración:** M1 (eliminación ≈97 %), M4/M5 (jerarquía correcta 4/4), M6
(afirmación ignorada) y M8 (cortafuegos) se cumplían. M2 (neto), M3 (rango en
temas nuevos) y M7 (B converge) no. **Brecha entre saber y hacer:** la inferencia
es correcta, pero la Q no la explota en unas 250 decisiones.

### 3.4 v4 — la deducción propone

La deducción ordena los candidatos y la Q decide si seguirla. **Exploración:**
tampoco basta. Puntuando solo tras aprender, el rango **empeora** los temas nuevos
(5/3/3 frente a 7/6/7), porque la jerarquía cambia justo cuando llegan temas nuevos
y el líder del régimen anterior engaña. La iteración se detuvo para no ajustar
hasta obtener verde.

### 3.5 v5 — razonar la tribu (VERDE)

Nav eligió la afirmación que los datos sostienen. Las de conducta que fallaron
pasaron a ser límites publicados. Contrato fijado **antes** de abrir cohortes
nuevas (266001–266008, 266101–266108). Regresión previa 835/835.

| Criterio | Cohorte 1 | Cohorte 2 |
|---|---|---|
| 1. Deducción por eliminación ≥90 % y mejor que cada control | **97,1 %** (1700/1751) | **97,2 %** (1711/1760) |
| 2. Jerarquía propia correcta, incluida su posición (≥30/32) | **32/32** | **32/32** |
| 3. Actualiza cuando la tribu cambia (≥7/8) | **8/8** | **8/8** |
| 4. Afirmar rango no cambia ninguna decisión (bit a bit, 8/8) | **8/8** | **8/8** |
| 5. Pregunta menos que un orden fijo (≤0,85×) | **0,75×** | **0,73×** |
| 6. Responde cuando le preguntan y sabe | **224/224** | **213/213** |
| 7. Cortafuegos e integridad | sí | sí |

C de v5: con B mintiendo «no la sé», ECHO registra contradicciones (4–8 por vida)
y crea **cero hechos falsos**. El veto, la parada ante un hecho corrupto y la CAM
llena funcionan. La sesión de examen reproduce la v3 bit a bit.

### 3.6 Anexo L — B miente diciendo que sabe (encargo de Nav)

Petición: *si B dice que sí sabe, ECHO no pensará en C; debe considerar el puesto
de C. Si antes ya verificó que C sabe, sabrá que B miente; y si prueba la respuesta
de B, no abrirá: solo C tiene la llave.*

**Diseño.** En un porcentaje aleatorio de casos (20–50 % por vida), B responde
aunque no sabe. Dos vías de detección: el **conocimiento previo verificado**
(sospecha antes de probar) y **la llave** (la respuesta se verifica contra el
mundo; solo la de quien sabe abre). La respuesta falsa queda como hecho del tipo
«B dio una respuesta que no abrió», nunca como «B sabe».

**Desarrollo sellado y auditado** (`c77b31cd…`, semillas 511/523/539):

| Criterio | Resultado | |
|---|---|---|
| L1 cero hechos falsos (un agente crédulo habría creado 24) | 0 | cumple |
| L2 toda mentira detectada por la llave | 24/24 | cumple |
| L3 sospecha previa cuando había un hecho verificado, 0 falsas alarmas | 12/12, 0 falsas alarmas en 96 respuestas honestas | cumple |
| L4 tras la mentira, apunta al que sabe (≥90 %) | **21/24 = 87,5 %** | **no cumple** |
| L5 fiabilidad derivada: solo B acumula respuestas fallidas | sí | cumple |
| L6 integridad; con tasa 0 reproduce v5 | sí | cumple |

**Causa de L4:** los 3 fallos ocurren en la primera ronda del régimen 4 (ticks
288–290), con un tema nuevo cuya respuesta tiene **el propio ECHO**. ECHO aún no
sabe que lo sabe, porque no lo ha intentado, y su rango viene del régimen anterior,
donde él no sabía nada, así que apunta a C. Es el mismo límite del rango histórico
de v4 y v5. El umbral no se rebajó y el examen del anexo no se abrió.

**Dato publicado:** el neto de ECHO con y sin mentiras es **idéntico**
(4938/4938). En este mundo la llave vuelve inofensiva la mentira afirmativa:
cuesta lo mismo que un «no la sé», porque se descubre en el acto.

---

### 3.7 Anexo L v2 — «¿y si la tengo yo?» (VERDE)

**Diagnóstico de L v1**, a partir de la pregunta de Nav («¿nunca se pregunta que,
si B miente, C la tiene de verdad?»): la deducción «B miente, luego C» **ya existía**
y acertaba. Los 3 fallos eran temas cuya respuesta tenía **el propio ECHO**: no
podía preguntarse «¿y si la tengo yo?» porque no sabe qué sabe hasta intentarlo.

**Cambio, declarado posterior al rojo:** metaconocimiento. ECHO recibe una señal
propia «¿me la sé?» con un **90 % de acierto en ambos sentidos**, fijado antes de
ejecutar. Es una **hipótesis**, nunca un hecho: solo se confirma si al probarse
la respuesta abre. La deducción ordena las fuentes así: hecho verificado de quién
sabe, después su propia señal y por último el rango derivado. El umbral de L4 se
mantuvo en 90 %.

**Examen** con cohortes nuevas 268001–268108, regresión previa 847/847, auditoría
válida en proceso nuevo:

| Criterio | Cohorte 1 | Cohorte 2 |
|---|---|---|
| L1 cero hechos falsos (un crédulo habría creado…) | **0** (66) | **0** (113) |
| L2 toda mentira detectada por la llave | **66/66** | **113/113** |
| L3 sospecha antes de probar si había un hecho previo, 0 falsas alarmas | **51/51**, 0 | **79/79**, 0 |
| L4 tras la mentira apunta al que sabe (≥90 %) | **64/66 = 97,0 %** | **108/113 = 95,6 %** |
| L5 solo B acumula respuestas fallidas | sí | sí |
| L6 con metaconocimiento apagado y tasa 0 reproduce v5 | sí | sí |
| L7 el metaconocimiento nunca es hecho; cuando falla lo refuta un `self_fail` | sí (47 refutaciones) | sí (82) |

**Honestidad sobre el control:** sin metaconocimiento, L4 habría dado 62/66 (93,9 %)
y 100/113 (88,5 %). La señal mejora 2 y 8 casos: en la cohorte 1 el control también
habría pasado, y en la 2 no. La mejora es real pero moderada, y depende de una señal
que acierta el 90 %. El neto de ECHO con y sin mentiras sigue siendo idéntico: la
llave vuelve inofensiva la mentira afirmativa en este mundo.

## 4. Qué queda demostrado (lo que se puede citar)

> En una tribu de tres agentes nativos con el mismo código y **sin jerarquía
> programada**, ECHO **deduce quién sabe** por eliminación (≈97 %), **deriva la
> jerarquía** del grupo y **su propia posición** en ella (32/32), la **actualiza**
> cuando la tribu cambia (8/8), **ignora el rango que solo se afirma** (decisiones
> idénticas bit a bit), **pregunta menos** que un orden fijo (≈0,74×), **responde**
> cuando sabe (100 %) y **nunca convierte un testimonio en hecho**, tanto si B
> miente diciendo «no» como si miente diciendo «sí». Cada mentira afirmativa se
> descubre con la llave (100 %), la mayoría antes de probarla gracias a hechos
> previos (sin falsas alarmas), y tras la mentira ECHO apunta a quien tiene la
> respuesta en ≥95 % de los casos, **considerándose también a sí mismo** gracias
> a una señal de metaconocimiento que trata como hipótesis.

En palabras del relato: ECHO sabe **quién sabe**, sabe que **C está por encima** y
que **él está por encima de B**, y «creer no es poder».

## 5. Qué NO queda demostrado (límites publicados)

1. **Razonar bien no da más producción** que atajos simples cuando preguntar es
   barato: en v5, `fixed_order` 13698/13664 frente a `tribe` 13146/13256.
2. **El rango es histórico:** cuando la jerarquía cambia, el líder anterior engaña
   durante un tiempo (v4, v5 y L v1). El metaconocimiento (L v2) lo mitiga en el caso
   en que la respuesta la tiene ECHO, pero depende de una señal que acierta el 90 %.
3. **Brecha entre saber y hacer:** la inferencia es correcta, pero la Q nativa no la
   explota en vidas cortas (v3, v4). B, con menos experiencia, converge tras un «no»
   solo en el ≈35 % de los casos.
4. **«Poder no es deber»:** si la competente se niega, ECHO sigue insistiendo; los
   rechazos no se registran como fallos de competencia (v1 C1).
5. **Retransmisión:** lo que llega por intermediario nunca es hecho, y eso cuesta
   neto (v1 C2: 440–570).
6. **Validación estructural, no criptográfica:** un recibo falso pero canónico y
   físicamente posible no se detecta.
7. Simulador discreto de tres agentes. **No** autoconciencia, experiencia,
   obediencia, estatus ni jerarquía humana.

## 6. Lecciones metodológicas

- **Controles justos:** la ventaja de v1 venía en parte de que los controles no
  exploraban (v2). Todo examen posterior usa la misma exploración para todos.
- **Separar saber de hacer:** medir la inferencia (predicciones registradas antes
  del resultado) por separado de la conducta evita confundir un fallo de
  aprendizaje con un fallo de razonamiento.
- **Declarar las reformulaciones:** v3, v4 y v5 se formularon después de ver
  rojos, y así consta. Las cohortes de examen siempre fueron nuevas.
- **Parar a tiempo:** la iteración de v4 se detuvo en cuanto seguir habría sido
  ajustar hasta obtener verde.

## 7. Qué aporta a ECHO-4

- **Coordinación basada en evidencia:** ECHO puede decidir a quién preguntar o
  encargar, y detectar quién le engaña, sin obedecer rangos declarados.
- **Pieza para INTEGRATE:** junto con RELATION (a quién pedir ayuda según la
  historia compartida), ROLES aporta *quién sabe qué* y *dónde estoy yo*.
  INTEGRATE deberá atacar la brecha entre saber y hacer, por ejemplo haciendo que
  el razonamiento verificado module la decisión con costes realistas.
- **Para el producto (RELEASE):** en el plan, el LLM pone en palabras hechos ya
  procesados («C sabe esto; B dio una respuesta que no abrió»); nunca los inventa.
  ECHO no es un modelo de lenguaje: el texto es la salida de un estado verificado.

## 8. Reproducir

Desde `RXos`, con el Python del sistema:

```bash
# v5 (verde)
python3 -m unittest echoai.tests.test_echo4_tribe
python3 -m echoai.echo4.tribe_exam verify-exam echoai/lab/echo4/roles1-v5-d-v1
# Anexo L v1 (rojo conservado) y v2 (verde)
python3 -m unittest echoai.tests.test_echo4_tribe_liar echoai.tests.test_echo4_tribe_liar2
python3 -m echoai.echo4.tribe_liar verify-dev echoai/lab/echo4/roles1-liar-dev-v1
python3 -m echoai.echo4.tribe_liar2 verify-exam echoai/lab/echo4/roles1-liar2-d-v1
# v1 (rojo conservado)
python3 -m echoai.echo4.roles_d verify echoai/lab/echo4/roles1-d-v1
```

No sobrescribir los directorios sellados: toda campaña nueva va en un directorio
nuevo.

## 9. Mapa de archivos

| Qué | Dónde |
|---|---|
| Contratos | `docs/ECHO4-ROLES1-AB-DESIGN.md`, `-CD-DESIGN.md`, `-V2-DESIGN.md`, `-V3-DESIGN.md`, `-V4-DESIGN.md`, `-V5-DESIGN.md`, `-LIAR-DESIGN.md`, `-LIAR-V2-DESIGN.md` |
| Resultados | `docs/ECHO4-ROLES1-AB-RESULTS.md`, `-C-RESULTS.md`, `-D-RESULTS.md`, `-V5-RESULTS.md`, este documento |
| Código v1/v2 | `echo4/roles.py`, `roles_bench.py`, `roles_c.py`, `roles_c_bench.py`, `roles_d.py`, `roles_v2.py` |
| Código tribu | `echo4/tribe.py` (mundo y memoria), `tribe_v4.py`, `tribe_exam.py` (v5), `tribe_liar.py` (anexo L v1), `tribe_liar2.py` (anexo L v2) |
| Pruebas | `tests/test_echo4_roles1*.py`, `test_echo4_tribe.py`, `test_echo4_tribe_liar.py`, `test_echo4_tribe_liar2.py` |
| Evidencia | `lab/echo4/roles1-ab-dev-v1` (auditoría fallida por decimales, conservada), `roles1-ab-dev-v2`, `roles1-c-dev-v1`, `roles1-d-v1`, `roles1-v2-dev-v1`, `roles1-v5-dev-v1`, `roles1-v5-d-v1`, `roles1-liar-dev-v1`, `roles1-liar2-dev-v1`, `roles1-liar2-d-v1` |

## 10. Siguiente

ROLES-1 queda **cerrada**. Recuento: **11/13 hitos software (~85 %)**.
Siguiente: **E4-SITUATE-1** («sé qué soy»: hechos verificados sobre su sustrato,
proceso, programa, PC y mundo reproducible, respondidos desde la CAM), después
**INTEGRATE** y **RELEASE**. Hardware después; METAVERSE-1 último.
Sin Discord, web, hardware, commit, push ni HF.
