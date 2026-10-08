# ECHO-4.5 — capacidad asociativa, transferencia y siguiente arquitectura

2 de octubre de 2026. Investigación local sobre el candidato V2
`87490fe0e53447a6ef4e2a1158ddf7051011c4670635fa286cb7bcea40bd6b13`.
La inspección no modifica ese candidato ni sus resultados. S6 sigue aplazado
según la decisión vigente. Se implementó y ejecutó CAP-STRESS-1; el actor ARC
con coste diferido y el DSL tipado de este documento son diseños pendientes.

La capacidad adicional tiene utilidad medible cuando hay muchas asociaciones
distintas: a 16.384 contextos, el banco de 500k recupera el 99,814 % y el de
65k el 46,885 %. El candidato ARC actual solamente contiene 492 asociaciones
rasgo–primitiva. Sus limitaciones observadas están en la representación, la
aplicabilidad de recuerdos y la búsqueda. La contribución causal de cada una
necesita las ablaciones descritas aquí.

**1. Diagnóstico matemático y arquitectónico**

Las «500.000 neuronas» de esta comparación son posiciones uint8 de
`SparsePrimitiveGuide`, en [kenyon_capacity.py](../seed/kenyon_capacity.py).
No son las células LIF, CAM ni STDP del núcleo NEXUS-0. Este banco no tiene
fase, spikes, conexiones recurrentes ni aprendizaje de una representación
mediante gradientes. Recibe rasgos fijos de las demostraciones y aprende
contadores que ordenan familias de primitivas.

Para cada rasgo f y nombre de primitiva a, ocho direcciones se obtienen de
BLAKE2b. Se actualizan y consultan así:

```text
h_j(f,a) = fragmento_j(BLAKE2b(f + NUL + a)) mod M, j=1…8
w[h_j(f,a)] ← min(255, w[h_j(f,a)] + 1)
s(a | x) = Σ_{f ∈ F(x)} Σ_{j=1}^8 w[h_j(f,a)]
hint(a | x) = 0,05 + 0,55 × s(a | x)/max_b s(b | x)
```

La última expresión es una pista de ordenación, sin calibración probabilística.
Los nombres repetidos de un programa se reducen a un conjunto. Los argumentos,
el orden y la estructura de ese programa no se aprenden en el banco.

Sean D las claves distintas `(rasgo,primitiva)`, k=8 y M las posiciones. Bajo
la aproximación de hashes uniformes independientes:

\[
\lambda=\frac{kD}{M},\qquad
\mathbb E[\text{ocupadas}]=M\left[1-\left(1-\frac1M\right)^{kD}\right]
\simeq M(1-e^{-\lambda}).
\]

La señal directa de una asociación permanece con k fijo; aumentar M reduce
interferencias. No hay un mecanismo que reparta su peso entre todas las
posiciones y diluya automáticamente esa señal. Las dependencias entre rasgos,
los pesos desiguales y la saturación impiden convertir esta aproximación en
una garantía de exactitud.

La [inspección reproducible](../seed/capacity_forensics.py) de los artefactos
de V2 dio 84 recibos, 66 programas únicos, 118 rasgos, 492 claves distintas,
769 actualizaciones de claves y masa total de contadores 6.152:

| Medición del candidato ARC | 65.536 | 500.000 |
|---|---:|---:|
| Posiciones no nulas | 3.818 | 3.917 |
| Ocupación | 5,8258 % | 0,7834 % |
| Posiciones compartidas por claves distintas | 116 | 19 |
| Contador máximo | 10 | 10 |
| Contadores saturados en 255 | 0 | 0 |
| Bytes del vector | 65.536 | 500.000 |

En esta población, λ vale aproximadamente 0,0601 y 0,00787. La memoria de
65k está poco ocupada. El tamaño mayor reduce colisiones, pero la primera
primitiva sugerida coincide en 127/128 tareas de desarrollo y 122/128 del
seguimiento. Las predicciones finales coinciden en las 128 de cada cohorte.
El orden completo sí cambia: los diez primeros nombres solo coinciden en una
tarea de cada cohorte. También cambian las aplicaciones primitivas en 52/128
y 56/128 tareas, respectivamente. La igualdad de aciertos no significa que
las trayectorias o todos sus costes sean idénticos.

Hay cuatro restricciones adicionales comprobadas en las fuentes:

- El encoder intersecta rasgos discretizados de todas las demostraciones.
  Resume tamaños, histogramas, objetos y acuerdos geométricos. Tres firmas
  idénticas de rasgos tienen conjuntos de etiquetas diferentes ya antes del
  hashing; ampliar el vector no recupera distinciones descartadas por el encoder.
- La guía reconoce 84 familias. `objects_to_row`, `marker_recolor`,
  `recolor_by_size` y `connect_color` no están en su vocabulario. V2 da prioridad
  fija a esas relaciones durante la expansión; la guía solo cambia parte del
  orden dentro del presupuesto. `Library.step_cost` no se consulta en V2.
- El diario ARC conserva programas concretos y su prueba, con colores y
  parámetros literales. `candidates` ordena por solapamiento de rasgos,
  confianza y longitud. No vuelve a ligar variables de color/objeto al nuevo
  problema. Las pruebas históricas siguen siendo válidas en su contexto;
  su utilidad fuera de él no está demostrada.
- La política del diario ARC todavía no llama a `choose/begin/charge/mature`.
  Guarda trabajo medido, pero no aprende a decidir en qué recuerdo gastar
  ni cuándo abandonar una rama.

El embudo de memoria aclara la transferencia. En cada cohorte se recuperaron
3.072 programas (24 por tarea). En desarrollo eran elegibles 2.516; 556 se
excluyeron por operaciones/argumentos no permitidos. En seguimiento eran
elegibles 2.528 y se excluyeron 544. Ninguno se excluyó por profundidad. Cero
recuerdos originaron un programa que pasara todas las demostraciones actuales.
Los recuperados no equivalen a 3.072 ejecuciones completas. Véanse
[datos forenses](../lab/seed/capacity-forensics-20261002/result.json) y
[elegibilidad](../lab/seed/capacity-forensics-20261002/memory-eligibility.json).

El seguimiento tiene 128 tareas únicas: 64 ARC-1 y 64 ARC-2. El empate 1/128
se descompone en **0/64 ARC-1 y 1/64 ARC-2**. No son 128 casos de ARC-1. En
127/128 no se encontró siquiera un programa compatible con todas las
demostraciones. La muestra es disjunta de este ajuste y sus 84 tareas de
adquisición, pero procede de entrenamiento público; no se declara examen
secreto ni ausencia de exposición en investigaciones antiguas.

Esto hace prioritaria la búsqueda de programas y su representación. No prueba
que el DSL sea incapaz de expresar la solución: una búsqueda limitada a 2.000
intentos, profundidad 4 y beam 12 puede no encontrar un programa expresable.
Hay que separar cobertura del lenguaje de capacidad de búsqueda.

El 71,04 % sintético corresponde a 64 instancias nuevas de **cuatro familias
conocidas**, con reglas aprendidas en ocho ejemplos. Recuperar exactamente
esas reglas ahorra trabajo: 81.168 → 23.504 aplicaciones. Incluyendo las 10.417
aplicaciones de búsqueda de adquisición, el ahorro baja al 58,21 %; todavía
faltan ahí encoder y custodia de recibos. Esto acredita reutilización bajo ese
contrato, sin demostrar optimalidad ni adquisición de familias nuevas.
Además, el control sintético posterior de V2 sin memoria obtuvo 63/64; con
memoria, 64/64. Se conserva esa diferencia en el registro.

| Hipótesis | Evaluación actual | Contraste que falta |
|---|---|---|
| Más posiciones diluyen la señal | No describe la actualización implementada; el incremento directo se mantiene | Comparar margen contra un diccionario exacto y carga creciente |
| La guía memoriza píxeles puntuales | No: guarda asociaciones de rasgos resumidos; el diario sí guarda programas y demostraciones concretos | Rasgos por roles y programas con variables frente a literales |
| ARC no estresa almacenamiento | Apoyado por baja ocupación y por CAP-STRESS-1 | Medir crecimiento de un repertorio útil, sin datos duplicados |
| Falta de 3E explica el estancamiento | Ausencia comprobada; causalidad sobre acierto pendiente | Política fija vs adaptativa con idéntico DSL y presupuesto |
| El DSL solo opera sobre píxeles | Incorrecto: ya tiene objetos, selecciones, simetrías y cuatro operaciones relacionales | Grafo tipado y composición frente a macros actuales |
| El lenguaje es insuficiente | Posible, sin demostrar con la búsqueda limitada | Control de cobertura con programas testigo y presupuesto diagnóstico separado |

El análisis de hashing puede inspirarse en [Weinberger et al., 2009](https://arxiv.org/abs/0902.2206).
ECHO suma contadores compartidos sin signos; no coincide con todas las variantes
de ese artículo. Tampoco implementa Count-Min, que consulta un mínimo entre
filas: no se le atribuyen sus cotas formales. Véase
[Cormode y Muthukrishnan, 2005](https://www.cs.helsinki.fi/u/jilu/paper/countMin.pdf).
Las capacidades teóricas de redes Hopfield tampoco son aplicables a este banco.

**2. Banco controlado de límite de capacidad: diseño y resultado**

CAP-STRESS-1 se fijó antes de medir y está [prerregistrado](ECHO45-ASSOCIATIVE-STRESS-DESIGN.md).
El [código](../seed/associative_stress.py) reutiliza el hashing y la consulta de
la guía real. Inyecta rasgos ya codificados y reproduce el incremento uint8
positivo; no pasa por el encoder de rejillas ni por `observe` y su verificador.
Esta separación deliberada permite medir el almacenamiento sin atribuirle
capacidades del solver.

Se entrenan ocho rasgos distintos por contexto, 32 etiquetas equilibradas,
dos observaciones por asociación y cinco cargas acumulativas. Veinte semillas
46001–46020 fijan los datos sin buscar hashes favorables. Ambos tamaños ven
las mismas claves y consultas; el control es un diccionario exacto sin
colisiones. Cada carga tiene 512 consultas (256 en la menor), limpias o con
dos de ocho rasgos sustituidos por otros contextos. Se recuperan contextos
almacenados: no se mide generalización de reglas nuevas.

La carga primaria fijada fue 16.384 contextos, sin corrupción. Implica
131.072 asociaciones diferentes: λ=16 en 65k y λ=2,097152 en 500k. La señal
directa ideal por consulta es 8×8×2=128. Los umbrales previos fueron exactitud
500k ≥95 %, 65k ≤90 %, ventaja ≥5 puntos, intervalo pareado al 95 % por encima
de cero, test de signos unilateral p<0,01 y control exacto ≥99 %.

| Contextos almacenados | 65k, limpio | 500k, limpio | 65k, 25 % corrupción | 500k, 25 % corrupción |
|---|---:|---:|---:|---:|
| 256 | 100 % | 100 % | 100 % | 100 % |
| 1.024 | 100 % | 100 % | 99,94 % | 100 % |
| 4.096 | 96,09 % | 100 % | 78,80 % | 100 % |
| **16.384** | **46,88 %** | **99,81 %** | **29,83 %** | **95,77 %** |
| 65.536 | 17,08 % | 73,00 % | 11,12 % | 49,68 % |

**Resultado primario: VERDE de recuperación asociativa.** Ventaja media
52,9297 puntos; intervalo bootstrap pareado por semilla [52,0313; 53,7793]
puntos, 10.000 remuestreos; p unilateral de signos = 9,5367×10⁻⁷. Son veinte
réplicas, no 10.240 consultas independientes. El diccionario exacto obtuvo
100 % en todas las condiciones. Las curvas secundarias son descriptivas.

Se realizaron 92.160 consultas por brazo, más la reproducción completa de
las dos semillas fijadas para auditoría en procesos nuevos. Ambas reproducciones
coinciden en todas las métricas deterministas; CPU/RSS se excluyen de esa
igualdad. Esta auditoría comprueba reproducción con el mismo código y no
sustituye una implementación independiente. Ningún contador llegó a 255 en
ninguna carga. La pérdida de exactitud procede de interferencia entre
direcciones, sin clipping numérico observado.

En la condición primaria todas las posiciones de 65k están ocupadas; en 500k
la media es 438.565,8. La guía utiliza vectores de 64 KiB y 488,28 KiB; el RSS
máximo del worker fue 137,06 MiB e incluye ambos bancos, el control exacto y
el intérprete. La CPU media de ajuste hasta 65.536 contextos fue 3,19 s y
3,32 s; la consulta acumulada de todas las semillas y condiciones fue 109,37 s
y 116,89 s. No se deduce significancia de esas diferencias temporales: el
orden de bancos fue fijo y CPU/cachés no constituyen un ensayo de latencia.

![Curvas de capacidad medidas](../lab/seed/associative-stress-20261002/capacity-curves.png)

El último punto observado con recuperación limpia ≥95 % es 4.096 contextos
para 65k y 16.384 para 500k. El siguiente punto cae por debajo del umbral en
ambos. Esto localiza un cruce en la malla experimental; no estima un máximo
universal ni demuestra monotonicidad entre puntos. Se necesitaría un contrato
de búsqueda más fina para localizar C95 con incertidumbre.

Métricas conservadas: top-1, top-5, rango recíproco medio, margen de selección,
ocupación, saturación, error de score respecto al
diccionario, CPU y memoria. La corrupción de rasgos es pertinente; «ruido de
fase» exigiría otro modelo temporal. El número de posiciones no proporciona
un número equivalente de recuerdos completos ni de tareas ARC resolubles.

Una extensión para grafos requiere un encoder canónico declarado: generar
objetos con relaciones, permutar sus identificadores, relabelar colores y
trasladar escenas conservando roles; consultar la transformación asociada.
Se compararía hashing con un diccionario exacto que use el mismo encoder.
Si ambos fallan, el problema está antes del almacenamiento. Si solo falla
65k a mayor carga, hay evidencia de interferencia. Los grafos no vistos y las
composiciones de reglas se medirían aparte de la recuperación. Esa extensión
queda propuesta; no está incluida en el verde de CAP-STRESS-1.

Reproducción y artefactos:

```bash
# La raíz existente ya contiene el contrato y los resultados cerrados.
python3 -m seed.associative_stress run --root lab/seed/associative-stress-20261002
python3 -m seed.associative_stress audit --root lab/seed/associative-stress-20261002
python3 -m seed.associative_stress_report
# Para repetir todo desde cero, preparar otra raíz y conservar el mismo perfil.
```

[Perfil](../lab/seed/associative-stress-20261002/profile.json),
[resultado](../lab/seed/associative-stress-20261002/summary.json),
[auditoría](../lab/seed/associative-stress-20261002/audit.json),
[costes](../lab/seed/associative-stress-20261002/report.json) y
[gráfica SVG](../lab/seed/associative-stress-20261002/capacity-curves.svg).
Solo CPU local; ninguna llamada al LLM, entrenamiento GPU ni nueva partida S6.
El [recibo de cierre](../lab/seed/associative-stress-20261002/closure.json)
recalcula la diferencia primaria y el test de signos, comprueba las veinte
semillas, contrasta el incremento contra `observe` real con y sin saturación,
y verifica que las 217 fuentes originales y los cinco perfiles anteriores de
integración siguen intactos.

**3. Actor ARC con el ciclo de coste diferido de 3E**

En [village3.py](../seed/village3.py), `begin` abre una cuenta de consecuencias,
`charge` descuenta costes observados y `mature` actualiza la política tras un
horizonte de 64 episodios. `mature` no verifica programas ni certifica verdad.
`begin` tampoco asigna presupuesto por sí solo. El adaptador ARC necesita un
planificador de presupuesto y un verificador separados de esa contabilidad.

Se propone **ARC-3E-POLICY-1**, conservando los recibos inmutables y añadiendo
estado de política serializable: contexto por roles, acción elegida, recibo
consultado, prueba realmente conservada, presupuesto reservado, consumo real,
consecuencias pendientes, edad y esquema/versiones de la política. El actor
original usa cuatro acciones `(verificar, escribir)`; las acciones ARC siguientes
son una extensión declarada. Sus Q no pueden reutilizarse como si significaran
lo mismo. El código y las puertas originales de 3E siguen intactos.

| Operación | Diseño propuesto | Evidencia y límite |
|---|---|---|
| `choose` | Elegir entre reutilizar, volver a ligar variables, componer, ampliar búsqueda o abandonar una rama | Aplicabilidad por tipos/roles, historial contextual de verificación, coste estimado y exploración acotada; un score no aprueba un programa |
| `begin` | Reservar un bloque del presupuesto común y abrir el registro de crédito | Identificadores de tarea/hipótesis, contexto, acción, edad, hash de estado y prueba realmente presente |
| `charge` | Cargar cada operación ejecutada, tanto exitosa como fallida | Encoder, recuperación, aplicaciones, emparejamiento de objetos, verificación, escritura y consecuencias; nunca cobrar dos veces el mismo evento |
| `mature` | Incorporar retornos observados de decisiones con el mismo horizonte | Las decisiones pendientes permanecen censuradas; no se inventa una recompensa futura para vaciar la cola |

La selección puede comenzar con una tabla contextual discreta. Para cada
par `(esquema,contexto)`, una estimación suavizada de aplicabilidad es:

\[
\widehat p=\frac{1+n_{\mathrm{válido}}}{2+n_{\mathrm{válido}}+n_{\mathrm{inválido}}},
\qquad U(a,c)=V\widehat p(a,c)-\lambda\widehat C(a,c)
-\rho\widehat R(a,c)+\beta B(a,c).
\]

Aquí «válido» significa ajuste exacto a demostraciones disponibles, no acierto
en test. R representa regresiones observadas en validaciones permitidas y B
un bonus de exploración acotado. Estos son nuevos estimadores a calibrar en
desarrollo; no se rebautiza `trust` como probabilidad. La implementación local
puede comparar racionales mediante enteros o punto fijo, sin modificar los
invariantes numéricos del núcleo. La independencia requerida por una posterior
Beta exacta no se presupone para episodios correlacionados.

El planificador asignaría bloques pequeños, por ejemplo 32/128/512 unidades
de trabajo según incertidumbre, hasta agotar un total común. Son valores de
diseño, todavía sin seleccionar mediante resultados. Antes de medir se fija
qué es una unidad: aplicaciones primitivas y eventos tipados de coste con
coeficientes publicados; intentos, CPU y memoria también se reportan separados.
Dos brazos con 2.000 programas no necesariamente consumen la misma computación.
No se amplía el presupuesto de la política adaptativa para fabricar una ventaja.

El retorno debe conservar una prioridad explícita por resolver tareas: minimizar
solo coste premiaría abandonar siempre. Se compararía utilidad restringida por
retención de aciertos, con coste observado y recompensas verificables únicamente
en desarrollo. Si se utiliza una expresión escalar, su peso por éxito se fija
antes de medir y la puerta exige conservación por separado. No se acredita
«ahorro» contrafactual contra una ejecución basal que nunca ocurrió.

El esquema `mature` debe contar una unidad temporal inequívoca. Una primera
condición puede conservar H=64, definiendo un episodio como una tarea de
desarrollo completada y evaluando suficiente cola posterior para atribuir
reutilizaciones. Todas las políticas se comparan con la misma edad de recuerdos.
Esta definición es distinta de contar expansiones de búsqueda y debe fijarse
en contrato. Costes tardíos conservan el identificador original; un fallo
contextual reduce la utilidad de reutilizar ahí, sin borrar un recibo histórico
correcto en su contexto.

La verificación sucede antes de `remember`. Un programa que pasa los ejemplos
puede guardarse con alcance `verified_on_demonstrations`. La política aprende
si consultarlo merece su coste. Promover un candidato requiere su propio examen;
ni `mature` ni el éxito de un ejemplo cambian ese alcance.

```text
public ← demostraciones + entradas de test, sin respuestas de test
context ← roles y relaciones(public)
action ← policy.choose(context, learn=modo_desarrollo)
ticket ← scheduler.reserve(action, presupuesto_restante)
policy.begin(ticket, context, action, coste_inicial_observado, episodio)
candidate ← retrieve_rebind_or_search(action, ticket)
policy.charge(ticket, coste_real_de_operaciones)
if verifier.matches_all_demonstrations(candidate):
    diary.remember(candidate, proof, scope="demonstrations")
policy.mature(episodio)  # utilidad con consecuencias observadas
```

Durante evaluación se congela la política entre tareas. Puede haber búsqueda
interna y memoria de trabajo con las demostraciones de cada problema. Ninguna
etiqueta de test actualiza la guía, el diario, el selector o su confianza. El
aprendizaje continuo entre tareas necesita otro protocolo prequential declarado.

Este enfoque está relacionado con selección de cómputos bajo presupuesto,
estudiada por [Callaway et al., 2018](https://arxiv.org/abs/1711.06892). El
artículo no demuestra que estos coeficientes o esta adaptación funcionen en ECHO.

**4. DSL relacional: cinco operaciones tipadas y evaluación**

La ampliación propuesta es **REL-DSL-1**. Se conservan las primitivas geométricas
existentes como operaciones locales. Lo nuevo es un intermediario tipado que
permita componer objetos, relaciones y variables. Las cinco operaciones no
contienen un solver oculto; sus alternativas y costes deben ser enumerables.

| Operación propuesta | Tipo y función | Semántica acotada |
|---|---|---|
| `OBJECTS(grid, segmentation)` | `Grid → Scene` con objetos, forma, caja, color y anclas relativas | Hipótesis explícitas de fondo, conectividad 4/8 y agrupación por color; número de variantes y objetos limitado |
| `RELATE(scene, relation)` | `Scene → RelationSet`: contiene, toca, alinea, misma forma, simetría, proximidad | Métrica, dirección y normalización declaradas; vecindad no depende de IDs ni del orden del recorrido |
| `BIND(pattern, scene, relations)` | `Pattern × Scene → Bindings` para roles y correspondencias | Restricciones y cuantificadores acotados; empates se mantienen como hipótesis o producen ambigüedad, nunca una elección por etiqueta oculta |
| `MAP_OBJECTS(bindings, subprogram)` | `Bindings × Program → Edits` | Aplica composición local a cada objeto/rol, con traslación relativa; expansiones y coste de cada instancia visibles |
| `RENDER(scene, edits, frame)` | `Scene × Edits → Grid` | Marco original, caja de objetos o dimensión derivada por regla explícita; colisiones y superposición con política fija, por ejemplo rechazo |

Ejemplo de sintaxis ilustrativa, todavía no implementada:

```text
scene = OBJECTS(input, connectivity=4, background=dominant_border)
rels = RELATE(scene, [contains, aligned, same_shape])
roles = BIND("source inside frame; targets are isolated markers", scene, rels)
edits = MAP_OBJECTS(roles.targets,
                   copy_translate(roles.source,
                                  anchor(target) - anchor(roles.source)))
output = RENDER(scene, edits, frame=original, overlap=reject)
```

La regla cambia de colores, coordenadas o número de destinos sin cambiar de
programa. Los roles se infieren de las demostraciones; `BIND` no recibe una
descripción correcta escrita por un humano para cada tarea evaluada. Los
constructores del patrón también forman parte de la búsqueda medida.

El diario puede guardar un esquema parametrizado y las restricciones que
funcionaron. La siguiente tarea vuelve a ligar sus variables y verifica la
instanciación. La guía necesita rasgos relacionales y vocabulario de estas
producciones; ampliar posiciones sin añadir esas conexiones repetiría el
problema actual. La adquisición de bibliotecas y la búsqueda guiada tienen
precedentes como [DreamCoder, Ellis et al.](https://arxiv.org/abs/2006.08381);
su resultado no se traslada automáticamente a este DSL o a ARC.

La ruta de implementación queda fijada así:

1. **Instrumentar aplicabilidad y cobertura.** Separar recuperado, permitido,
   instanciado, ejecutado y verificado; registrar argumentos y vocabulario.
   Un control diagnóstico con más búsqueda en desarrollo identifica soluciones
   que ya expresa el DSL. Su presupuesto extra no cuenta como ventaja del agente.
2. **Implementar roles y composición tipada**, con coste de segmentación,
   emparejamiento y render incluido. Pruebas de equivarianza por traslación,
   permutación de color/IDs, oclusión declarada y casos ambiguos. Retener exactitud
   de familias antiguas y medir combinaciones nuevas de roles/operaciones.
3. **Integrar ARC-3E-POLICY-1**, persistiendo también crédito y decisiones
   pendientes. Pruebas de reanudación exacta, costes tardíos, retirada causal,
   rechazo de evidencia alterada y aislamiento de las etiquetas de examen.
4. **Comparación factorial**: DSL antiguo/nuevo × política fija/adaptativa,
   seguida de guía apagada/65k/500k con el mismo encoder y datos de ajuste.
   Igual trabajo total, mismas semillas, etiquetas de resultados fuera del actor.
   Se registra acierto exacto, regresiones por tarea, CPU, memoria, programas
   encontrados, aplicabilidad, amplitud/profundidad y cobertura de familias.
5. **Seguimiento nuevo** con cohortes y criterios congelados antes de correr.
   El seguimiento anterior ya orientó el diseño; no certificará su confirmación.
   Reservar familias/composiciones además de separar IDs. Cualquier resultado
   negativo se publica, sin mover umbrales ni seleccionar el mejor contraste.

Puertas: verde de sintaxis y persistencia exige sus propiedades y replays;
verde de política exige utilidad atribuible a decisiones con coste diferido;
verde relacional exige transferencia a combinaciones fuera del ajuste;
verde de guía ARC exige ventaja sobre el mismo candidato sin guía y sobre el
banco menor según el contrato futuro. La mejora global exige aciertos nuevos,
retención y costes permitidos en la confirmación. Vistas y consistencia conservan
sus propias ablaciones pendientes. CAP-STRESS-1 cierra únicamente la cuestión
de capacidad del backend en esta distribución. **ECHO-4.5 sigue abierto; S6 no
se reabre ni se declara verde con este resultado.**
