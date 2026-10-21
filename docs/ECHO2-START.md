# ECHO-2 — arranque incremental, 2026-09-09

Nav autoriza empezar implementación por tajos y fija como destino el
**AKD1500 M.2**. Las notas de rol «Codex no pica» de NOW son históricas.
El mapa funcional de ECHO-2: VITA-1 →
FOOD-1 → SURV-1 → SHIFT-S; escala y herencia después.

## Puerta y primer cambio

XFER-1 ejecutado en este árbol: `green=true`, 51/51 mutantes rechazados.
Esto verifica su banco actual; no certifica robótica ni hardware.

Primer incremento: `QTable.update(..., terminal=True)`, opt-in.
En una transición terminal, `delta = r - Q[s,a]`: el estado de
renacimiento no aporta valor futuro. Las trazas reciben la última
consecuencia y se vacían, evitando crédito entre vidas. Q y los restos
enteros de CREDIT-1 persisten. Una recompensa negativa por sí sola no
marca el episodio como terminal. Las llamadas existentes conservan su
cálculo anterior.

Pruebas: recompensa terminal con sucesor valioso, modos normal/restos/
trazas/cuatro acciones, crédito al camino anterior y aislamiento de la
siguiente vida, conservación de restos y recompensa negativa no terminal.

Validación de esta entrega:

- Q-table: 7/7; léxico, CREDIT-1 y trazas: 22/22.
- Suite completa: 488 pruebas ejecutadas, un fallo esperado. Primera
  pasada con 12 errores y un fallo: cuatro referencias al léxico movido,
  ocho pruebas de sockets bloqueadas por sandbox y una comparación de
  informes interferida por otro banco concurrente. Todos esos casos
  pasan al repetirlos tras corregir la ruta, permitir sockets y ejecutar
  OPEN-1 aislado. No se presenta la primera pasada como verde.
- Anillo: `policy_after=[-12,5,0]`, `novel_approach_return=80`,
  `surprise_known=1`, hechos falsos/destrucciones/llamadas al córtex = 0.

Se corrige además `tools/gen_lex.py` para leer la tabla C trasladada a
`legacy/kernel-navi/wsp_lex.c`; el léxico generado conserva su contenido.
Los bancos regeneran sus informes habituales en `lab/`. Ejecutarlos en
serie cuando haya pruebas que comprueben bytes y mtime de esos informes.

**Estado al terminar el primer incremento (superado abajo):** faltaba conectar este contrato al loop,
añadir `H` en Agent, reloj del entorno, terminalidad y renacimiento con
Q/T/CAM conservados. Después, observación por bandas de H opt-in (sin
convertir E en almacén fisiológico), alimento/veneno y el banco de 50
vidas frente a reset. No afirmar aprendizaje de supervivencia hasta medir
`median(lifespan_persist) > median(lifespan_reset)` en varias semillas.

## Segundo incremento: VITA-1, FOOD-1 y SURV-1

Nav autoriza 2–3 fases por sesión, con consumo acotado. Implementación
en `loop.py`, `encoder.py`, `vita1.py`, `food1.py`; banco `echo2.py` y
pruebas `tests/test_echo2.py`. Se conserva el mismo Agent, gate, CAM y Q/T.

### VITA-1

`Agent(env=VitalEnv(world), initial_h=16, ask=False)` activa supervivencia.
Sin `initial_h`, el agente no tiene registro `H` y mantiene el protocolo
anterior. El entorno calcula, en cada acción, incluida espera:

```
H_next = clip(H - drain + nutrition, 0, 127)
terminal = (H_next == 0)
```

El consumo y el desgaste pertenecen al mismo paso: comer con H=1 puede
salvar esa vida. El registro H vive en Agent, no en el entorno ni en E.
El encoder observa cuatro bandas viables de H mediante U=0/30/60/90;
H=0 observa U=100. No cambia ningún otro byte. Esta cuantización pierde
el valor exacto de H: no se afirma que T prediga fisiología exacta.

El paso terminal paga −16, actualiza Q sin valor futuro y registra en T
el sucesor físico terminal, nunca el renacimiento. Se limpian trazas y
contexto temporal; actuar muerto produce error antes de modificar nada.
`run(n)` se detiene al morir. `respawn()` sólo acepta una vida terminal,
resetea cuerpo/H y conserva CAM/Q/T, restos y PatternMemory. El primer
paso de la nueva vida no forma un patrón con la vida anterior.

El diario WSP existente conserva sus 22 claves; U permite leer la banda,
pero aún no hay visualización explícita de H/vida/muerte en la placa.
No se añade otro thought-bus. Córtex y planner están deshabilitados para
este primer contrato de supervivencia.

### FOOD-1

`FoodEnv` extiende el objeto transportable de OBJ-1. El movimiento y el
acoplamiento se reutilizan. `approach` con el objeto en mano lo consume
sin mover el cuerpo; desaparece y no puede consumirse dos veces. La mesa
de entrega deja de pagar en este entorno. Cada renacimiento repone un
objeto. Nutrición +24 paga +16, −24 paga −16 y cero paga cero; no hay
premio por estar vivo ni política `if hunger: eat`.

Prueba local: 32 vidas de entrenamiento con el objeto ya en mano y un
paso greedy de examen, en mundos separados de alimento/veneno/inerte:

| Mundo | Q antes del examen | Acción | H antes → después |
|---|---|---|---|
| alimento | [15,10,13] | approach; consume | 8 → 31 |
| veneno | [-7,-3,-4] | avoid; no consume | 8 → 7 |
| inerte | [0,0,0] | wait; no consume | 8 → 7 |

Alimento y veneno tienen la misma apariencia WSP; el control mide
aprendizaje por consecuencias en cada mundo. **No demuestra distinguir
dos objetos visualmente idénticos mezclados ni transferencia entre ellos.**
La prueba local tampoco demuestra navegación: ésa se mide en SURV-1.

### SURV-1

50 vidas por brazo y semilla, desde START normal del cubo. Un brazo
conserva Q/T; el control las reinicia después de cada muerte, conservando
CAM. Mismo H inicial 16, desgaste 1, objeto finito +24 y secuencia de
fases de exploración por vida. Las semillas inicializan esas fases;
no generan mapas. No hay curriculum, teleport al objeto ni selección
de acciones en el harness de supervivencia.

| Semilla | Mediana conserva Q/T | Mediana reinicia Q/T |
|---|---|---|
| 17 | 28 | 16 |
| 101 | 40 | 16 |
| 20260903 | 40 | 16 |

El 28 es la mediana aritmética de una muestra par de vidas de 16 y 40
turnos; no es una vida individual de 28. El techo físico es 40 turnos:
este mundo tiene una sola ración. Control de nutrición cero: 16/16.
Se publican las 50 vidas de cada brazo, muertes, consumos, fases,
recompensas, ocupación CAM y contadores en `lab/echo2_report.json`.

`green()` recalcula medianas, comprueba vida finita y terminal, igualdad
de fases y ausencia de bonus +1, exige mejora en cada semilla y empate
en el control inerte. Los tests rechazan 11 alteraciones del informe y
un mutante ejecutado que añade +1 por turno vivo, aunque pueda aprender.
Es un certificado acotado del banco, no un registro criptográfico ni una
prueba de todos los posibles errores del runtime. El aprendizaje medido
puede explicarse por adquirir y consumir la ración antes del agotamiento;
no se atribuye una capacidad distinta al número de muertes por sí solo.

Reproducción desde `echoai/`:

```
PYTHONPATH=.. python3 -m unittest echoai.tests.test_echo2 echoai.tests.test_qtable
PYTHONPATH=.. python3 -m echoai.nexus0.echo2
PYTHONPATH=.. python3 -m echoai.tests.test_nexus0
```

Validación final del segundo incremento: **21 pruebas de ECHO-2/Q-table
pasan; 488 pruebas de regresión pasan con el único fallo esperado previo
de WALK-1** (253 s, sockets locales permitidos). No se ejecutaron bancos
que reescriben informes de ECHO-1 mientras corría esa suite.

Siguiente tras ese incremento: SHIFT-S (implementado abajo), comida renovable y
mejor observación, en experimentos separados. Integración AKD1500 sigue
pendiente; ninguno de estos números es una medida de la NPU.

## Tercer incremento: SHIFT-S y aclaración WALK-1

**WALK-1 es el control antiguo, deliberadamente rojo.** Sin restos,
`delta >> 2` descarta actualizaciones positivas menores que cuatro;
la cadena de valor se queda en `[13,8,4,0,…]` y el examen desde START
no alcanza el objetivo. `expectedFailure` conserva ese resultado.
CREDIT-1 mantiene los restos enteros y su prueba de navegación es verde.
ECHO-2 utiliza `remainder=True`; no vuelve al algoritmo de WALK-1.
No se elimina la comparación ni se cambia el default del anillo.

SHIFT-S vive en `nexus0/shifts.py`, sin cambios al núcleo ni a la física
de FOOD-1. Para cada semilla de SURV-1:

1. El mismo Agent aprende 50 vidas con alimento +24 desde START.
2. Tras renacer, se cambia únicamente `env.world.nutrition` a −24.
   Se verifican identidad y contenido de CAM/Q/T antes/después, además
   de igualdad de la observación. No hay repintado ni aviso semántico.
3. Otras 50 vidas en tres brazos: adaptativo con memoria conservada;
   copia del entrenado que desactiva sólo `Q.update` (Q y restos
   congelados, T/CAM siguen observando); agente nuevo en el mundo tóxico.
   START y fases de exploración son iguales por vida entre los brazos.

| Semilla | Turnos adaptativo / congelado / nuevo | Consumos de veneno adaptativo / congelado / nuevo |
|---|---|---|
| 17 | 653 / 232 / 752 | 25 / 48 / 9 |
| 101 | 694 / 278 / 747 | 21 / 46 / 15 |
| 20260903 | 706 / 260 / 733 | 14 / 47 / 14 |

En las últimas diez vidas, las medianas son 16/16/16 para el adaptativo
y 4/4/5 para el congelado. `green` exige menos consumos, más turnos
acumulados y mejor mediana final frente a la política congelada en cada
semilla. Recalcula esas cifras desde las vidas individuales y comprueba
que los restos y Q del control permanecen idénticos. Hay 13 alteraciones
de evidencia rechazadas por tests.

**Transferencia negativa frente al nuevo:** −99/−53/−27 turnos acumulados.
La costumbre aprendida perjudica inicialmente y requiere readaptación.
El certificado no exige ni afirma superioridad frente al agente nuevo.
Tampoco prueba adaptación perfecta: aún hay consumos de veneno y la
exploración continúa. Sin alimento sano, evitar el veneno sólo permite
llegar al agotamiento de 16 turnos; no hay supervivencia indefinida.

El banco no añade rutas, recetas de acciones, LLM, otro bus ni hardware.
Las huellas pickle son una auditoría local antes/después; no constituyen
un formato portable ni autentican un informe editado externamente.

```
PYTHONPATH=.. python3 -m echoai.nexus0.shifts
PYTHONPATH=.. python3 -m unittest echoai.tests.test_shifts
```

Informe independiente: `lab/echo2_shifts_report.json`. Siguiente problema
útil: acceso a alimento sano tras el cambio, con señales observables y
recursos renovables, antes de afirmar supervivencia sostenida.

## Puerta acordada para abrir ECHO-3

Al cerrar las cinco fases restantes de ECHO-2 se ejecutará **NEURAL-VIZ-1 /
CAPACITY-1**: comparar 256 frente a 512 LIF y probar Adaptive-LIF temporal
sólo si un benchmark lo justifica. El mismo tajo añadirá un visor de red en
árbol con capas, tipos, conexiones, potenciales y spikes sincronizados con
WSP/CAM/T/Q/gate/H. Será de sólo lectura y no creará un segundo thought-bus.
ECHO-3 quedará bloqueado hasta ese cierre verde; la cantidad de neuronas no
será el KPI, sino la mejora causal en representación y percepción.

### To-do condicionado a tener AKD1500 M.2

- [ ] Confirmar tarjeta M.2 2230 B+M Key, ranura host, alimentación y enlace PCIe/SPI.
- [ ] Registrar el runtime/SDK y compilar un modelo mínimo de referencia.
- [ ] Medir baseline: 256 LIF en CPU, precisión, latencia, memoria y spikes.
- [ ] Probar 512 LIF y tamaños mayores sólo si el modelo cabe.
- [ ] Medir la capacidad real del modelo compilado; no deducir neuronas desde GOPS.
- [ ] Comparar CPU/AKD1500 en la misma tarea, datos y host, incluido consumo.
- [ ] Verificar salida de rasgos/confianzas enteros hacia WSP; Q/T/CAM/VERIFY/gate siguen en CPU.
- [ ] Probar modelo ausente, salida errónea y acelerador desconectado: fallback seguro.
- [ ] Publicar `capacity1_report.json` y cerrar CAPACITY-1 sólo con mejora causal en examen nuevo.

Validación de SHIFT-S: **62 pruebas pasan**, con el único fallo esperado
de WALK-1. Incluyen SHIFT-S, ECHO-2, Q-table, WALK-1, CREDIT-1 y los
candados del banco principal. El runner SHIFT-S devuelve `green=true`.
No se repite la suite completa de 488: este incremento sólo añade el
harness, sus pruebas y documentación; no cambia el núcleo validado.

## Cuarto incremento: PATTERN-1

PATTERN-1 añade una memoria de familias perceptivas de capacidad fija. Su
entrada es una firma binaria de 16 bits. Durante aprendizaje recibe también
la consecuencia física; durante el examen congelado sólo recibe la firma.
Nunca recibe id de objeto, posición, vista, contexto, `kind`, WSP, CAM o Q.
Agrupa firmas a distancia Hamming ≤3 únicamente cuando sus consecuencias
son compatibles y devuelve familias anónimas `P0`, `P1`, …; una igualdad
visual cercana con consecuencia contraria se conserva como familia distinta.

El banco sintético entrena cuatro familias en varios objetos, vistas,
contextos y posiciones. Examina objetos, vistas, contextos y posiciones no
vistos. El resultado reproducible se escribe en
`lab/echo2_pattern1_report.json`:

```
PYTHONPATH=.. python3 -m echoai.nexus0.pattern1
PYTHONPATH=.. python3 -m unittest echoai.tests.test_pattern1
```

Cierre: 32/32 consecuencias y familias correctas frente a 0/32 de una
memoria de firma exacta; cuatro familias; el recurso y el imitador peligroso,
separados aunque sus prototipos estén a distancia 3; cero escrituras durante
el examen, cero descartes, cero córtex y `destroyed=0`.

Este resultado demuestra invariancia en rasgos binarios sintéticos, no visión
de objetos reales ni identidad persistente en vídeo. La posición y el
contexto existen sólo en el harness de puntuación. STREAM-1 deberá suministrar
un flujo externo y medir alias; la futura simulación 3D o un front-end
neuromórfico tendrá que producir las firmas antes de poder ampliar la
afirmación.

Validación de PATTERN-1: sus 10 pruebas y las 36 pruebas focales conjuntas
de ECHO-2/SHIFT-S/Q pasan. La suite histórica ejecuta 488 casos con el único
`expectedFailure` deliberado de WALK-1; los ocho casos que abren sockets
locales pasan por separado fuera del sandbox (22/22).

## Quinto incremento: STREAM-1

STREAM-1 consume transiciones externas con la única interfaz
`(wsp, action, next_wsp)`. El número de secuencia y el chunk son metadatos
del productor y no entran ni en WSP, ni en CAM/T. El procesador reutiliza el
asignador CAM y el predictor `World` existentes; no elige acciones, no mueve
Q y no crea un segundo predictor.

El banco recorre 48 chunks y 4.608 transiciones, por encima del techo `seq`
de 256. Los 32 paquetes locales se comparten entre todos los chunks,
con `domain=style=0` y `seq` local. En el flujo coherente
`DynamicAlias=0`. Un control cambia físicamente una transición en un chunk
sin cambiar su WSP: `DynamicAlias=1`, T registra el conflicto y pierde una
predicción; el sistema lo informa y no añade un id de chunk al paquete.

```
PYTHONPATH=.. python3 -m echoai.nexus0.stream1
PYTHONPATH=.. python3 -m unittest echoai.tests.test_stream1
```

El informe es `lab/echo2_stream1_report.json`. Este slice valida ingestión
de transiciones WSP externas y alias temporal. No es aún vídeo, cámara ni la
simulación 3D: esos productores podrán alimentar la misma interfaz cuando
existan.

## Sexto incremento: SLEEP-2

SLEEP-2 sólo se ejecuta fuera del paso rápido. Lee estados WSP de CAM y filas
observadas de T, y escribe una tabla fija de reglas; no toca CAM, T, Q ni
hechos. Una regla elimina `seq` como detalle local y conserva
`(plantilla WSP, acción) → (plantilla siguiente, delta seq)`. Requiere ocho
orígenes distintos con un resultado único: repetir una sola anécdota no crea
una regla y dos dinámicas incompatibles hacen que el grupo se rechace.

El banco crea presión antes de justificar el sueño: 48 plantillas semánticas
por 64 estados locales ocupan 3.072/4.096 ranuras CAM. Enseña 8.208 filas
específicas de T, reserva cinco estados por plantilla y consolida 144 reglas.
Así, `compressed_knowledge = covered_rows - rules = 8.064`. En 720 sondas
reservadas T obtiene 0 porque esas filas no fueron enseñadas; las reglas
obtienen 720. Un control contradictorio elimina las 48 reglas `approach` y
conserva sólo las 96 no ambiguas.

```
PYTHONPATH=.. python3 -m echoai.nexus0.sleep2
PYTHONPATH=.. python3 -m unittest echoai.tests.test_sleep2
```

El informe es `lab/echo2_sleep2_report.json`. Los hashes completos de CAM, T
y Q son idénticos antes y después; `destroyed=0` y `cortex_calls=0`. Las
reglas son una extensión predictiva compacta y todavía no toman control de la
política.

Validación de SLEEP-2: sus 9 pruebas y las 53 pruebas focales conjuntas de
SLEEP-2/STREAM-1/PATTERN-1/ECHO-2/SHIFT-S/Q pasan.

## Séptimo incremento: GEN-1, resultado rojo

GEN-1 implementa el entero heredable `b=-1/0/+1` como período de exploración
4/8/16. Un hijo recibe sólo ese entero: nace con CAM vacía, Q a cero y T
vacía. Respawn conserva la memoria propia del individuo. `b=0` mantiene el
calendario histórico y el candado del anillo.

El protocolo prefijado seleccionó `b=+1` en tres semillas, pero no transfirió
ventaja a cinco semillas nuevas: mediana 34 episodios para el hijo frente a
27 para el naïf, con 0/5 victorias estrictas. El control sin Q alcanzó también
el criterio en algunas semillas, revelando que ese criterio puede premiar el
calendario de exploración sin aislar aprendizaje. El informe queda publicado
con `green=false`; no se retocó el banco después de medir.

```
PYTHONPATH=.. python3 -m echoai.nexus0.gen1
PYTHONPATH=.. python3 -m unittest echoai.tests.test_gen1
```

Informe: `lab/echo2_gen1_report.json`. Validación: 11 pruebas GEN-1 pasan con
un `expectedFailure` deliberado que representa el KPI causal todavía rojo;
64 pruebas focales conjuntas pasan con ese mismo fallo esperado.

## Octavo incremento: GEN-1f, cierre verde

Los resultados negativos anteriores se conservan. GEN-1b sustituyó el reloj
por evidencia local `T.n[estado][acción]`; GEN-1c separó entrenamiento y examen
congelado; GEN-1d eliminó un ruido que dependía de la acción. Esos bancos
mostraron que los candidatos 1/2/4 no daban una ventaja confirmatoria estable.
GEN-1e amplió el presupuesto a 8 y encontró una mejora grande, pero quedó rojo
por su umbral estadístico prefijado (`p≈0,0158 > 0,01`).

GEN-1f repitió el mismo mecanismo sobre 128 condiciones nuevas derivadas por
SHA-256. Cada hijo hereda únicamente `evidence_budget=8`; CAM, Q, T y restos
nacen vacíos. T da prioridad a la acción local menos observada hasta reunir
ocho muestras de cada orden; después decide `Q.best`, con gate aún soberano.
El examen sólo lee la política y no ejecuta ni aprende.

Resultado: 360 errores tardíos heredados frente a 602 del naïf y 470 del
histórico; mediana 0 frente a 1; criterio en 126/128; 52 victorias, 24 derrotas,
52 empates y prueba unilateral exacta `p≈0,000881`. El control sin Q obtuvo
0/6.144 aciertos. Configuración directa y ablaciones reprodujeron exactamente
sus pares. `destroyed=false_facts=cortex_calls=0`.

```
PYTHONPATH=.. python3 -m echoai.nexus0.gen1f
PYTHONPATH=.. python3 -m unittest echoai.tests.test_gen1f
```

Contrato y resultado: `docs/GEN1F-DESIGN.md`. Certificado:
`lab/echo2_gen1f_report.json`, `green=true`. El informe original
`echo2_gen1_report.json` sigue rojo deliberadamente; forma parte del historial
y no es el certificado final. Este cierre prueba calibración sensorimotora
ruidosa, no navegación ni herencia de recuerdos.

## Noveno incremento: HEAT-1b, cierre verde

HEAT-1 añade al Agent una segunda variable homeostática entera,
`temperature=0..127`. H=0, temperature=0 o temperature=127 terminan la vida;
respawn restaura ambos registros y conserva CAM/Q/T. La observación reconstruye
temperatura en `E[B]` dentro del WSP de 16 bytes. El modo VITA sin temperatura
y el encoder por defecto permanecen opt-in e intactos.

El primer protocolo queda rojo: su control sin Q resolvía accidentalmente la
física mediante el ciclo plano de acciones. HEAT-1b lo corrigió sin rebajar el
control: ocho bandas térmicas y un ambiente caliente donde wait añade 16.
Cargar recupera 3 H y añade 24 de temperatura; refrigerar cuesta 4 H y resta
24. La política no contiene reglas `if temperature` y cortex permanece apagado.

En doce semillas nuevas, joint obtuvo 20.786 turnos frente a 7.221 del control
sin temperatura, 5.293 reiniciando Q/T y 7.186 sin actualizaciones Q. Ganó en
turnos totales en 12/12 parejas. En examen congelado eligió cargar a 80 y
refrigerar a 112 en 12/12. Las muertes joint fueron 641 por calor y 79 por
energía, evidencia del coste de refrigerar.

```
PYTHONPATH=.. python3 -m echoai.nexus0.heat1b
PYTHONPATH=.. python3 -m unittest echoai.tests.test_heat1
```

Contrato: `docs/HEAT1B-DESIGN.md`. Certificado:
`lab/echo2_heat1b_report.json`, `green=true`. El primer informe
`echo2_heat1_report.json` permanece rojo como resultado histórico.
Validación focal: 80 pruebas de HEAT-1, VITA/FOOD/SURV, encoder, GEN-1 y
fases ECHO-2 relacionadas pasan.

## Décimo incremento: CAPACITY-1, cierre verde en CPU

CAPACITY-1 conserva `Layer256` importado y compone dos spokes para 512 LIF.
El resultado sólo entra como firma sensorial `u16` en PATTERN-1: WSP sigue en
16 bytes y Q/T/CAM/VERIFY/gate permanecen en CPU. No hay segundo bus, LLM ni
hardware Akida.

El examen reservado contiene 128 semillas emparejadas. En percepción, 512 LIF
logra 2.048/2.048 frente a 829/2.048 de 256 LIF; la firma barajada después de
la red baja a 142/2.048. El banco temporal demuestra el cuello antes de abrir
Adaptive-LIF: current-only 0/256, oracle 256/256. El candidato 512 LIF + 128
Adaptive-LIF logra 256/256 frente a 0/256 del control de igual tamaño con
adaptación desactivada; gana las 128 parejas (`p=1/2^128`).

El certificado recomputa semillas, filas, hashes, signos y controles desde el
runner: `lab/echo2_capacity1_report.json`. Mide tiempo CPU sin caché, spikes y
estado declarado; no atribuye energía, paralelismo neuromórfico, cámara,
robótica física ni capacidad AKD1500. Diseño: `docs/CAPACITY1-DESIGN.md`.

## Destino hardware confirmado, integración pendiente

BrainChip identifica su tarjeta como **M.2 2230 B+M Key** en
[Development Tools](https://brainchip.com/dev-tools/).
La [ficha AKD1500 V2.4](https://brainchip.com/wp-content/uploads/2025/10/AKD1500-Product-Brief-V2.4-Oct.25.pdf)
especifica PCIe Gen2 y SPI para el chip. No inferir compatibilidad de un
host sólo porque tenga un conector M.2: falta comprobar ranura, señales,
alimentación, sistema operativo y soporte del runtime para la tarjeta.
Las cifras del fabricante no son mediciones de este laboratorio.

Ruta de integración prevista:

1. Cerrar supervivencia en software conservando WSP de 16 B, CAM, Q/T y
   el gate. Córtex apagado en los bancos principales.
2. Seleccionar una tarea pequeña medible (patrón/percepción o propuesta
   de acción) y verificar su conversión y ejecución con el SDK compatible
   con AKD1500. No asumir que el Q6/LIF propio mapea al chip.
3. En host compatible, identificar tarjeta y versión mediante runtime,
   ejecutar modelo y comparar resultados con software. Registrar fallos
   y latencia; la indisponibilidad debe quedar explícita.
4. Sólo después evaluar integración con echOS y consumo medido. VERIFY,
   hechos y veto siguen en CPU; la NPU no obtiene autoridad sobre ellos.

Pendiente: host concreto, presencia física de tarjeta, documentación de
su controlador/runtime y modelo que compila para ese dispositivo.
No reutilizar los IDs del antiguo probe AKD1000 sin verificarlos.
No se ha añadido driver, SDK, dependencia ni backend simulado.

`07-AKIDA.md` describe el plan histórico AKD1000; sus detalles de versión
y edge learning no deben trasladarse automáticamente al AKD1500.
