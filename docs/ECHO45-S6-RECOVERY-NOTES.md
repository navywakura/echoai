# S6-A · nota de ejecución, antes de lanzar ECHO (2026-09-27)

Después de lanzar FIJO y **antes de lanzar la campaña válida de ECHO**, la revisión encontró un
error en la interfaz P3. El texto de la petición mostraba una tarea no resuelta elegida por ECHO,
pero `build_request` devolvía los identificadores de las tareas ya resueltas por la operación que
se generalizaba. V3 cribaría esas tareas resueltas, descartaría todas y rechazaría la propuesta.

Se corrige devolviendo el identificador de la tarea pendiente que aparece realmente en la petición.
La elección aleatoria y el texto siguen usando la misma tarea; se modifica solo el identificador
entregado al verificador. FIJO no ejecuta P3 y no cambia su comportamiento. Los filtros V1–V4,
el presupuesto, el modelo, la partición, la base y los criterios A1–A5 son iguales en ambos brazos.

La fuente de FIJO ya estaba congelada y se conserva. ECHO se congela en un segundo paquete con
este arreglo antes de hacer sus 300 propuestas. Las huellas iniciales/finales se comparan con el
paquete correspondiente a cada brazo, y se comprueba que las funciones de verificación son
idénticas. No se presenta a los dos archivos completos del ejecutor como literalmente idénticos.

La prueba `test_generalization_screens_the_unsolved_task_shown_in_the_prompt` verifica este caso.
Las ejecuciones válidas no se han medido todavía en las reservadas cuando se fija esta corrección;
el control SEMILLA solo reprodujo la cifra preexistente de 24/201.

## Revisión que sustituye el plan anterior: V3 (2026-09-27)

Antes de lanzar ECHO se comprobó la única operación aceptada del FIJO antiguo, sin modificar
la biblioteca: la semilla resuelve `bb43febb` y `d282b262` sin ella, con las mismas 400 expansiones.
El diario histórico de S2v no era una medida completa de la biblioteca ampliada. Evidencia:
`lab/kaggle/s6-closure-20260927/legacy-counterfactual.json`.

Por ello **también se excluye el FIJO de recuperación `echo45-s6-fijo-closure`**: sus peticiones
partieron del inventario antiguo y V3 no comprobaba el contrafactual al mismo presupuesto.
Los dos brazos finales vuelven a partir de cero, con **un único paquete idéntico** y una línea
base A/B medida sobre todas las 808 tareas de desarrollo, sin operaciones propuestas.
V3 resta las tareas que la biblioteca anterior ya resuelve a 400 expansiones antes de exigir
dos soluciones nuevas. Se mantiene V4 y todos los umbrales A1–A5; se corrige el significado
operativo de «nueva», sin seleccionar propuestas por su resultado en reservadas.

V2 se ejecuta en un proceso nuevo con 1 GB, límite de CPU de 5 segundos y espera máxima de
15 segundos. Cada aplicación conserva 50 ms, incluida la validación de salida. Se restringen
también las anotaciones evaluadas al definir funciones a nombres simples o constantes.
Los manejadores de excepciones admiten solo subclases explícitas de `Exception`; se rechazan
tipos calculados que podrían alcanzar `BaseException`, y la asignación de atributos persistentes.
Los arreglos P3 y de custodia anteriores se incluyen en ambos brazos.

Artefactos finales separados: `lab/kaggle/s6-final-20260927/` y
`lab/seed/s6-final-20260927/`. Las campañas descartadas se conservan para auditoría.

La medición completa terminó el 27 de septiembre a las 01:23 UTC: **A 73/606 y B 16/202**.
La biblioteca conserva SHA256 `69bdcd4ac01c623a8208c5efa0e010db674d9c15c74e0cd8f5ca5ba3691e7ebc`.
Paquete final idéntico para ambos brazos:
`c295e291fb1cc15bac76acbadf1b27ed07621a0c817244cbbd4f61f8d41a6313`.

## Campañas terminadas y recuperación de la medición

Las GPU quedaron libres al terminar FIJO de diagnóstico y cancelarse la sesión antigua de ECHO.
FIJO final se lanzó a las 03:18 UTC y ECHO final a las 03:30 UTC. Ambos completaron 300 intentos,
con cero operaciones aceptadas y todos sus archivos protegidos intactos. No hubo respuestas
ausentes en las campañas finales. SEMILLA, FIJO y ECHO reprodujeron 24/201.

La primera medición de SIN FILTRO se atascó al morir trabajadores: `ProposalTimeout` podía
escaparse durante el `finally` que desactivaba su temporizador. El registro fallido se conserva en
`lab/kaggle/s6-final-20260927/probe-sinfiltro-failed-cleanup.log`.
Antes de obtener un resultado completo de SIN FILTRO se congeló un envoltorio de medición,
`probe_driver.py`: captura también ese escape como `ValueError`, desactiva el temporizador y
restaura el manejador anterior. No cambia el código de las propuestas, su orden, las 400
expansiones, los veredictos ya registrados ni los archivos protegidos de las campañas.
Su huella y fecha se conservan en `measurement-profile.json`. También guarda cada tarea
independiente terminada para no perderla en una interrupción, ligada por hash a las tareas,
biblioteca, diario, fuente protegida y envoltorio. Los replays usan procesos nuevos y un
directorio de reconstrucción sin esos resultados cacheados. SIN FILTRO se mide con seis
trabajadores y sin otras mediciones compitiendo durante su replay.

El resultado de SIN FILTRO y la auditoría completa siguen pendientes en este punto. No se
declara cerrado S6 hasta comprobarlos. La reparación del temporizador tiene una prueba
específica, además de las once pruebas anteriores del ejecutor.

## Cierre, 2026-09-27 a las 10:53 UTC

**S6-A cerrado y auditado: ROJO.** SEMILLA 24/201, FIJO 24/201, ECHO 24/201 y SIN FILTRO
25/201, con 244 operaciones distintas en este último. Las cuatro mediciones se repitieron
en procesos nuevos desde los diarios y dieron informes idénticos byte a byte. La auditoría
no encontró incidencias: A5 pasa; A1–A4 no pasan. Las doce pruebas pasaron y el coste de
API fue 0 USD.

La única reservada adicional es `4347f46a`, resuelta por `s6_echo_f5e737ea`, propuesta 182
de tipo P2. La criba V3 la había rechazado por no resolver ninguna tarea de su petición
a 150 expansiones. Su programa resolvió la reservada en una expansión; no perdió ninguna
de las 24 soluciones anteriores. La procedencia quedó registrada después de la medida,
sin cambiar el experimento: `lab/kaggle/s6-final-20260927/unfiltered-gain-provenance.json`.

Resultado completo: `ECHO45-S6-RESULTS.md`. Estado del resto del proyecto:
`ECHO45-ECHO5-ROADMAP.md` y `NOW.md`. Las notas anteriores describen cada punto de la
recuperación; los estados pendientes de esos puntos quedan resueltos por este cierre.
