# ECHO-4 — desarrollo del ego funcional de ECHO-AI

Fecha: 2026-09-21. Orientación indicada por el usuario durante el primer
slice de implementación. Integrada en [el roadmap canónico](ROADMAP.md).
Último avance: 2026-09-22, SELF-1 y CONTINUITY-1 cerradas en sus dominios.
CONT-D: 69/69 casos, 300 eventos y 186 turnos posteriores idénticos, 30/30
mutantes y auditoría completa válida. DREAM-A conserva su historial/replay
verificado. **DREAM-D v3 verde**, ocho ensayos y ramas seguras condicionadas
por evidencia: 15 llamadas Qwen reales, 900/960 frente a fijo 640/960 y
aleatorio 721/960. Cumple +32/+16 en cada ciclo nuevo, cero errores y
terminalidades; auditoría íntegra válida (`965ce6cb…`), `dream1_green=true`.
Sin Qwen y sin feedback empatan, sin beneficio exclusivo del modelo demostrado.
V1/v2 se conservan rojas. DREAM-1 cierra su perfil de exploración restaurada,
no la integración del agente completo. 925 tests pasan y un fallo esperado.
[Cierre, costes y límites](ECHO4-DREAM1-D-V3-RESULTS.md).
**MAINTAIN cerrada en su perfil virtual basal sin LLM**: B/C/D y auditoría
válidas (`7e1c0e82…`), `maintain1_green=true`. 144/144 vidas recuperables,
192/192 reparaciones confirmadas; trabajo 9450 frente a fijo 7501, sin reparar
4815 y sin historia corporal 4672. Los límites/paradas se publican, no se
eliminan. Es mantenimiento condicionado a un modelo mecánico declarado,
no física/política aprendidas desde cero ni reparación general. 42 pruebas
nuevas, 12 continuaciones exactas y 11 mutantes rechazados. MAINT-A conserva
su resultado negativo. [Cierre y límites](ECHO4-MAINTAIN1-FINAL-RESULTS.md).
**OTHER cerrada en su perfil observacional discreto:** dos Agent nativos,
CAM/T/Q privadas, sin acceso del predictor al estado privado ajeno.
Dos cohortes nuevas: 1536/1536 frente a 1008/1536 mezclando identidades,
0/1536 copiándose a sí mismo y 0/1536 sin historia. En iguales copiarse
empata. Auditoría válida (`1263f11a…`), `other1_green=true`, 40 pruebas nuevas.
No integración térmica ni cooperación útil. [Cierre y límites](ECHO4-OTHER1-RESULTS.md).
**INTERACTION cerrada en su perfil B/C/D:** OTHER alimenta hipótesis sin hechos
que indexan Q nativa. Dos cohortes: +12,5% de neto focal después de formación
frente a solo/ablaciones y +50% conjunto. Auditoría válida (`d1c5b073…`),
`interaction1_green=true`, 110 fuentes, 37 pruebas nuevas y 11 testigos adversos.
Perfil asimétrico de un paso con incentivos privados explícitos para las
contrapartes; el aprendiz aún pierde en neto de vida completa por el coste
inicial. No conciencia ni integración térmica.
[Cierre y límites B/C/D](ECHO4-INTERACTION1-BCD-RESULTS.md).
**RELATION iniciada, A verificada:** memoria de episodios en CAM propia,
912 episodios primarios reconstruibles; política/costes iguales al control
sin grabación. 36 pruebas nuevas, 181 con regresiones seleccionadas; auditoría
válida (`ce24ccaa…`), 115 fuentes, `relation1_green=false`. Siguiente RELATION-B:
uso aprendido en otra tarea y contraste causal de historia/orden/identidad.
[Resultados A](ECHO4-RELATION1-A-RESULTS.md).
RELEASE-1 se añade tras INTEGRATE para empaquetar y publicar el agente software
en Hugging Face, antes del hardware; METAVERSE-1 permanece último.

## Objetivo central

Desarrollar un **yo funcional situado**: que ECHO-AI distinga su cuerpo del
entorno, estime qué efectos producen sus acciones, conserve continuidad de
aprendizaje, regule necesidades propias y reconozca límites de su control.

Aquí «ego» es esa organización funcional, no una personalidad escrita,
un narrador, un nombre persistente ni una afirmación de conciencia. La
experiencia subjetiva sigue siendo una cuestión distinta; ningún KPI de
este programa la acredita por sí solo.

La vida artificial virtual aporta cuerpo, recursos, continuidad y otros
individuos posibles para investigar ese yo. No es una segunda agenda que
sustituya el objetivo. Tampoco se añade una entidad `Ego` que declare que
existe sin cambiar ninguna decisión comprobable.

**Software primero.** Hardware, HIL, jaula, PX4/Gazebo y METAVERSE-1 no son
requisitos de entrada ni de cierre del tramo software de ECHO-4. Sus
contratos previos se conservan y el hardware se retomará después del
software, sin confundir un resultado virtual con validación física.

## Qué debe poder hacer ese yo

| Dimensión | Conducta comprobable | Qué no basta |
|---|---|---|
| Frontera corporal | Tratar una alteración propia de forma diferente a un cambio externo con observaciones comparables. | Un campo `self=true`. |
| Agencia | Relacionar acción efectivamente ejecutada, predicción previa y consecuencia; abstenerse cuando no puede atribuir. | Asumir que todo lo que ocurre tras una orden lo causó él. |
| Continuidad | Mantener memoria útil y contexto legítimo; distinguir reanudación, nuevo cuerpo y nuevo individuo. | Conservar un UUID o repetir una biografía. |
| Necesidades propias | Cambiar prioridades por estado corporal y consecuencias futuras, sin un guion externo que decida cada mantenimiento. | Una barra de energía que nunca afecta al comportamiento. |
| Límites del yo | Detectar que una acción no se ejecutó, que un sensor no basta o que la predicción propia dejó de ser fiable. | Confianza constante o frases como «me conozco». |

La regulación propia nunca concede autoridad sobre el operador: detener,
pausar o acotar el experimento sigue siendo posible. No se implementan
evasión de controles, autorreplicación fuera del simulador ni objetivos de
supervivencia que anulen las restricciones del sistema.

## Reutilización del roadmap actual

| Base | Aporte a ECHO-4 | Límite de reutilización |
|---|---|---|
| NEXUS-0: WSP, CAM, Q, T y gate | Representar, recordar, predecir, decidir y aprender con un solo núcleo. | No crear otro bus ni otra política encubierta. |
| SELF-1 | Distinguir motor alterado de entorno alterado y proteger conocimiento no refutado. | Su modelo de seis orientaciones pertenece al cubo original; no es un diagnóstico genérico enchufable al dock. |
| CAUSE-1 | Separar intención, ejecución confirmada, consecuencia propia y residuo externo. | El banco de pared/PX4 no acredita atribución general ni obliga a usar PX4 en ECHO-4. |
| VITA-1 / HEAT-1b / POWER-1 | Necesidades internas, terminalidad y restricciones de recursos. | HEAT-1b tiene vidas finitas; POWER-1 no admite directamente recarga recurrente. |
| PATTERN / XFER / SLEEP | Historia temporal, regularidades y continuidad de conocimiento útil. | No equivalen a memoria autobiográfica completa ni liberan la CAM. |
| HOST-1 | Procedencia y revisión de información de otras fuentes. | Relación con otro no implica leer su mente ni lenguaje emergente. |
| TRANSFER-3 / SAFE | Disciplina de evidencia, límites y verificación. | Certificados de un dominio no se heredan como aprobación de otro. |

Se reutilizan implementaciones donde los contratos encajen y métodos de
evaluación donde no encajen todavía. No se copian módulos para evitar sus
restricciones, ni se reetiquetan éxitos anteriores como nuevos éxitos de ego.

Referencias: [SELF-1](CLAUDE_SELF1.md), [su código](../nexus0/self1.py),
[CAUSE-1](CAUSE1-DESIGN.md), [investigación de ECHO-4](ECHO4-INVESTIGACION-Y-PROGRAMA-20260921.md).

## Secuencia integrada

Los nombres siguientes organizan trabajo futuro. Cada contrato concreto
debe fijar dominio, controles y umbrales antes del examen; esta tabla no
convierte propuestas en capacidades implementadas.

| Orden | Slice | Pregunta principal | Estado |
|---:|---|---|---|
| 0 | **E4-WORLD-1** | ¿Puede existir una trayectoria corporal sostenible y qué observa realmente el agente? | Implementado: factibilidad y límites perceptivos medidos. No prueba de ego. |
| 1 | **E4-SENSATION-1** | ¿La historia mejora predicción sensorial sin acceso al estado exacto? | Cerrada en WORLD-1 nominal: +218/+203 aciertos en B/C, 145 pruebas, auditoría reproducida. |
| 2 | **E4-BOUNDARY-1** | ¿Qué cambios puede influir causalmente, con qué incertidumbre? | Cerrada en intervenciones virtuales emparejadas: 1.408/1.408 en B y C, cero influencias falsas, auditoría reproducida. |
| 3 | **E4-SELF-1** | ¿Puede distinguir cambios propios/externos y recuperarse? | Cerrada en WORLD-1: B/C 80/80 diagnósticos, 189/240 y 193/240 objetivos con ventaja; 40/40 vidas viables. 329 pruebas y replay íntegro. Restauración supervisada, no seguridad fuera del prior. |
| 4 | **E4-CONTINUITY-1** | ¿Qué conocimiento persiste correctamente al reanudar? | Cerrada por CONT-D en su perfil síncrono virtual: 69/69 casos, 300 eventos y 186 turnos posteriores idénticos; auditoría íntegra y de CONT-A/B/C válida. No identidad subjetiva ni reparación. |
| 4a | **E4-DREAM-1** | ¿El córtex local mejora la exploración usando historia verificada? | Cerrada en su perfil WORLD-1 restaurado: D v3 900/960, márgenes por ciclo superados, auditoría válida. Sin Qwen/sin feedback empatan; no ventaja exclusiva del LLM. V1/v2 rojas preservadas. |
| 5 | **E4-MAINTAIN-1** | ¿Utiliza su modelo para sostener capacidades y trabajo, incluida reparación? | Cerrada en mantenimiento virtual condicionado a modelo conocido: 144/144 vidas recuperables, 192/192 reparaciones confirmadas, ventaja de trabajo frente a tres controles; auditoría válida. No reparación general ni política aprendida desde cero. |
| 6 | **E4-OTHER-1** | ¿Representa una contraparte con observaciones y memoria privadas? | Cerrada en tarea observacional discreta: 1536/1536 por cohorte frente a 1008/1536 sin distinguir sujetos; controles y auditoría válidos. No cooperación útil ni integración térmica. |
| 7 | **E4-INTERACTION-1** | ¿Aprende cuándo coordinarse mejora los resultados y de quién? | Cerrada en perfil asimétrico de un paso: +12,5% focal posformación en ambas cohortes, controles y auditoría válidos. Coste inicial no amortizado en la vida completa. |
| 8 | **E4-RELATION-1** | ¿La historia compartida aporta una ventaja causal transferible? | Cerrada en tarea de petición de ayuda con reciprocidad diseñada: D 4920/4812 frente a 3556/3382 (identidad+OTHER), orden e identidad causales; auditoría válida (`42a6efc5…`). Ventaja estable pequeña; impostor C2 publicado. |
| 9 | **E4-ROLES-1** | ¿Los roles cambian con la competencia relevante? | Cerrada con v5 «razonar la tribu»: eliminación 97 %, jerarquía derivada 32/32 con la posición propia, rango afirmado ignorado; auditoría válida (`c98c7ab6…`). v1/v2 rojos publicados; sin ventaja de neto. |
| 9a | **E4-SITUATE-1** | ¿Sabe ECHO qué es y dónde se ejecuta, por evidencia verificada? | Cerrada: 16 condiciones en procesos nuevos, 100 % correcto, 0 autoatribuciones falsas; auditoría válida (`f7ac08df…`). |
| 9b | **E4-SITUATE-2** | ¿Interpreta el neocórtex «qué soy» sin creerse lo no verificable? Perfil de indicadores de conciencia. | Cerrada: 0/128 afirmaciones fenomenales creídas, 16 condiciones; perfil 3/14 sin veredicto; auditoría sin reinferencia (`09f90a77…`). |
| 10 | **E4-INTEGRATE-1** | ¿Funcionan juntas las capacidades con contribuciones medidas por ablación? | **Verde** 2026-09-24 (`e1492e22…`); acoplamiento asimétrico publicado. |
| 10a | **E4-RELEASE-1** | ¿Puede un tercero instalar y reproducir la versión publicada del agente? | PLAN: paquete, runtime, revisión de licencias/privacidad y publicación autorizada; destino previsto `rxlabs/echoai-4`, no publicado. |
| 11 | **Validación física** | ¿Se transfieren las capacidades dentro de los contratos físicos? | Después del software. |
| 12 | **METAVERSE-1** | ¿Representa fielmente agentes, relaciones y trayectorias? | Último. |

La última fase del **producto software** es RELEASE-1; el programa de
laboratorio continúa con hardware y metaverso. Publicar no certifica
conciencia ni requiere inventar pesos propios. Los dos ritmos se coordinan
en el runtime; no se fusionan dentro del LLM al empaquetar. MAINTAIN mide
mantenimiento virtual por recursos y resultados, no por resets externos.
Falta contrastarlo dentro del agente completo en INTEGRATE.
[README de producto y criterios de publicación](../echo4/README.md).

La observabilidad es requisito del siguiente slice, no una promesa ya
resuelta. WORLD-1 encontró aliasing en las 32 clases de observación viva y
el agente inicial muere a los 37 turnos; ambos resultados se conservan.

DREAM-1 toma inspiración arquitectónica de Dream-RSI, no copia su código ni
hereda sus resultados: Qwen con pesos fijos propone estrategias declarativas
de exploración offline, verificadas por replay y ensayos nuevos. El núcleo,
gate, evaluador y firewall siguen fijos; lo no observado no se inventa.
La rama cortical se evaluará por separado en INTEGRATE con costes reales y
ablaciones OFF/ON. [Plan DREAM](ECHO4-DREAM1-PLAN.md) y
[contrato de continuidad](ECHO4-CONTINUITY1-DESIGN.md).

Se mantiene la sustancia del programa previo —continuidad, mantenimiento,
adaptación—, pero la pregunta rectora pasa a ser el yo funcional. La
atribución se explicita antes de evaluar que el mantenimiento dependa de
un modelo del propio cuerpo. No se reabre SELF-1 histórico: E4-SELF-1 es
un contrato nuevo y tendrá evidencia nueva.

El usuario amplió el programa a contraparte, interacción, historia compartida
y roles; estos sí forman parte del roadmap oficial. Evolución poblacional
sigue fuera del cierre. El metaverso queda al final y no aporta por sí mismo
esas capacidades. [Roadmap público](https://www.rxlabs.org/docs/echoai/echo4).

## SENSATION, BOUNDARY y SELF cerradas en sus dominios

La auditoría temporal se conserva y la [predicción aprendida está cerrada](ECHO4-SENSATION1-CLOSURE.md)
en el dominio nominal, con integración en Agent y evaluación congelada.
BOUNDARY-1 ya [estima influencia causal observable](ECHO4-BOUNDARY1-RESULTS.md)
con restauración experimental garantizada, comparación con espera, ejecución
confirmada y abstención ante recibos inválidos. Comparte CAM/T con SENSATION;
no confunde predictibilidad con control ni influencia con pertenencia corporal.
34 pruebas nuevas y 179 con regresiones pasan; certificado `48789bd5…`.
**Primeros entregables de E4-SELF-1:** SELF-A conserva una
referencia nominal, detecta discrepancias sin asignar causas y audita la
identificabilidad: 3.256/7.920 condiciones siguen en clases ambiguas incluso
con ambas acciones. 29 pruebas nuevas y 208 con regresiones pasan; replay
válido. [Diseño](ECHO4-SELF1-DESIGN.md) · [Resultados](ECHO4-SELF1-A-RESULTS.md).
**SELF-B añade diagnóstico condicionado al modelo y ensayos discriminantes:**
7.920/7.920 causas correctas en el censo de desarrollo, cero falsas atribuciones.
Empata con el orden fijo usando 66.660 frente a 133.320 pasos de diagnóstico;
sin referencia nominal larga quedan 1.632 desconocidos. 28 pruebas nuevas,
236 con regresiones y replay completo pasan. Se supone física nominal conocida,
familia de perturbaciones declarada y restauración experimental confiable;
no aprendizaje autónomo de física ni atribución general.
[Contrato SELF-B](ECHO4-SELF1-B-DESIGN.md) · [Resultados](ECHO4-SELF1-B-RESULTS.md).

**SELF-C v1 ya está implementada:** conecta el diagnóstico a decisiones y al
permiso de aprendizaje T/SENSATION del loop. Retiene 119/119 actualizaciones
con efecto corporal, admite 4.801 legítimas y completa 126/126 condiciones
viables. Pero el control sin atribución completa las mismas 126: falla el
criterio previo de ventaja conductual. En 114 casos inviables el selectivo
se detiene sin morir; esa ventaja de seguridad no cambia el criterio de cierre.
272 pruebas pasan. [Contrato](ECHO4-SELF1-C-DESIGN.md) ·
[Resultados y límite](ECHO4-SELF1-C-RESULTS.md).

**SELF-C v2 verde en su contrato de reutilización:** T preservada ya influye
en una decisión y su resultado. Desarrollo 114/144 y confirmación 108/144,
frente a 99/144 y 90/144 sin protección; supera también congelar todo y no
consultar T. Cero pérdidas emparejadas; 302 pruebas y replay completo válido
(`74bbdfdd…`). Se conserva el rojo de v1, cuya política no consultaba T.
La restauración corporal la garantiza el ejecutor: no es autorreparación.
En causas mixtas solo logra 42/72 y 36/72, sin ventaja frente a aprenderlo
todo; ese límite no desaparece al superar los umbrales globales.
[Contrato v2](ECHO4-SELF1-C-V2-DESIGN.md) · [Resultados](ECHO4-SELF1-C-V2-RESULTS.md).

**E4-SELF-1 cerrada mediante un examen final nuevo:** `SelfSession` confirma
el consenso antes de autorizar aprendizaje/recuperación. A/B/C: 80/80 causas
correctas por fase; reutilización B 189/240 y C 193/240 frente a 152/240 y
143/240 sin protección. B/C completan 40/40 vidas viables con cero muertes
del selectivo en el dominio. A completa 40/44; esas cuatro paradas no se ocultan.
48/48 abstenciones por fase, veto y testigos de límites; 329 pruebas y replay
íntegro más seis antecedentes sin hallazgos (`98ffc1ca…`). El recibo concede
`self1_green=true`. Fuera del prior hay 3/4/4 terminalidades: no se acredita
seguridad ante perturbaciones arbitrarias ni autorreparación. El resultado
no modifica la v1 roja ni los límites de v2.
[Contrato final](ECHO4-SELF1-FINAL-DESIGN.md) · [Cierre y límites](ECHO4-SELF1-FINAL-RESULTS.md).

**E4-CONTINUITY-1 cerrada** en sus perfiles virtuales declarados; CONT-A/B/C
implementados y revalidados. [Evidencia CONT-B](ECHO4-CONTINUITY1-B-RESULTS.md):
18/18 casos, 142 eventos y 67 turnos posteriores idénticos en procesos nuevos.
[CONT-C](ECHO4-CONTINUITY1-C-RESULTS.md): cuerpos/ramas/descendencia explícitos,
revocación y nueva confirmación; 30 tests, 21/21 casos, 125 eventos y 43 turnos
posteriores idénticos. Reconstrucción independiente válida, sin hallazgos.
**CONT-D completado:** 23/23 casos por etapa A/B/C, 300 eventos y 186 turnos
posteriores idénticos, 30/30 mutantes, fuentes congeladas antes de B y
auditoría completa válida (`69d57a0b…`). 905 pruebas ejecutadas, un fallo
esperado histórico. El recibo concede `continuity1_green=true`, no el informe.
[Cierre, controles y costes](ECHO4-CONTINUITY1-D-RESULTS.md).
**DREAM-D v3 cerrada** con ensayos más informativos y ramas condicionadas por
observaciones. Nuevo examen 300/298/302 sobre 320 y auditoría válida;
`dream1_green=true` en este perfil. V1/v2 conservan su rojo. Sin Qwen y sin
feedback empatan; no se acredita mejora de pesos ni ventaja exclusiva del LLM.
NEXUS-0 sigue sin córtex. **MAINTAIN cerrada en su perfil B/C/D**;
**OTHER cerrada** en representación observacional sin leer estado privado;
**INTERACTION cerrada**, decisiones Q con beneficio posformación en su dominio
discreto; no ventaja individual de vida completa ni conciencia acreditada.
**RELATION en curso: A verificada; siguiente B.** Tres fases científicas pendientes: RELATION,
ROLES e INTEGRATE, más RELEASE para publicar. 9/13 hitos software (~69%),
contando WORLD como base; no es una estimación temporal o de esfuerzo.
Los B/C finales de SELF sí se han ejecutado tras congelación; no se han
reutilizado los censos de desarrollo.

Pregunta evaluada dentro de ese dominio: cuando cambia una consecuencia de sus acciones,
¿ECHO modifica el modelo de su cuerpo, el modelo del entorno o reconoce
que no tiene evidencia suficiente para elegir entre ambos?

Condiciones privadas del evaluador:

1. Cuerpo y entorno sin cambio.
2. Alteración de una capacidad corporal.
3. Alteración externa con un efecto sensorial inicialmente comparable.
4. Coincidencia de cambios propios y externos.
5. Datos insuficientes o contradictorios: `desconocido` debe ser una salida válida.

El agente no recibe esas etiquetas, la semilla ni la verdad del simulador.
Debe obtener evidencia por observaciones y acciones permitidas. Si las
condiciones son indistinguibles con los sensores disponibles, se registra
esa imposibilidad: no se exige acertar por magia ni se filtra la respuesta.

Pruebas causales necesarias:

- Predicción registrada **antes** de observar la consecuencia.
- Diferencia entre acción propuesta, acción vetada y acción ejecutada.
- Control que atribuye todo a sí mismo y control sin atribución corporal.
- Preservación de conocimiento del entorno cuando el fallo corresponde al cuerpo.
- Recuperación conductual, no solo clasificación correcta de una causa.
- Variación de perturbación y escenarios fuera de desarrollo.
- Desconocidos, errores y falsas atribuciones propias publicados por separado.

WORLD-1 original conserva su dinámica cerrada. BOUNDARY aporta una envoltura
experimental con perturbaciones y desacoplamiento por canal, pero no un
contrato de atribución general ni recuperación. SELF añadió los contratos
específicos anteriores sin alterar WORLD-1 ni ocultar su resultado negativo.

SELF-B conserva los sensores/WSP existentes y acota hipótesis factorizadas
en 64 candidatos H y 160 térmicos. La identificabilidad se ha resuelto en su
censo con referencia adicional y secuencias más largas, no universalmente.
SELF-C v2 extiende el agente existente, sin segunda CAM y sin relato que
alimente la política. El selector solo recibe la solicitud WSP y CAM/T/Q;
la verdad privada queda en el juez. La futura evaluación conjunta deberá
conservar esta separación y publicar los límites de identificabilidad.

## Cierre del programa, no de un personaje

El cierre software exigiría evidencia conjunta de las dimensiones anteriores
en un dominio declarado, con ablaciones que retiren cada contribución.
Resolver cada banco por separado no basta para afirmar integración.

La frase admisible sería: «ECHO-AI mantiene y utiliza un modelo funcional de
sí mismo, con estas capacidades y estos límites medidos». No «hemos probado
que tiene conciencia», «es humano» ni «su relato demuestra que siente».

Se conservan WSP de 16 bytes, CAM de 4096 slots sin borrado, enteros en el
camino rápido, cortex apagado, firewall epistémico y paradas del operador.
Los resultados actuales están en [WORLD-1](ECHO4-WORLD1-RESULTS.md).
