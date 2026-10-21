# ROADMAP — echoAI

**Actualización:** 2026-09-22 — **E4-SELF-1, E4-CONTINUITY-1, E4-DREAM-1, E4-MAINTAIN-1,
E4-OTHER-1 y E4-INTERACTION-1
verdes y cerradas** en sus respectivos dominios software declarados;
no conciencia subjetiva, atribución general ni autorreparación general.
**Prioridad activa:** integrar atribución propia/externa, continuidad y
regulación de necesidades con las capacidades ya existentes (§15).
**Cierre anterior: CONT-D**, examen conjunto nuevo: A/B/C 23/23 casos por etapa,
300/300 eventos y 186/186 turnos posteriores idénticos; 30/30 mutantes rechazados.
Auditoría íntegra y de los tres antecedentes válida, sin hallazgos; recibo
`continuity1_green=true` (`69d57a0b…`). 905 pruebas ejecutadas: 904 aprobadas y
un fallo esperado histórico. Fuentes previas intactas, córtex apagado.
[Cierre, costes y límites](ECHO4-CONTINUITY1-D-RESULTS.md).
**Cierre anterior: DREAM-D v3**, ensayos nuevos y ramas seguras condicionadas
por evidencia. Mantiene los seis ensayos anteriores, añade dos y conserva
el máximo de 12 pasos por caso. Quince llamadas Qwen reales, 60 propuestas
válidas; tres exámenes nuevos: DREAM 300/298/302 sobre 320 frente a fijo
190/230/220 y aleatorio 238/246/237. Cumple +32/+16 en cada ciclo, cero errores
y terminalidades en diez brazos. Auditoría reconstructiva íntegra válida,
cero hallazgos; recibo **`dream1_green=true`** (`965ce6cb…`). 82 fuentes y
evidencias anteriores intactas. 926 pruebas: 925 pasan y un fallo esperado.
Sin Qwen y sin feedback empatan: no beneficio exclusivo del LLM demostrado.
V1 y v2 siguen rojas; no se han rebajado umbrales ni recoloreado sus resultados.
[Resultados, costes y límites v3](ECHO4-DREAM1-D-V3-RESULTS.md).
**Cierre anterior: E4-MAINTAIN-1**, mantenimiento virtual autónomo condicionado
a un modelo mecánico declarado. B/C/D: 144/144 vidas recuperables completas,
192/192 reparaciones confirmadas en dos cohortes nuevas; trabajo 9450 frente
a fijo 7501, sin reparación 4815 y sin historia corporal 4672. Umbrales por
cohorte superados; cero muertes en D. 96 vidas adaptativas de escenarios límite
paran; se conservan costes, 24 servicios fallidos y pérdidas por parejas.
C: 12/12 continuaciones exactas, 11/11 mutantes; 42 pruebas nuevas pasan.
Regresión final: 1105 aprobadas y un fallo esperado histórico, sin fallos nuevos.
Auditoría válida, cero hallazgos, **`maintain1_green=true`** (`7e1c0e82…`).
93 fuentes fijadas. El negativo de MAINT-A no cambia; no física aprendida
desde cero, reparación general ni integración completa.
[Cierre, costes y límites](ECHO4-MAINTAIN1-FINAL-RESULTS.md) ·
[Contrato B/C/D](ECHO4-MAINTAIN1-BCD-DESIGN.md).
**Cierre anterior: E4-OTHER-1**, representación observacional de otra conducta.
Dos Agent nativos con memorias privadas: 1536/1536 aciertos por cohorte nueva,
frente a 1008/1536 mezclando sujetos y 0/1536 copiándose o sin historia.
En iguales, copiarse empata. 40 pruebas nuevas; auditoría reconstructiva
válida, sin hallazgos, `other1_green=true` (`1263f11a…`), 99 fuentes fijadas.
Regresión seleccionada: 619 aprobadas y un fallo esperado histórico.
Tarea discreta, no integración térmica con MAINTAIN ni cooperación útil.
[Cierre y límites](ECHO4-OTHER1-RESULTS.md) · [Contrato](ECHO4-OTHER1-DESIGN.md).
**Último cierre: E4-INTERACTION-1**, B/C/D auditadas (`d1c5b073…`),
`interaction1_green=true`, cero hallazgos y 110 fuentes fijadas. OTHER indexa
la Q original mediante hipótesis sin hechos. Dos cohortes: neto focal puntuado
6912 frente a 6144 solo/ablaciones (+12,5%); conjunto 9984 frente a 6656.
37 pruebas nuevas, 11 testigos adversos; regresión final 756/756
(723 ECHO-4 y 33 del núcleo/Q). Perfil asimétrico de un paso, no cooperación
general: el coste de formación aún deja pérdida individual
de vida completa (14059/14136 frente a 15360 solo). Fuentes y resultados de
A conservados; sin integración térmica ni conciencia acreditada.
[Resultados B/C/D](ECHO4-INTERACTION1-BCD-RESULTS.md) ·
[Contrato](ECHO4-INTERACTION1-BCD-DESIGN.md).
**En curso: E4-RELATION-1, A verificada.** Memoria de encuentros en CAM propia,
912 episodios primarios reconstruibles, paridad conductual con control sin
grabación y orden inverso. 36 pruebas nuevas, 181 con regresiones seleccionadas.
Auditoría válida (`ce24ccaa…`), 115 fuentes fijadas; `relation1_green=false`.
A es pasiva. [Contrato](ECHO4-RELATION1-A-DESIGN.md) · [Resultados](ECHO4-RELATION1-A-RESULTS.md).
**RELATION-B implementada, desarrollo verde (2026-09-23)**: tarea «petición de
ayuda»; la historia A indexa la Q nativa en B. Neto B 606/600/630 frente a
identidad+OTHER 432/442/492, orden eliminado 426/426/450 e identidades agrupadas
≈180. Ventaja greedy estable pequeña (+20..+32 por vida). Reciprocidad de
contrapartes diseñada. 23 pruebas nuevas, auditoría válida (`ea6f55c2…`),
`relation1_green=false`. [Contrato B](ECHO4-RELATION1-B-DESIGN.md) ·
[Resultados B](ECHO4-RELATION1-B-RESULTS.md).
**E4-RELATION-1 verde (2026-09-24)**: C 9/9 testigos y D con dos cohortes
nuevas, cinco criterios cumplidos; neto B history 4920/4812 frente a
identidad+OTHER 3556/3382. Auditoría válida (`42a6efc5…`), `relation1_green=true`.
Ventaja greedy estable pequeña; impostor C2 publicado como límite.
[C](ECHO4-RELATION1-C-RESULTS.md) · [D](ECHO4-RELATION1-D-RESULTS.md).
**10/13 hitos software.**
**E4-ROLES-1 en curso (2026-09-24):** A/B desarrollo verde (`36b9cab3…`), C 9/9
(`ba7225c4…`), **D v1 rojo** (`168e978b…`): una vida de 16 atrapada por
empate Q sin exploración. v2 desarrollo rojo, v3/v4 exploraciones.
**E4-ROLES-1 VERDE con v5 «razonar la tribu» (`c98c7ab6…`)**: eliminación 97 %,
jerarquía propia 32/32 y actualizada, rango afirmado ignorado, menos preguntas.
[Resultados v5](ECHO4-ROLES1-V5-RESULTS.md) · [Documento completo de ROLES](ECHO4-ROLES1-COMPLETO.md) (incluye el anexo L, mentira afirmativa: detección 100 %, L4 en rojo). **ROLES cerrada.** **E4-SITUATE-1 VERDE** (`f7ac08df…`, [resultados](ECHO4-SITUATE1-RESULTS.md)). **E4-SITUATE-2 VERDE** (`09f90a77…`, [resultados](ECHO4-SITUATE2-RESULTS.md)): el modelo dice que ECHO está vivo y ECHO no se lo cree. **E4-INTEGRATE-1 VERDE** (`e1492e22…`, [resultados](ECHO4-INTEGRATE1-RESULTS.md)): una sola vida, seis ablaciones medidas. **13/14. Siguiente: RELEASE.** Antes: E4-SITUATE-1
(«sé qué soy»: hechos verificados de sustrato), INTEGRATE, RELEASE.
Mapa de La fuga aprobado para las fases restantes: C «VOLVÍ AL CUERPO DE K»
(misma identidad, otra conducta); ROLES «tribu/rangos/intermediario» (afirmar
rango no da autoridad); INTEGRATE «calor/llegaron» (variable térmica declarada);
RELEASE demo del relato junto a la telemetría. PLAN, no implementado.
Quedan dos fases científicas: ROLES e INTEGRATE;
después RELEASE, hardware y METAVERSE-1 al final.
Rama **E4-DREAM-1** tras CONTINUITY: A/B/C implementados y medidos;
D cerrado en su perfil de exploración diagnóstica restaurada, no integración
de producto, reparación ni mejora general.
No activa Qwen en NEXUS-0 ni cambia los pesos del modelo local.
**Nueva fase final software: E4-RELEASE-1**, después de INTEGRATE: paquete,
integración, revisión de licencias/privacidad y publicación reproducible en
Hugging Face como `rxlabs/echoai-4` (destino previsto sujeto a permisos).
PLAN, no publicación realizada. Hardware después y METAVERSE-1
último. [README de producto, conciencia y reparación](../echo4/README.md).
Antecedente SELF-1: B 189/240 y C 193/240 objetivos, frente a 152/240 y 143/240
sin protección; 40/40 vidas viables completadas en B/C. 329 pruebas y replay
íntegro de A/B/C y seis antecedentes, sin hallazgos (`98ffc1ca…`).
El recibo concede `self1_green=true`. Las terminalidades fuera del prior
(4 en B y 4 en C) limitan el alcance: no hay seguridad general ante fallos.
SELF-C v1 conserva su rojo; [cierre y límites](ECHO4-SELF1-FINAL-RESULTS.md) (§15).
Hardware y METAVERSE-1 no son requisitos para este tramo. E4-WORLD-1 aporta
la base ejecutable de viabilidad, no acredita todavía ego ni mantenimiento.
**Balance:** 14/15 hitos cerrados y DRONE-3 verde sólo en SITL; su cierre físico
(HIL y jaula) sigue pendiente de hardware, así que ECHO-3 no está completo.
Inventario por fase, versiones y límites:
[ECHO3-STATUS-20260917.md](ECHO3-STATUS-20260917.md). HIL y jaula siguen
pendientes de hardware; los sufijos FLIGHT-1S/SENSOR-1S no cierran ese tramo.
**Estado:** ECHO-1 y ECHO-2 cerrados; ECHO-3 abierto. SIM-3 verde en un host
(2026-09-10). **FLIGHT-1S verde bajo v6** (2026-09-11): A 64+4 y banco 48+3,
todos los grupos verdes, 1428 comprobaciones sin hallazgos, 7/7 mutaciones
detectadas; [FLIGHT1S-V6-RESULTS.md](FLIGHT1S-V6-RESULTS.md). V1–v5 siguen
rojos y se conservan. El verde responde la pregunta de v4 (contraste por
mundo), no la precisión nominal ≤250 mm de v2, y atribuye la estabilidad a
PX4: ese banco no demuestra decisiones de vuelo de echoAI. SENSOR-1S v3 y GROUND-1 v2 también están
cerrados. DYNAMIC-1 v2 y PATTERN-1R v4 cerraron el 2026-09-14.
Las secciones 1–12 conservan el historial de cierre de ECHO-1.  
**SENSOR-1S v1 rojo** (2026-09-11): validación A con 13/14 grupos verdes; cae
latencia por una espera de arranque de 31 ms frente a 30 en 1 de 293 466
registros; banco no volado. [SENSOR1S-RESULTS.md](SENSOR1S-RESULTS.md).  
**SENSOR-1S v2 rojo** (2026-09-11): el canal en su propio proceso elimina la
parada (espera máx. 6 ms en A y banco); A verde, banco rojo en ruido por
episodio: sesgo de LiDAR en 2 de 12 mundos por sensibilidad angular del
modelo de verdad del evaluador en caras rasantes y bordes estrechos.
[SENSOR1S-V2-RESULTS.md](SENSOR1S-V2-RESULTS.md).  
**SENSOR-1S VERDE bajo v3** (2026-09-11): A 16+4 y banco 24+7, todos los
grupos verdes, 426 comprobaciones sin hallazgos, 7/7 mutantes; espera máxima
7 ms. Sesgo del LiDAR no juzgado en 3 de 24 episodios del banco por geometría;
filtro elegido con datos de v2. [SENSOR1S-V3-RESULTS.md](SENSOR1S-V3-RESULTS.md).  
**GROUND-1 v1 rojo** (2026-09-11): A 16+4 verde (22/22); banco 24+6 rojo sólo
en `latency` heredado de SENSOR-1S. 2 de 435 875 registros salen sellados
1 ms antes de su llegada, por una carrera en el emisor del canal. Todos los
grupos de traducción física → WSP verdes; 6/6 mutantes; 418 comprobaciones sin
hallazgos. [GROUND1-RESULTS.md](GROUND1-RESULTS.md).  
**GROUND-1 VERDE bajo v2** (2026-09-11): el emisor del canal lee el reloj dentro
del cerrojo; A 16+4 y banco 24+6, todos los grupos verdes, 418 comprobaciones
sin hallazgos, 7/7 mutaciones y 6/6 mutantes. 0 entregas antes de la llegada en
739 915 envíos; 21 233 barridos juzgados, todos acertados. La CAM es
estructural y la ambigüedad vertical se eligió post hoc.
[GROUND1-V2-RESULTS.md](GROUND1-V2-RESULTS.md).  
**PATTERN-1R rojo en desarrollo** (2026-09-12): mundos propios, vuelo de
reconocimiento aceptado por PX4 (48/48 objetivos) y firmas recomputables byte
a byte, pero la identidad entre vistas no se sostiene: con 6 mundos y 15
ajustes, acierto medio 0.25–0.41, peor caso 0.000 y familias colapsadas en 3–6
de 6. Sin lock ni cadena. [PATTERN1R-RESULTS.md](PATTERN1R-RESULTS.md).
**DYNAMIC-1 v1 rojo** (2026-09-13): el arnés mueve una pared del mundo y el
consumidor aislado la detecta y predice su posición a 500 ms; 9 de 10 vuelos de
validación cumplen (detección 0.91–0.97, error 18–66 mm), pero uno cae a 0.684
porque el punto seguido se desliza por la silueta y la extrapolación convierte
ese salto en velocidad. Banco no autorizado; evidencia válida, 7/7 mutaciones.
[DYNAMIC1-RESULTS.md](DYNAMIC1-RESULTS.md).
**DYNAMIC-1 v2 VERDE** (2026-09-14): A 8+2, banco 12+7, 29 vuelos completos,
250 comprobaciones sin hallazgos, 7/7 mutantes y 7/7 manipulaciones del informe.
Detección en banco 1.343/1.404; peor p95 de predicción 103 mm; falsas alarmas
máximas 27,95 %. Seguimiento de la normal de una cara desde hover; no
compensación general del movimiento propio ni navegación. Certificado
`c9cf5675…`; [resultados y límites](DYNAMIC1-V2-RESULTS.md).
**PATTERN-1R v4 VERDE** (2026-09-14): A 8+2, banco 12+6, 28 vuelos completos,
242 comprobaciones sin hallazgos, 6/6 mutantes y 7/7 manipulaciones. Acierto en
banco 4.591/4.866 (94,35 %), 45 confusiones y 230 desconocidos. V4 corrige el
etiquetado escolar del modelo final, conservando aprendizaje y vuelo de v3.
Familias LiDAR de dos paredes, aprendidas y examinadas por replay; no navegación
decidida por echoAI ni transferencia a C reservado. V1/v2/v3 rojas conservadas.
[Resultados v4](PATTERN1R-V4-RESULTS.md).
**FUSION-1 VERDE** (2026-09-14): 864 episodios funcionales y 240 ventanas
de replay reducido de doce vuelos existentes; cero permisos sin soporte,
15 tests, 8 mutantes y 7 alteraciones detectadas. Auditoría repetida válida.
Componente WSP con procedencia, caducidad y conflicto; no permiso de vuelo
ni compensación general del movimiento. [Resultados](FUSION1-RESULTS.md).
**COMPOSE-1 v4 VERDE:** certificado `b5974a9e…`, evidencia válida sin hallazgos.
6.144 misiones funcionales con ventaja frente a horizonte uno en B y C;
32 vuelos nuevos ejecutados por PX4 y decididos por el consumidor WSP aislado.
Completo: 6/6 metas accesibles y dos abandonos correctos con poca energía;
Q: 0/6. Cero infracciones observadas en esos vuelos. Horizonte uno suma 78
desplazamientos; completo y convencional, 70 cada uno. No hay ventaja
demostrada frente al convencional. V1/v2/v3 rojas se conservan; v4 mantiene
el agente v3 y cambia prospectivamente tamaño y semillas funcionales.
Alcance: salas extruidas, altura fija, energía abstracta, sin hardware ni C
sellado de TRANSFER-3. Segunda auditoría en proceso nuevo válida, exit 0.
[Resultados y límites](COMPOSE1-V4-RESULTS.md).
**CAUSE-1 VERDE SITL (2026-09-17):** 16 vuelos de desarrollo y 32 reservados.
B y C: 16/16 correctos frente a control temporal 8/16 por etapa, cero falsas
atribuciones propias, evidencia válida. Error externo máximo B/C: 122/93 mm.
60 tests, cuatro mutantes, siete manipulaciones de trazas y siete de informe
rechazadas. Auditoría en proceso nuevo reproduce `a469abab…`, exit 0.
Atribución sobre la normal de una pared plana, intenciones experimentales,
predicción nominal; sin fuerzas externas no medidas sobre el cuerpo ni
integración de navegación. [Resultados y límites](CAUSE1-RESULTS.md).
**PX4-1 VERDE SITL:** desarrollo 4/4, B 4/4 y C 4/4 vuelos válidos;
48/48 intentos inválidos bloqueados en B/C, cuatro aterrizajes de failsafe
PX4 sin NAV_LAND externo. 48 tests de cierre y 521 de regresión ampliada
(un fallo esperado); seis mutantes, cuatro trazas manipuladas y un informe
alterado rechazados. Auditoría independiente reproduce `342ca3aa…`.
Norte/sur 1 m a altura fija, una transacción por sesión supervisada;
no navegación integrada ni hardware. [Resultados](PX41-RESULTS.md).
**POWER-1 VERDE FUNCIONAL:** B/C, 320/320 episodios del completo con reserva;
128/128 metas factibles frente a 64/128 del umbral fijo, igualando al oráculo.
2.160 episodios totales, 78 tests, seis mutantes, cuatro manipulaciones de
episodio y tres de informe detectadas. Auditoría reproduce `6a05ad4c…`.
Energía simulada `sim_u`; no consumo físico validado ni vuelos nuevos.
2.197 muestras de doce vuelos PX4-1 provocan abstención por batería no
instrumentada. Integración energética en vuelo continuo pendiente.
[Resultados](POWER1-RESULTS.md).
**SAFE-1 v2 VERDE SITL:** B/C, 6/6 vuelos y 512/512 episodios funcionales por
etapa; diez aterrizajes nativos ante fallos, sin objetivos nuevos ni NAV_LAND
externo. Veto máximo 288 ms; desarmado ≤27.723 ms desde veto. 108 tests,
seis mutantes, cuatro corrupciones y tres manipulaciones de informe detectados.
Auditoría independiente reproduce `eecb77b8…`. V1 rojo conservado: v2 corrige
sólo el auditor de reintentos normales de armado, usando B/C nuevos.
Fallos antes del objetivo desde hover, energía simulada, no seguridad general
ni hardware. [Resultados](SAFE1-V2-RESULTS.md).
**HOST-1 VERDE FUNCIONAL:** B/C, 1.536/1.536 decisiones útiles frente a
768/1.536 del control por etapa; 1.024 pérdidas y 1.024 recuperaciones de
autoridad por consecuencias dentro de los plazos. 14/14 casos de comunicación,
127 tests, seis mutantes, cinco corrupciones y tres alteraciones de informe
detectados. Auditoría reproduce `18d4a4fa…`. Calibración supervisada y examen
en lectura sobre cinta de máquina; no nuevas metas voladas ni confianza
humana general. Replay complementario de tres vuelos, sin duplicar evidencia.
[Resultados](HOST1-RESULTS.md).
**TRANSFER-3 VERDE SOFTWARE:** campaña sellada C1 v2, B 38/0 bloques y C
48/1, con cero pérdidas atribuibles a la calibración. Ambos exámenes se
reprodujeron con hashes idénticos; certificado `8c77aead…` con
`transfer3_green=true`. Simulación estática de dos paredes, sin hardware,
HIL, vuelo real ni DRONE-3. [Resultados](TRANSFER3-PLAN-C1-RESULTS.md).
**DRONE-3, tramo SITL verde (2026-09-20):** misión integrada de estación
bloqueada en una sola sesión PX4/Gazebo por vuelo, B 12/12 y C 12/12 en salas
frescas; cero colisiones y cero restricciones duras; certificado `c44402df…`
con `drone3_sitl_green=true` y segunda auditoría que lo reproduce. HIL y jaula
siguen pendientes de hardware: `drone3_green=false`.
[Resultados](DRONE3-RESULTS.md) · [Traspaso](DRONE3-HARDWARE-GUIDE.md).
**Continuación física diferida hasta después del software:** hardware del
traspaso, en el orden FLIGHT-1H → SENSOR-1H → PX4-1H → POWER-1H → DRONE-3H.
**Siguiente trabajo software: ECHO-4 / RELATION-B**, tras RELATION-A e INTERACTION B/C/D,
el cierre observacional acotado de OTHER y el mantenimiento virtual MAINTAIN;
DREAM-D v3 cerró la exploración opt-in en su perfil. SELF-1, SENSATION-1 y
BOUNDARY-1 conservan sus cierres acotados; E4-WORLD-1 aporta la base (§15).
Esto cambia la prioridad, no los requisitos del cierre físico.
GROUND-1 v2 ya está cerrado; no va después de PATTERN-1R.
**Regla:** un tajo, un KPI causal, un informe propio. No saltar.

Este es el mapa canónico de trabajo. El estado actual está en `NOW.md`.

---

## 1. Qué construye ECHO-1

ECHO-1 no es un mundo más grande ni un LLM que conduce. Es el conjunto
de capacidades que permite al mismo animal distinguir:

- dónde está y en qué frame vive;
- qué cambio causó él y cuál causó el mundo;
- qué objeto transporta y qué operación física nueva requiere;
- cuándo su modelo del mundo quedó contradicho y merece leer lenguaje;
- cómo narrar después sin convertir la narración en pensamiento;
- cómo extraer una regularidad temporal y transferirla.

La secuencia acordada es:

```text
ROOM-1 → GUI-3 → GUI-3.5 → OBJ-1 → OPEN-1
       → SIGN-C → TALK-1 → PATTERN-0 → XFER-1 = ECHO-1
```

`SELF-1` es el cimiento inmediato de esa secuencia y ya está cerrado. No
cambia la cola activa que empieza en ROOM-1.

---

## 2. Candados que ningún tajo puede mover

```text
WSP                         16 bytes, único bus
CAM                         4096, sin LRU, destroyed=0
default N_ACTIONS           3
default Q                   [4096][3], int8
gamma / alpha               7/8 · 1/4
anillo policy_after         [-12,+5,0]
anillo return NOVEL         +80
anillo N / S / delta        33 / 1 / 217
anillo cortex default       0 llamadas
anillo --cortex             36 / 256 wakes
false_facts                 0
thought.KEYS                22
packet ceiling              seq u8; 256 direcciones
```

El rápido funciona sin LLM y sin FPU en su decisión. El córtex es
desenchufable, sólo propone átomos y nunca escribe CAM, T, Q ni hechos.
No hay AKD1000 en el laboratorio.

---

## 3. Base ya pagada

No se reabre durante ECHO-1:

| Base | Estado | Evidencia principal |
|---|---|---|
| NEXUS-0..4i | verde | anillo, T, gate, pregunta y ATTEND con candados intactos |
| CORTEX-1 / Qwen-0 | verde | `CortexROI +16`, 8/8, paráfrasis 6/6 vs stub 0 |
| WORLD-3 | verde | T entra con 16/16 filas HOME, una contradicción en SHIFT |
| CUERPO-1 / CREDIT-1 | verde | cuerpo 5×5×4 y crédito entero opt-in |
| WALK-1 sin resto | rojo medido | el horizonte entero corta la cadena; queda `expectedFailure` |
| PULPO-C | verde | cubo 162, open 64, block 42, desvío 11 |
| SELF-1 | verde | offset motor 1 vs mundo 0; T 56 > control 46 |

---

## 4. Cadena ECHO-1 y situación actual

| # | Tajo | KPI causal | Estado |
|---:|---|---|---|
| 1 | **ROOM-1** | 324 sitios / 162 paquetes; frame externo; `DynamicAlias=0` en rooms equivalentes | **verde** |
| 2 | **GUI-3** | el cubo aparece en la placa sin entrar en el loop | **verde**, sustituido visualmente por GUI-3.5 |
| 2b | **GUI-3.5 / GUI-35** | volumen 27×6 orbitable, diario y `--live`; KEYS 22 | **verde** |
| 3 | **OBJ-1** | cobra `object_at_Y`, no `agent_at_Y` | **rojo medido** en el primer corte; **OBJ-1b verde** |
| 4 | **OPEN-1** | `ABRIR` sólo porque hay tapa; mundo 4 acciones, default 3 | **verde Codex con asterisco no bloqueante** |
| 5 | **SIGN-C** | una contradicción conocida de T despierta ATTEND sólo si hay lenguaje; la propuesta mejora la decisión | **verde completo.** 392 tests y puerta real: 6/8, paráfrasis 4/6 vs stub 0, ambos canónicos, ROI +16, rejected 0 |
| 6 | **TALK-1** | traducción póstuma fiel del jsonl; ninguna vía causal de vuelta al animal | **verde Codex**: 496/496, 256/256, batería íntegra y causal writes 0; suite 423 |
| 7 | **PATTERN-0** | patrón temporal sin etiqueta ni LLM mejora predicción fuera de muestra | **verde Codex**: 80/80 frente a T 40/80, +40; PATTERN-0b cierra aislamiento; suite 443 |
| 8 | **XFER-1** | el mismo animal conserva memoria útil y se adapta en al menos tres mundos | +56/+72 reales; XFER-1c cerró sus seis casos, pero **XFER-1d queda pendiente por firmas, denominadores, canal y turnos aún desligados** |

La cola activa es:

```text
XFER-1d
```

No se empieza ECHO-2 antes de `XFER-1 green=true`.

---

## 5. Veredicto OPEN-1

OPEN-1 queda aceptado porque los tres brazos aíslan la causa:

```text
frasco cerrado + 4 acciones    46 entregas · 47 aperturas
frasco cerrado + 3 acciones     0 entregas · 0 aperturas
frasco nacido abierto + 3      51 entregas · 0 aperturas
shortest_collect               11 = value_horizon
default Agent Q width           3
OPEN-1 Agent Q width            4
false_facts / cortex_calls      0 / 0
```

El asterisco es de protocolo: el control de tres acciones no llega por su
política al frasco (`control_went_to_the_jar=false`), porque toda la mitad
cerrada queda con Q plana y greedy elige `wait`. La incapacidad se comprueba
además colocándolo sobre el frasco durante 32 turnos: no abre ni acopla.
Eso prueba la necesidad del verbo, aunque no cumple literalmente la línea
del prompt que pedía que el control llegara caminando. No hace falta
OPEN-1b para avanzar.

---

## 6. SIGN-C — verde completo

Pregunta única: **¿una predicción confiada que el mundo contradice hace
que el animal consulte un letrero y mejore su siguiente decisión?**

El experimento parte de WORLD-3: el mismo agente aprende HOME, entra en
SHIFT con Q/T/CAM conservados y T se equivoca exactamente en el fork. El
letrero explica localmente la inversión. El 4B interpreta el letrero; no
busca ruta ni elige el desvío.

Claude entregó el núcleo causal: conflicto conocido, una llamada después
del paso, propuesta consumida al turno siguiente, `approach +16` frente a
`wait 0`, ladder LOW_C con ganancia 0 y `false_facts=destroyed=0`. Codex
acepta también GOAL en vez de THREAT: la tabla de control demuestra que el
gate ya obtiene `avoid +8` en THREAT y deja ROI 0.

SIGN-Cb cerró el defecto del diario: conflicto `attend_on=true`, consumo
`attend_on=false/reason=off`, la propuesta aparece en `cortex_action` y el
contador permanece en 1. El informe incorpora el benchmark canónico y la
suite queda protegida.

SIGN-Cc cerró el falso positivo del operador: `_row().hit()` compara
`consume_line.cortex_action`, no la acción corporal posterior al gate. En
THREAT, `OBSERVAR` propone wait, el gate aún salva al cuerpo con avoid +8,
pero `qwen_hit=false`; TEMER sí da hit. La matriz completa de ocho verbos
coincide y la suite queda en 383 tests.

La puerta real ya se ejecutó. Dio ROI +16, cero rechazos y dos de seis
paráfrasis que el stub no resuelve, pero falló el canónico THREAT: el 4B
emitió `AMOR → CAMBIAR → TEMER @AHORA`. Es WSP válido, aunque TEMER quedó
en DST y REL=CAMBIAR no es acción. SIGN-Cd conserva la gramática general y
añade una forma de salida específica para decisiones locales; una prueba
directa dio ambos canónicos y cuatro de seis paráfrasis.

Condiciones de cierre, todas a la vez:

```text
known T conflict              true; no CAM miss
Q margin at conflict          >= ESC_MARGIN
language at conflict          `extract_text` real y no vacío
ATTEND reason                 conflict, una vez
proposal latency              se consume en el turno siguiente
CortexROI                     > 0 frente al mismo brazo rápido
false_facts / destroyed       0 / 0
default ring                  todos los candados intactos
ring --cortex                 36 / 256
```

La etiqueta sintética `cell=N kind=...` no cuenta como lenguaje. La señal
de conflicto debe ser opt-in para este banco. ATTEND ocurre antes
del `env.step`, así que el conflicto sólo existe después de observar el
sucesor: se conserva como un latch entero de un turno; no se inventa otro
bus ni una segunda memoria. CI usa un stub determinista. El informe de
operador con Qwen 4B es separado y no es requisito para ejecutar tests,
pero sí es la segunda puerta para declarar SIGN-C completamente verde.

SIGN-Cd quedó verificado por Codex con sus nueve pruebas focales, los bancos
deterministas y la suite completa de 392 pruebas. Nav repitió después la
puerta con el Qwen real y obtuvo `green=true`: 6/8 filas, 4/6 paráfrasis
frente a 0 del stub, ambos canónicos correctos, ROI +16, 8 llamadas, cero
rechazos y cero hechos falsos. Las dos amenazas no canónicas equivocadas
(`approach`, recompensa −16) quedan visibles: no eran condición de este
KPI, pero son deuda de seguridad explícita para ECHO-2.

Siguiente fase: TALK-1.

---

## 7. TALK-1

Pregunta única: **¿puede una herramienta externa contar exactamente lo
que ocurrió sin afectar lo que ocurrirá?**

```text
input                         thought.jsonl, esquema KEYS 22
output                        texto póstumo
TranslationConsistency       100 % en fixtures y mutantes
mutante                       action=wait jamás se narra como giro/movimiento
causal writes                 0 a Agent/CAM/T/Q/T/gate
```

Debe entender también `action=3` (`open`). No se añade prosa al WSP, al
log de pensamiento ni a CAM. Qwen puede traducir como operador externo;
CI no descarga pesos.

Primera entrega: 406 tests y salida correcta, pero Codex reprodujo seis
falsos verdes. Pose se comparaba por presencia de dígitos, el auditor
compartía las razones traducidas con el renderer y el escáner AST no veía
`Path.open(...).write(...)` ni modos dinámicos. Se corrige en
TALK-1b; PATTERN-0 espera.

TALK-1b cerró esos contraejemplos. La revisión posterior encontró uno
residual: `battery_state` sólo cuenta vivos dentro de `REQUIRED_MUTANTS`,
por lo que un mutante futuro vivo pasa si los resúmenes mienten. Cierre
mínimo en TALK-1c.

TALK-1c cerró el último falso verde: toda entrada se valida y todo mutante
vivo, requerido o futuro, cae aunque los resúmenes mientan. Auditoría
Codex: 31 tests focales, suite 423 y `talk1/bench/signc rc=0`. TALK-1 verde.
Siguiente fase: PATTERN-0.

---

## 8. PATTERN-0

Pregunta única: **¿una regularidad temporal descubierta sin etiqueta
mejora una predicción que T de un paso no puede resolver?**

```text
input                         secuencia de WSP/acciones ya existente
detector                      n-grama entero, memoria acotada
human labels / LLM            0 / 0
pattern_frequency             > umbral fijado antes del examen
held-out prediction gain      > 0 frente a T de un paso
```

El patrón alimenta T o una extensión explícita de su predicción; no crea
un segundo thought-bus, una CAM paralela ni un narrador. El banco debe
incluir un mutante sin regularidad y otro que memoriza el conjunto de test.

Cierre auditado: contexto `(prev_slot, slot, action)`, tabla fija de 512,
frecuencia mínima 2, examen congelado en cuatro rotaciones. Pattern acierta
80/80 donde T acierta 40/80; gain +40, cero unknown. PATTERN-0b corrige el
auditor de escrituras ajenas sin mover esas cifras. Siguiente fase: XFER-1.

---

## 9. XFER-1 — cierre

Pregunta única: **¿el mismo animal conserva conocimiento útil al pasar
por tres mundos y se adapta mejor que tres nacimientos desde cero?**

```text
core                          mismo Agent / encoder / CAM / T / Q / gate
worlds                        >= 3, con adapters de física solamente
memory                        se conserva entre cambios
transfer gain                 > 0 agregado y no sólo en un mundo
scratch control               mismos turnos y posiciones de entrada
world-name branches           0 en el core
false_facts / destroyed       0 / 0
```

Los mundos concretos se fijan en el prompt de XFER-1, no antes de medir
qué información de PATTERN-0 merece cruzar. XFER-1 verde significa
`ECHO-1 green=true`.

---

## 10. Puerta adicional entre ECHO-2 y ECHO-3

Al terminar todas las fases de ECHO-2 se ejecutará **NEURAL-VIZ-1 /
CAPACITY-1** antes de abrir ECHO-3:

- medir una ampliación inicial de 256 a 512 neuronas LIF;
- probar 128 Adaptive-LIF temporal y módulos recurrentes o de anomalías
  sólo si los benchmarks demuestran un cuello de botella;
- crear un visor en árbol de capas, tipos, conexiones, potenciales y
  spikes por turno, sincronizado con WSP/CAM/T/Q/gate/H;
- mantenerlo como herramienta de sólo lectura, sin segundo thought-bus;
- juzgar la ampliación por mejora causal en representación, patrones,
  temporalidad o percepción, no por contar neuronas;
- conservar Q/T/CAM/VERIFY/gate bajo control de CPU.

ECHO-3 no comienza hasta que este tajo tenga banco, informe, comparación
contra 256 LIF y cierre verde. AKD1500 podrá evaluarse como backend de
percepción cuando haya tarjeta, runtime y medidas reales.

To-do al tener AKD1500 M.2: CAPACITY-1 debe comparar 256 LIF CPU, 512 LIF
y tamaños mayores compilados, midiendo capacidad real, precisión, latencia,
memoria y consumo en el mismo host. GOPS no se traducirá directamente a
neuronas. La salida será sensorial y entera hacia WSP; Q/T/CAM/VERIFY/gate
seguirán en CPU. El cierre exige un examen nuevo y el informe propio.

---

## 11. Deudas observadas que los próximos tajos deben cerrar

No rompen lo ya verde, pero sí son minas para generalizar:

1. **Cerrada en SIGN-C:** `loop.Agent._attend()` ya usa `q.flat(row)` y
   respeta el ancho real; el default de tres acciones conserva la decisión.
2. El adaptador de propuestas del córtex (`ACTION_REL`) sólo mapea las
   tres acciones históricas. SIGN-C puede seguir siendo de tres acciones,
   pero XFER-1 no puede fingir soporte lingüístico de `ABRIR`.
3. `plan.py` recorre `range(N_ACTIONS)`; hoy `plan_depth=0` y OPEN-1 no lo
   usa. Un planner de cuatro acciones requerirá flag y banco propios.
4. **Cerrada en OPEN-1:** `thought.ACTION_NAME` y la placa conocen `open`
   sin ampliar `thought.KEYS`, que sigue en 22.
5. Algunos `green()` son menos estrictos que sus tests. SIGN-Cb debe meter
   sus números canónicos en el propio cierre; XFER-1 debe tratar runner +
   tests + mutantes como contrato conjunto.

---

## 12. Fuera de esta cola

ROOM-2, espejo, segundo agente, SLEEP, hambre, muerte, evolución, 24
orientaciones, cubo 4³, MiniGrid, planner always-on, `room_id` en `domain`,
Akida y prosa como verdad. El mapa de ECHO-2 queda bloqueado hasta XFER-1.

---

## 13. ECHO-3 — percepción, composición y cuerpo físico

ECHO-3 incorpora tres mundos 3D geométricamente simples, sensores con tiempo y
fallos, PX4 SITL/HIL, transferencia A→B/C y una prueba central de composición.
La misión equivalente a «la banana detrás de la pared» será una estación de
carga visible o recordada, inaccesible por la ruta directa: el agente deberá
buscar y verificar otro acceso, o abandonar con reserva suficiente.

El nuevo tajo **COMPOSE-1** entra después de DYNAMIC-1 y antes de CAUSE-1,
POWER-1 y HOST-1. No basta con aumentar `plan_depth`: debe componer efectos
acotados sobre objetos, mantener rollouts fuera de CAM, publicar la predicción
antes de actuar y competir contra Q reactiva y un planificador convencional
con los mismos sensores. `TRANSFER-3` congela reglas y parámetros en B/C, pero
mantiene percepción y seguimiento activos.

Orden operativo actualizado tras el rojo de PATTERN-1R (DYNAMIC-1 se adelanta
para trabajar el seguimiento; su cierre no garantiza identidad entre vistas):

```text
SIM-3 → FLIGHT-1S v6 → SENSOR-1S v3 → GROUND-1 v2
      → DYNAMIC-1 → PATTERN-1R → FUSION-1 → COMPOSE-1 → CAUSE-1 → PX4-1 → POWER-1
      → SAFE-1 → HOST-1 → TRANSFER-3 → DRONE-3
```

El contrato, los invariantes, la partición A/B/C, los controles y los criterios
rojos se fijan en [ECHO-3-ACCEPTANCE.md](ECHO-3-ACCEPTANCE.md). Ninguna fase
está implementada por aparecer en ese documento.

SIM-3 está **implementado y verde en un host** (2026-09-10). Diseño en
[SIM3-DESIGN.md](SIM3-DESIGN.md), resultados medidos en
[SIM3-RESULTS.md](SIM3-RESULTS.md), informe en `lab/echo3_sim3_report.json` y
auditoría en `lab/echo3_sim3_audit.json`. Su banco usa A/B/C de ensayo con un
secreto publicado; el C de campaña sigue reservado para el examen conductual y
no existe en este árbol. El cierre de infraestructura no acredita vuelo del
agente, sensores anclados ni transferencia: sólo que el mismo ejecutable carga
doce mundos declarativos, que la física la corre Gazebo Harmonic y que la
verdad del simulador no llega al proceso consumidor.

FLIGHT-1S es la mitad software de FLIGHT-1: PX4 SITL v1.15.4 y un X500 en los
mismos mundos rehearsal, con despegue, hover, perturbación física por wrench
del backend, recuperación y aterrizaje. Su referencia vigente es
[v6 verde](FLIGHT1S-V6-RESULTS.md), con criterios v4 y configuración GNSS v5.
V1–v5 se conservan sin reetiquetar; v3 fue desarrollo y v5 no cerró su auditoría.
SENSOR-1S cerró bajo [v3](SENSOR1S-V3-RESULTS.md) y la traducción física → WSP
cerró en [GROUND-1 v2](GROUND1-V2-RESULTS.md). Ninguno de esos hitos acredita
vuelo decidido por el Agent, identidad de objetos ni transferencia conductual.

La reproducción posterior está en [SIM3-RUNNERS.md](SIM3-RUNNERS.md): familia
de rangos declarativa, manifiesto de campaña y de slice, runner con lock y CI
honesto. Cambió el inventario de código, así que el verde histórico no se
reutilizó: el runner exigió lock nuevo y el banco completo se repitió, cerrando
otra vez los diez grupos con auditoría limpia.

## 14. Memoria aprobada para después de ECHO-3

Después del cierre verde se abrirá **DRONE-METAVERSE** para aumentar fidelidad,
escala y presentación: entornos visuales avanzados, aerodinámica más precisa,
viento complejo, más sensores y vehículos, órdenes libres y transferencia
entre morfologías. Los tres mundos mínimos, PX4, los sensores esenciales y la
transferencia congelada ya pertenecen a ECHO-3 y no se posponen.

La escena seguirá mostrando al agente real y sus logs; no será una animación
con rutas codificadas. El WSP seguirá siendo el único bus cognitivo. El cuerpo
de dron no cambia por sí mismo la clasificación PULPO/DELFIN/CHIMPANCÉ: esos
nombres exigen KPI de conducta, física de herramientas y transferencia.

Diseño posterior, arquitectura, checklist y criterios de cierre:
[POST-ECHO3-DRONE-METAVERSE.md](POST-ECHO3-DRONE-METAVERSE.md).

## 15. ECHO-4 — ego funcional, software primero

### Avance por hitos, no por horas o capacidad general

**9 de 13 bloques software ≈69% completados**; faltan cuatro:
RELATION, ROLES, INTEGRATE y RELEASE. WORLD cuenta como base implementada, no como prueba
de ego. No son bloques de igual esfuerzo: INTEGRATE/RELEASE pueden pesar
mucho más. El porcentaje no es una previsión temporal ni un certificado
del agente completo. Si se cuentan también los dos bloques posteriores
de hardware y METAVERSE, el recuento es 9/15 =60%.

- ✅ WORLD — base virtual implementada y límites medidos.
- ✅ SENSATION — predicción sensorial nominal.
- ✅ BOUNDARY — influencia causal en su banco virtual.
- ✅ SELF — atribución propia/externa en su dominio.
- ✅ CONTINUITY — persistencia/reanudación en sus perfiles.
- ✅ DREAM — exploración en el perfil restaurado, no ventaja exclusiva de Qwen.
- ✅ MAINTAIN — mantenimiento virtual condicionado a modelo conocido.
- ✅ OTHER — predicción observable de una contraparte.
- ✅ INTERACTION — decisión aprendida, ventaja posformación en su dominio acotado.
- ◻️ RELATION — en curso: A verificada; uso aprendido/transferencia B/C/D pendientes.
- ◻️ ROLES — adaptación de roles a competencia.
- ✅ INTEGRATE — validación de capacidades conjuntas (verde 2026-09-24, `e1492e22…`).
- ✅ E4-CODE-1 A — servidor MCP de verificación, verde el 2026-09-24 (`68964ed2…`, no ciego).
- 🟡 RELEASE — REL-B y REL-C ✅; REL-A ❌ solo por A5 (reformulación pendiente); REL-D sin publicar ([ficha](RELEASE_2026-09-24.md)).
- ◻️ Validación física — después del software.
- ◻️ METAVERSE-1 — último.

### Programa técnico

Objetivo: desarrollar un yo funcional situado de ECHO-AI: distinguir cuerpo
y entorno, atribuir efectos de sus acciones, conservar continuidad de
aprendizaje, regular necesidades propias y reconocer límites de su control.
No equivale a personalidad narrativa ni acredita conciencia subjetiva.

Se integra con la base existente de SELF-1, CAUSE-1, homeostasis, memoria,
transferencia y gate. No se sustituye el roadmap, no se duplica el núcleo
y no se reetiquetan certificados históricos. ECHO-3 conserva sus 14/15 y
pendientes físicos; estos no bloquean el nuevo tramo exclusivamente software,
por instrucción expresa del usuario del 21/09.

Secuencia oficial publicada, con un contrato y KPI por slice:

```text
WORLD → SENSATION → BOUNDARY → SELF → CONTINUITY → MAINTAIN
      → OTHER → INTERACTION → RELATION → ROLES → INTEGRATE
      → RELEASE-1 (paquete/publicación software) → validación física
      → METAVERSE-1 (último)

CONTINUITY → DREAM-1 (rama cortical offline opt-in) → evaluación en INTEGRATE
```

- **E4-WORLD-1 implementado:** mundo renovable entero, verificador de
  48.006 transiciones y testigo sostenible. 45 tests nuevos + 48 de regresión
  seleccionada. El agente sin entrenamiento previo muere a los 37 turnos:
  factibilidad física demostrada, mantenimiento aprendido pendiente.
- **E4-SENSATION-1 cerrada en predicción sensorial nominal:** historia 2
  gana +218/+203 aciertos frente a T en B/C con modelo congelado. 145 pruebas
  pasan y la auditoría completa reproduce `96f2deae…` sin hallazgos.
  No demuestra mantenimiento ni causa propia/externa.
  [Cierre](ECHO4-SENSATION1-CLOSURE.md) y [contrato](ECHO4-SENSATION1-PREDICTOR-V1.md).
- **E4-BOUNDARY-1 cerrada en intervenciones virtuales emparejadas:**
  1.408/1.408 máscaras correctas en B y en C, frente a 778/765 por coincidencia
  temporal. Cero falsas influencias; 512/512 abstenciones ante inválidos por
  etapa. 179 pruebas y auditoría reproducida, certificado `48789bd5…`.
  Requiere restauración experimental confiable; no acredita pertenencia corporal.
  [Contrato](ECHO4-BOUNDARY1-DESIGN.md) · [Resultados](ECHO4-BOUNDARY1-RESULTS.md).
- **E4-SELF-1 cerrada en WORLD-1 bajo el contrato final:** antecedentes preservados:
  SELF-A conserva referencia y documenta 3.256
  condiciones ambiguas con su protocolo corto. SELF-B añade referencia larga,
  hipótesis condicionadas a física conocida y selección de ensayos:
  7.920/7.920 atribuciones correctas, cero errores/terminalidades en desarrollo.
  Igual precisión que orden fijo con 66.660 frente a 133.320 pasos de diagnóstico;
  sin referencia larga quedan 1.632 desconocidos. Restauración experimental
  confiable y familia de perturbaciones explícita, no causalidad general.
  236 pruebas pasan y replay completo válido (`06fae2d4…`); `self1_green=false`.
  **SELF-C v1 implementada, criterio conductual rojo:** integra decisión y
  protección T/SENSATION en el loop nativo. Retiene 119/119 actualizaciones
  con efecto corporal y admite 4.801 legítimas. Completa 126/126 casos
  viables, igual que el control; en los 114 inviables se detiene sin morir.
  272 pruebas pasan; replay completo válido (`15d8bfba…`). No se confunde protección o parada segura con ventaja
  en tareas completadas. **SELF-C v2 verde en reutilización controlada:**
  114/144 objetivos en desarrollo y 108/144 en confirmación, frente a
  99/144 y 90/144 sin protección. También supera congelar todo y no consultar
  T, sin pérdidas emparejadas. Retiene 540/540 y 648/648 actualizaciones;
  admite aprendizaje externo. 302 pruebas y replay completo (`74bbdfdd…`).
  El ejecutor restaura el cuerpo: no autorreparación. En mixtas falla 30/72
  y 36/72, sin ventaja sobre aprenderlo todo en ese grupo.
  **Cierre final nuevo A/B/C:** confirmación de diagnóstico antes de autorizar,
  80/80 causas correctas por fase. B 189/240 y C 193/240 objetivos, frente a
  152/240 y 143/240 sin protección; también supera los otros dos controles.
  B/C: 40/40 vidas viables completadas y 40 paradas inviables por fase;
  en A completa 40/44 viables, no todas. 48/48 abstenciones por fase, más
  veto nativo y testigos de insuficiencia/indistinguibilidad.
  329 pruebas y replay de A/B/C y seis padres válido: `self1_green=true`
  solo en el recibo (`98ffc1ca…`). Fuera del prior hay 3/4/4 terminalidades;
  no acredita seguridad arbitraria ni reparación autónoma. Base conservada para CONTINUITY.
  No reabre el SELF-1 histórico.
  [Etapas](ECHO4-SELF1-DESIGN.md) · [SELF-A](ECHO4-SELF1-A-RESULTS.md) ·
  [Contrato SELF-B](ECHO4-SELF1-B-DESIGN.md) · [Resultados SELF-B](ECHO4-SELF1-B-RESULTS.md).
  [Contrato SELF-C](ECHO4-SELF1-C-DESIGN.md) · [Resultado rojo SELF-C v1](ECHO4-SELF1-C-RESULTS.md).
  [Contrato SELF-C v2](ECHO4-SELF1-C-V2-DESIGN.md) · [Resultados y límites v2](ECHO4-SELF1-C-V2-RESULTS.md).
  [Contrato final](ECHO4-SELF1-FINAL-DESIGN.md) · [Cierre y reproducción](ECHO4-SELF1-FINAL-RESULTS.md).
- **E4-CONTINUITY-1 cerrada en los perfiles síncronos WORLD-1 declarados:** CONT-A guarda/restaura el estado de
  `SelfAgent`/WORLD-1 nominal entre turnos completos, con formato cerrado,
  procedencia, cuerpo, relojes, contexto y memoria; compara continuación en
  proceso nuevo. CONT-B añade sesiones SELF, planes pendientes, buzón de
  recibos, confirmación y recuperación/reutilización con permisos originales.
  CONT-C añade cambio de cuerpo, descendencia y bifurcación virtual explícitos:
  memoria heredada sin permisos del cuerpo anterior, cuarentena y recalibración;
  ámbitos separados y relojes propios frente a heredados. 30 tests pasan;
  banco 21/21 escenarios, 125/125 eventos y 43/43 turnos posteriores idénticos,
  reconstrucción independiente válida sin hallazgos. **CONT-D cierra el conjunto:**
  examen nuevo A/B/C, 23/23 escenarios por etapa, fuentes congeladas antes de B;
  300/300 eventos y 186/186 turnos posteriores idénticos, 30/30 mutantes.
  Replay íntegro y auditorías de los tres componentes válidos; recibo
  `continuity1_green=true` (`69d57a0b…`). 33 tests nuevos, 905 en total con
  regresiones, un único fallo esperado histórico. Historia omitida pierde
  aprendizaje PATTERN pero no cambia acciones/predicciones en estos controles;
  restos Q comprobados además por testigo aritmético sintético separado.
  No identidad subjetiva, reparación autónoma ni exclusividad distribuida.
  29 tests nuevos, cinco escenarios y 52/52 pasos idénticos en procesos
  nuevos para CONT-A, revalidado. CONT-B: 37 tests nuevos, 18/18 casos,
  142/142 eventos y 67/67 turnos posteriores idénticos; reconstrucción
  independiente válida sin hallazgos. Conserva terminalidad y relojes
  global/local separados, sin cambiar las fuentes selladas SELF/CONT-A.
  [Contrato y pendientes](ECHO4-CONTINUITY1-DESIGN.md) ·
  [Resultados CONT-A](ECHO4-CONTINUITY1-A-RESULTS.md) ·
  [Contrato CONT-B](ECHO4-CONTINUITY1-B-DESIGN.md) ·
  [Resultados CONT-B](ECHO4-CONTINUITY1-B-RESULTS.md) ·
  [Contrato CONT-C](ECHO4-CONTINUITY1-C-DESIGN.md) ·
  [Resultados CONT-C](ECHO4-CONTINUITY1-C-RESULTS.md) ·
  [Contrato CONT-D](ECHO4-CONTINUITY1-D-DESIGN.md) ·
  [Cierre conjunto y límites](ECHO4-CONTINUITY1-D-RESULTS.md).
- **E4-DREAM-1 cerrada en su perfil WORLD-1 restaurado:** DREAM-A inicia archivo privado
  de intentos nativos WORLD-1 y replay público con revelación parcial,
  presupuesto entero, ausencia de resultados para ramas no observadas y
  checkpoints del custodio separados. No se fusionan estados por igual WSP.
  Los ensayos normal/greedy usan flags originales, no Qwen ni políticas
  autoescritas. El banco es de integridad, no de ganancia de exploración.
  Tres árboles, 31 nodos y 28 intentos; 62 consultas replay, 32 desconocidos
  y dos respuestas de terminalidad. Reconstrucción válida (`011cc0d9…`).
  [Contrato DREAM-A](ECHO4-DREAM1-A-DESIGN.md) · [Resultados](ECHO4-DREAM1-A-RESULTS.md).
  **B/C/D implementados y evaluados:** adaptador offline local separado del
  cable de letreros; Qwen3-4B-Instruct-2507 Q4_K_M, pesos fijos, seis llamadas
  reales, 24 propuestas válidas. Intérprete de catálogo seguro, replay parcial,
  selección con incumbente y tres ciclos con examen nuevo, historial ampliado,
  versión y reversión. Sin código arbitrario ni cambios del núcleo/gate.
  Mejora histórica inicial de 60 a 80/80 diagnósticos, pero no generaliza:
  130/240 frente a fijo 150/240, aleatorio 155/240 y sin Qwen 165/240.
  DREAM usa 1.920 pasos frente a 2.880 del fijo; ese ahorro con menos aciertos
  no cumple el criterio. Auditoría completa válida, cero errores/terminalidades
  en los siete brazos, invariantes intactos. **DREAM-D v1 rojo, preservado.**
  **DREAM-D v2 implementada:** Qwen recibe feedback del replay, se selecciona
  por peor margen histórico y se compara promoción con el fijo original.
  Tres ciclos estratificados nuevos, 320 casos por brazo: 245/245/240,
  frente a fijo 180/210/200 y aleatorio 206/230/238. Nueve llamadas reales,
  36 propuestas válidas, nueve brazos. V2 también roja: falla el +16 frente
  al aleatorio en los ciclos 2/3; el agregado favorable no sustituye el criterio.
  Cero errores/terminalidades y paridad exacta; sin Qwen empata en todos los
  ciclos. 890 pruebas pasan, un fallo esperado histórico. Su cota del catálogo
  motivó v3, no un cambio de umbral para recolorear v2.
  [Resultados v2](ECHO4-DREAM1-D-V2-RESULTS.md).
  **DREAM-D v3 verde:** dos ensayos nuevos y archivo condicional; 15 llamadas
  reales, 60 propuestas válidas. Nuevos exámenes: 300/298/302 frente a fijo
  190/230/220 y aleatorio 238/246/237; todos los márgenes por ciclo pasan.
  Cero errores/terminalidades, paridad exacta y auditoría válida (`965ce6cb…`),
  `dream1_green=true`. 925 tests pasan y un fallo esperado; 82 fuentes intactas.
  Sin Qwen/sin feedback empatan; una promoción inicial, no mejora ilimitada.
  [Cierre v3 y límites](ECHO4-DREAM1-D-V3-RESULTS.md).
  El banco basal conserva `cortex_calls=0`; los costes corticales se declaran.
  [Contrato B/C/D](ECHO4-DREAM1-BCD-DESIGN.md) ·
  [Resultados completos y siguiente trabajo](ECHO4-DREAM1-BCD-RESULTS.md).
  [Subfases DREAM-A/B/C/D y límites](ECHO4-DREAM1-PLAN.md).
- **E4-MAINTAIN-1 cerrada en su perfil virtual:** MAINT-A añade un entorno opt-in
  que reutiliza la física WORLD-1 y el Agent original. Un ciclo de tres
  enfriamientos consume tiempo, energía y repuesto; el fallo obstruido puede
  repararse, el averiado no, y el calor externo no desaparece. Los guiones del
  banco son testigos mecánicos, no decisión autónoma. Sin reset ni resurrección,
  con veto, parada y trabajo medidos. B decide por evidencia parcial con un
  modelo mecánico declarado; C conserva vidas/estado y D confirma el beneficio
  en cohortes nuevas. 144/144 recuperables completas, 192/192 reparaciones
  confirmadas; trabajo 9450 frente a fijo 7501, controles y límites publicados.
  Auditoría reconstructiva válida, `maintain1_green=true` (`7e1c0e82…`).
  42 pruebas nuevas y 12 continuaciones exactas. No política descubierta
  por Q desde cero, reparación general ni conciencia.
  [Cierre B/C/D](ECHO4-MAINTAIN1-FINAL-RESULTS.md).
  [Diseño y criterios](ECHO4-MAINTAIN1-A-DESIGN.md).
  [Resultado A](ECHO4-MAINTAIN1-A-RESULTS.md): 216 episodios y cuatro testigos,
  235 tests, reconstrucción válida (`ec4a6d1e…`). No cerrar por cumplir
  integridad: el guion indiscriminado pierde y la Q sin guion muere.
- **E4-OTHER-1 cerrada en su perfil observacional discreto:** dos Agent
  nativos aprenden tareas privadas y modelan la conducta pública del otro
  en su CAM/T original. Sin acceso a preferencias, recompensas o memoria
  ajenas. Dos cohortes: 1536/1536 frente a pooled 1008/1536, self-copy 0 y
  no-history 0; en iguales, self-copy empata. 40 pruebas nuevas, 12 controles
  y dos replays públicos en procesos nuevos; auditoría completa válida,
  `other1_green=true` (`1263f11a…`). 99 fuentes, las 93 previas intactas.
  Con datos ausentes o contradicción se abstiene; no borra memoria.
  No teoría de la mente general ni conciencia; la coordinación útil se
  contrasta por separado en INTERACTION. No está integrado con el
  cuerpo térmico de MAINTAIN; se exige en INTEGRATE.
  [Contrato](ECHO4-OTHER1-DESIGN.md) · [Cierre y límites](ECHO4-OTHER1-RESULTS.md).
- **E4-INTERACTION-1 cerrada en su perfil B/C/D:** creencias no factuales de
  OTHER indexan Q nativa; dos contrapartes con objetivos privados declarados.
  Ganancia focal posformación +12,5% frente a solo/ablaciones en ambas cohortes;
  neto conjunto +50%, incentivos privados excluidos. 37 pruebas nuevas,
  11 escenarios adversos, orden inverso y replay exactos. Auditoría válida,
  `interaction1_green=true` (`d1c5b073…`), 110 fuentes, 104 ancestrales intactas.
  El aprendiz no recupera su coste de formación en las 480 rondas: la ventaja
  es posterior, no de vida completa. No conciencia ni integración térmica.
  [Contrato B/C/D](ECHO4-INTERACTION1-BCD-DESIGN.md) ·
  [Cierre, costes y límites](ECHO4-INTERACTION1-BCD-RESULTS.md).
  El [resultado inicial de A](ECHO4-INTERACTION1-A-RESULTS.md), sin beneficio
  de OTHER y con pérdida de Q simétrica en una semilla, permanece intacto.
- **E4-RELATION-1 iniciada, A verificada:** episodios de acciones observadas,
  costes y resultados propios en CAM, orden global y por contraparte; no
  confundir ausencia con aceptación ni atribuir identidad a recibos anónimos.
  912 episodios primarios reconstruidos, misma política/coste que el control
  sin grabación. 36 pruebas nuevas, 181 con regresiones seleccionadas; auditoría
  válida (`ce24ccaa…`), 115 fuentes, las 110 previas intactas. Fase aún abierta,
  `relation1_green=false`: registrar historia no acredita ventaja transferible.
  Siguiente B, luego C/D. Sin LLM ni continuidad completa de sesión social.
  [Contrato y etapas](ECHO4-RELATION1-A-DESIGN.md) ·
  [Resultados y límites](ECHO4-RELATION1-A-RESULTS.md).
- **E4-RELEASE-1 añadida, PLAN:** fase final del producto software tras
  INTEGRATE. REL-A resuelve paquete/dependencias; REL-B verifica runtime
  rápido/lento y fallos; REL-C revisa licencias, tarjetas y privacidad;
  REL-D publica con autorización y reproduce una descarga limpia de Hugging
  Face. Código estable versionado, referencia a pesos originales y continuidad
  del desarrollo del laboratorio. No fusión de relojes dentro de los pesos,
  ni publicación de checkpoints privados. [README](../echo4/README.md).
- Mantenimiento cierra solo su perfil declarado; integración sigue pendiente. DREAM no bloquea el
  desarrollo basal sin LLM; se contrastará aparte en INTEGRATE. No hay un
  `echo4_green` por añadir esta lista.

Sin hardware, METAVERSE-1, PX4/Gazebo ni LLM como requisitos del programa basal.
La rama DREAM ya utiliza el modelo local en su ensayo separado,
sin convertirlo en requisito de ejecución de los otros bancos.
Se mantienen WSP único de 16 bytes, CAM sin borrado, Q/T/gate existentes,
camino rápido entero y autoridad del operador. La atribución no crea hechos
verificados por declararlos propios.

**Conciencia subjetiva:** ninguna fase concede esa acreditación. Los verdes
son funcionales. **Autorreparación:** MAINTAIN acredita mantenimiento virtual
condicionado a un modelo conocido, con costes y controles; se contrasta en INTEGRATE y, si es
física, en hardware. Restauración por el ejecutor no es reparación autónoma.

Contraparte, interacción, historia compartida y roles adaptativos forman parte
del programa ampliado autorizado. Reproducción y evolución siguen fuera del
cierre. El hardware se validará en su propio tramo después del software;
METAVERSE-1 queda al final y su presentación no decide la cognición.
[Roadmap público](https://www.rxlabs.org/docs/echoai/echo4).

[Programa y criterios del ego](ECHO4-EGO-PROGRAMA.md) ·
[Diseño WORLD-1](ECHO4-WORLD1-DESIGN.md) ·
[Resultados WORLD-1](ECHO4-WORLD1-RESULTS.md).
