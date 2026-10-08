# ECHO-4.5 V3 · cierre de módulos en bancos sintéticos

3 de octubre de 2026. **REL, MEM, SYN, VIEW, CONS y GUIDE pasan sus contratos
de esta condición**, con reproducción completa en procesos nuevos. El alcance
fue autorizado por el propietario: medir también utilidad fuera de ARC.
**S6 sigue pendiente y el cierre final de ECHO-4.5 sigue abierto.** No se ha
medido una nueva puntuación oficial ARC ni revertido el seguimiento V2 de 1/128.

El candidato combina objetos y relaciones tipadas, recuerdos verificados,
elección aprendida del orden de búsqueda, composición, ocho vistas y detección
de desacuerdos entre programas. Un banco opcional de 500.000 posiciones ordena
32 esquemas ejecutables. Son contadores asociativos uint8, no 500.000 neuronas
LIF ni pesos de un LLM. Todas las ejecuciones fueron locales, sin modelo ni GPU.

| Módulo | Contraste confirmado | Qué acredita el verde |
|---|---|---|
| REL-DSL-1 | DSL anterior + orden fijo: 64/192; relacional + orden aprendido: 160/192. Ambos órdenes del DSL anterior dan 64; ambos del nuevo dan 160 | Representación y composición relacional útil bajo el mismo límite de trabajo, sin pérdidas por tarea respecto al control |
| ARC-3E-POLICY-1 / MEM | 64 tareas equilibradas directas/composiciones: 228.192 → 184.352 unidades; **19,21 % menos** frente al mejor orden fijo | Aprender cuándo consultar los recuerdos ahorra trabajo; las respuestas se conservan |
| Refinamiento / SYN | Sin memoria, composición 32/32 frente a 0/32 sin refinamiento; composición girada también 32/32 frente a 0/32 | Componer operaciones conocidas resuelve instancias que una operación no resolvió, conservando los casos simples |
| Multi-view / VIEW | Sin memoria: 160/192 → **192/192**, sin pérdidas; regla girada 0/32 → 32/32 | Cambiar el marco permite encontrar reglas orientadas con el mismo presupuesto |
| Consistencia / CONS | En 32 puzzles ambiguos, primera solución: 16 respuestas erróneas; consistencia: 0 errores y **32 abstenciones**. En 32 controles inequívocos ambos aciertan 32/32 | Reconocer desacuerdo evita compromisos sin respaldo suficiente; no significa resolver los 32 casos ambiguos |
| Guía de programas / GUIDE | 4.090/4.096 (99,85 %) con 500k; 1.956/4.096 (47,75 %) con 65k; 109/4.096 (2,66 %) sin guía, con una propuesta por consulta | Recuperación de programas adquiridos a carga alta, bajo cambios de color y posición |

El candidato integrado con memoria, política, vistas y consistencia obtuvo
**192/192** en la batería de seis familias. Esta cifra corresponde a generadores
sintéticos declarados. Las consultas contienen tres destinos frente a los dos
de sus demostraciones, y cambian colores, márgenes y tamaños. La composición
girada no tiene un recibo propio de adquisición. Aun así, las operaciones y
familias del generador fueron diseñadas por el laboratorio; no se acredita
descubrimiento de primitivas desconocidas ni razonamiento general fuera de ellas.

![Mediciones de módulos](../lab/seed/relational-v3-20261003/module-results.png)

Se implementaron `OBJECTS`, `RELATE`, `BIND`, `MAP_OBJECTS` y `RENDER` como
funciones tipadas. La segmentación usa el color dominante del borde, con rechazo
si empata. Los roles disponibles son mayor, menor y superior, con rechazo de
empates. Las relaciones incluyen misma forma, color, fila, columna y todos los
otros objetos. Las ediciones permiten pintar, copiar, borrar o extraer; las
copias solapadas o fuera del marco se rechazan. Es una primera gramática
relacional acotada, no la totalidad de GROUND-1/HIER-1 de ECHO-5.

Los programas se construyen enumerando operaciones, verificando todas las
demostraciones y refinando prefijos con menor error. Las hipótesis de objetos y
sus variables vuelven a resolverse sobre cada entrada: un color concreto no
representa el papel de «fuente». La búsqueda conserva un presupuesto duro y
reutiliza resultados de prefijos. El control sin REL conserva el vocabulario
anterior completo, incluidas sus operaciones de objetos; no se recortó a
rotaciones para fabricar la diferencia. La relación y su orden de enumeración
forman parte del cambio: el experimento no separa ambos efectos entre sí.

![Resultados por familia](../lab/seed/relational-v3-20261003/family-results.png)

La política reutiliza el mecanismo de crédito de `village3`, con tablas nuevas
para las acciones `recall_first` y `search_first`. El verificador nunca consulta
esa tabla para aprobar un programa. `choose` selecciona el orden usando contexto
observable; `begin` registra la decisión; `charge` carga trabajo observado;
`mature` incorpora retornos a los 64 episodios. Hay protección contra tickets
duplicados y doble cargo, y se conserva la atribución de costes tardíos.
Las acciones de verificar/escribir de la aldea no se han importado con sus Q
antiguos. Esta transferencia acredita el ciclo completo para **dos decisiones
de planificación**; no implica que todas las políticas posibles de retención,
escritura y revalidación estén aprendidas.

Se ajustaron 256 episodios por política. Cada estado final conserva 192 retornos
maduros y 64 pendientes. Las decisiones pendientes permanecen pendientes: no
se adelantó artificialmente el reloj para cobrar una recompensa futura. La
confirmación congeló Q y el estado aleatorio entre tareas. Las pruebas de
ingeniería ejercitan también cargos posteriores a la maduración y continuidad
del RNG al reiniciar. El ensayo de rendimiento usa costes de resolución y
éxito en demostraciones; no demuestra por sí solo que retrasar el crédito sea
mejor que aprenderlo inmediatamente en este banco.

El **19,21 %** pertenece a una mezcla de 32 rotaciones directas y 32 composiciones
reutilizables, declarada mediante adenda de desarrollo antes de abrir las
semillas 48000–48031. El ahorro en las seis familias completas es **0,166 %**.
Esta diferencia se publica porque las búsquedas largas dominan la cuenta global.
La política no obtuvo más aciertos que el orden fijo. Q aprendió a evitar la
consulta innecesaria en las rotaciones y a recuperar programas en composiciones.

La intervención causal retiró el recibo de composición: el trabajo pasó de
159.040 a **5.326.494** unidades. Retirar un recibo de otra familia mantuvo
159.040. Las tres condiciones resolvieron las 32 tareas. La memoria aporta ahorro
de búsqueda en ese contraste; la mejora de acierto procede de otras partes del
solver. La adquisición inicial de tres programas costó 193.606 unidades de
búsqueda, y el ajuste de la política nueva 2.022.393. No se contabiliza ese ajuste
como gratuito ni se afirma ahorro neto de todo el entrenamiento en solo 64 tareas.
La verificación de recibos, serialización y carga inicial tienen además coste CPU.

El banco de guía contiene 16.384 motivos binarios de 7×7 por semilla y 32
esquemas: ocho simetrías, con/sin recorte y escala 1/2. Las asociaciones se
adquieren a partir de programas suministrados para este banco y comprobados
contra sus demostraciones antes de actualizar contadores. La guía no descubre
esos programas de forma autónoma. El encoder conserva el motivo bajo cambios
de color y margen. El solver solo recibe las demostraciones y entradas de test;
un juez separado calcula la exactitud de las predicciones.

500k superó a 65k en las ocho semillas, con **52,10 puntos porcentuales** de
ventaja agregada y p=0,00390625 en el contraste unilateral de signos previsto.
Las réplicas independientes son las ocho semillas, no las 4.096 consultas.
Las seis consultas que 500k no resolvió se rechazaron por no ajustar las
demostraciones. No hubo respuestas erróneas comprometidas en ninguno de los
cuatro brazos. La búsqueda sin guía sobre los 32 programas obtuvo **4.096/4.096**;
la ventaja de 500k depende del límite de una propuesta. Los datos demuestran
recuperación útil de asociaciones conocidas, sin inferir una regla arbitraria
para un motivo nunca aprendido.

El trabajo de consulta fue 12.877.451 unidades con 500k y 41.971.680 con búsqueda
de 32 programas. El brazo sin guía de una propuesta gastó solo 1.394.827, pero
resolvió 109: no se afirma que todo uso de la guía sea más barato. El ajuste de
cada tamaño sumó 202.752.848 unidades en las ocho semillas. Ambos tamaños y sus
datos coexistieron en workers con hasta 60,22 MiB RSS. Los vectores solos ocupan
64 KiB y 488,28 KiB. La adquisición consumió 150,96 segundos CPU acumulados y
las consultas 20,31; son costes de esta ejecución concurrente, no un ensayo de
latencia de producción ni una estimación de energía.

El límite común de rejillas fue 500.000 unidades lógicas por tarea: celdas de
entrada de primitivas, segmentación/renderizado, pares de objetos, consultas de
memoria y comparación de salidas. Son unidades del instrumento, no FLOPs exactos.
CPU y número de candidatos se conservan separados. Las rotaciones de vistas,
el encoder y el verificador tienen coste; ninguna etiqueta de test entra en la
selección, memoria o recompensas. No se ejecutaron tareas de reserva ARC o S6.

La reproducción rehizo **1.952 resoluciones**, **512 episodios de ajuste** y las
tres adquisiciones, con igualdad exacta de artefactos deterministas. GUIDE rehizo
las ocho adquisiciones completas y 4.096 consultas por brazo. El recibo de
cierre vuelve a contar los aciertos contra el juez, verifica presupuesto por
tarea y comprueba **366 fuentes anteriores intactas**. Es una auditoría interna
con procesos nuevos y el mismo código; una reproducción externa sigue pendiente.

Pasaron **31 pruebas dirigidas** (16 nuevas y 15 de integración previa) y las
**488 pruebas de NEXUS-0**, con un fallo esperado histórico. La entrada CLI
adquirió un recuerdo y otro proceso cargó el candidato derivado y resolvió su
consulta. El candidato padre se conserva. Los diarios usan `echo_arc.observe`
y la mini terminal existente; contienen decisiones y métricas ejecutadas.

Uso local, desde `echoai/`:

```bash
PYTHONPATH=.. python3 -m seed.echo45_v3 mi_tarea.json \
  --candidate lab/seed/relational-v3-20261003/primary/candidate.json

# Banco opcional de programas adquiridos; si no verifica, sigue el solver.
PYTHONPATH=.. python3 -m seed.echo45_v3 mi_tarea.json \
  --candidate lab/seed/relational-v3-20261003/primary/candidate.json \
  --guide lab/seed/program-guide-20261003/primary/guide500k.json

# Adquirir demostraciones propias en un hijo, conservando estado y linaje.
PYTHONPATH=.. python3 -m seed.echo45_v3 demostraciones.json \
  --candidate lab/seed/relational-v3-20261003/primary/candidate.json \
  --learn-to candidato-hijo.json
```

El formato de tarea es `train: [{input, output}], test: [{input}]`. El comando
admite `--no-views`, `--first` y `--output`. La variante por defecto usa vistas y
consistencia; puede devolver `AMBIGUOUS` con predicción nula. La adquisición se
niega en rutas o IDs de reserva conocidos y solo conserva programas verificados.
La opción de guía usa el primer banco de la semilla prerregistrada 49100,
sin seleccionar retrospectivamente el que más acertó.

Referencias: [contrato y adenda](ECHO45-RELATIONAL-V3-DESIGN.md),
[perfil](../lab/seed/relational-v3-20261003/profile.json),
[resultados por tarea](../lab/seed/relational-v3-20261003/primary/rows.json),
[resumen](../lab/seed/relational-v3-20261003/primary/summary.json),
[reproducción](../lab/seed/relational-v3-20261003/audit.json),
[guía](../lab/seed/program-guide-20261003/primary/summary.json),
[reproducción de guía](../lab/seed/program-guide-20261003/audit.json) y
[cierre recalculado](../lab/seed/relational-v3-20261003/closure.json).
Los PNG tienen versiones SVG en el mismo directorio. Nada de este ensayo se ha
publicado en la web. S6 y la medición final de ECHO-4.5 siguen siendo los siguientes
bloques de trabajo, con transferencia ARC todavía por confirmar allí.
