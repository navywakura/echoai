# CRECE · plan condicionado de implementación F3/F4

21/10/2026. **Plan de trabajo, no contrato activado ni permiso para abrir
reservas.** Depende de la entrada de [borrador F3](B4-CRECE-F3-BORRADOR.md):
F2 r1 completa y verde, auditoría verde y requisitos F0/F1/persistencia.
**Instrucción posterior de Nav, con F2 en 38/40 candidaturas: terminar el
piloto sin hacer el examen. Este plan queda preparado, sin activar F3/F4.**
Mantener facturación.
Si F2 r1 no pasa, conservar este documento como preparación no ejecutada.

## 1. Cerrar F2 antes de cambiar fuentes

Conservar results.json, 12 fuentes exactas y cinco protocolos con los hashes
de started.json. Archivar el auditor independiente y sus pruebas; verificar
recibos, reservas, caches, puertas, continuidad, curvas y base congelada.
Publicar el resultado de desarrollo con gráficos y límites. No confundir
una auditoría verde con un resultado científico verde.

No modificar ni añadir módulos en echo58/crece mientras R1 esté abierta:
su manifiesto incluye el directorio completo. No tocar fuentes congeladas
de memx/acumula/acumula2/b3/acumula3/enjambre, NEXUS ni echo-discord.

## 2. Fijar contrato y configuración verificable

Tras entrada verde y revisión, convertir el borrador revisado en
`B4-CRECE-DESIGN.md`; conservar borrador e historial. Incluir todos los
parámetros, interpretación de controles, supuestos, cuotas, límites y
tratamiento de fallos. Hash del contrato antes de empezar entrenamiento.

Crear `echo58/crece/confirmatory.py` con una configuración explícita e
inmutable de las veinte macros, cinco generaciones, siete brazos, semillas
y presupuestos. Mantener `generations.py` como referencia histórica de F2;
reutilizar funciones estables de fichas, prompts, mecánica, puerta y
persistencia, sin cambiar runtime ni lenguaje para mejorar resultados.
El bucle F3 debe conservar la semántica de F2 descrita en el contrato.

Primero pruebas en `tests/test_echo58_crece_confirmatory.py`: disyunción de
lotes independientes con las veinte macros, permitiendo el emparejamiento
deliberado entre brazos/generaciones; conteos 300/900/100/400/840; prohibición de
abrir F4 con F2 roja/incompleta o auditoría ausente; cambio de hash rechaza
reanudación; agotamiento de tres intentos no produce una trayectoria
científica cerrada. Usar respuestas y mundos sintéticos, ninguna reserva.
Ver fallar esas pruebas antes de implementar los comportamientos nuevos.

Comprobar con un fixture sintético de cinco generaciones que el nuevo
bucle conserva orden, campeón, fichas, rechazos, control sin información,
sin relevo y sorteo de F2. No exigir igualdad de resultados entre semillas
distintas ni interpretar fixtures como aprendizaje medido.

## 3. Inferencia exacta, sin datos de examen

Crear `echo58/crece/statistics.py` y
`tests/test_echo58_crece_statistics.py`. La preparación temporal en
`/tmp/echo58-crece-f3/exact_stats.py` es solo un prototipo; promover mediante
pruebas independientes, no copiar sus aserciones como única verificación.

Casos: ceros, todos positivos/negativos, empates absolutos y mixtos,
permutaciones de orden, distribución exhaustiva de signos para n pequeño,
Holm en el umbral exacto y monotonicidad de p ajustada. Comparar el algoritmo
de programación dinámica con enumeración independiente y un ejemplo
publicado. Rechazar bool, NaN y valores no enteros en conteos/diferencias.
Representar probabilidades como fracciones numerador/denominador, sin
redondear antes de decidir. Todos ceros da p=1.

El evaluador de Q1…Q4 será una función pura sobre recibos agregados por macro.
Probar con datos sintéticos que la media de episodios no sustituye a la
unidad macro, que menos de tres transiciones consecutivas falla Q1 y que
un error del enchufe o aumento de daño en una sola familia impide verde.
Incluir casos de desigualdad estricta, margen 6 y transferencia por variante.

Preparación aislada ya disponible en
`lab/echo58/crece/f3-preparation/statistics-v2/`: función pura y 21 pruebas
sintéticas, más 3906 casos por enumeración independiente. Incluye un arreglo
para iteradores de una sola pasada y casos donde significación favorable
no basta si falla la mejora agregada o el margen medio. No está integrada
en producción; al promoverla se validarán imports y contrato final.

## 4. Evaluador de examen separado y durable

Crear `echo58/crece/exam.py` y `tests/test_echo58_crece_exam.py`. Importar
HAgent directamente; no llamar al evaluador observado ni al score de F2.
Antes de reservar o crear cualquier mundo, el evaluador rechaza ejecución
si falta cierre completo de F3, preflight válido o auditoría previa verde.
Probar su entrada directa, sin depender del orden de un script coordinador.
Identidad del episodio: memoria/configuración, piezas ordenadas, fuentes
runtime y dependencias, entorno, familia/variante, régimen y semilla.
Congelar también `echo58/enjambre/coop.py`. La biblioteca viaja sin LLM.

Antes del mundo, reservar el intento de episodio durablemente. Después,
publicar un recibo completo con identidad, éxito, daño, agotamiento, pasos
y errores del enchufe mediante la publicación exclusiva existente. Un
recibo publicado nunca se reemplaza; si hay interrupción sin recibo, se
reanuda la identidad pendiente bajo los mismos hashes y se conserva su
reserva anterior. Contabilizar ejecuciones y reutilizaciones por separado.

Pruebas con entorno falso: fallo antes/después de reserva, antes/después de
publicación; dos solicitudes de la misma identidad; pieza/orden/régimen/
entorno distinto no reutiliza score; JSON truncado o hash alterado bloquea.
Una ejecución terminada con resultado rojo queda cerrada igualmente.

Preparación genérica ya disponible en
`lab/echo58/crece/f3-preparation/journal-v1/`: quince pruebas sintéticas y
revisión estática del guard previo, lock por identidad, reservas, recibos
y reanudación. Reutiliza el publicador existente sin modificarlo. Sus
callbacks son falsos; faltan el verificador real de preflight, adaptadores
de entornos y conexión con HAgent. No es todavía el evaluador F4.

Bloquear sockets y aperturas de archivos de claves dentro del proceso de
examen antes de cargar campeones. Probar denegación sin leer secretos, con
rutas y sockets simulados. No importar ni llamar `complete` en el evaluador.
Sin observador ni traza añadida al examen. Un smoke de desarrollo puede
comprobar adaptadores MiniGrid/CoopWorld; no usar familias/semillas reservadas.

Validar alcanzabilidad solo con los nueve mundos ya fijados de desarrollo:
el recibo `lab/echo58/crece/f3-preparation/individual-reachability.json`
conserva fuente, acciones y hashes. No usar el oráculo para filtrar mundos
del examen ni como política de ECHO.

## 5. Entrenamiento completo y cierre previo al examen

Revisar la implementación y ejecutar las pruebas necesarias, incluyendo
regresión F0/lenguaje/mecánica/API/persistencia/pacing afectada. No añadir
repeticiones costosas una vez verificadas sin un cambio que las justifique.
Congelar fuentes, contrato y configuración antes de las primeras propuestas.
Carpeta nueva `lab/echo58/crece/f3-confirmatory-v1/`; no reutilizar resultados
de pilotos como entrenamiento confirmatorio.

Veinte macros m11…30, cinco generaciones, exactamente el modelo 120b y
presupuesto fijados. Decisiones de desarrollo visibles en el terminal
existente. Un solo envío HTTP activo, limitador compartido y Retry-After;
una cuota aplaza la misma solicitud conservando intentos, sin cambiar
modelo, permisos o facturación. Cache por identidad íntegra de petición,
sin clave; distinguir hits, envíos y tokens nuevos.

Cerrar todas las macros aunque las sondas sean malas. Verificar 400 trials,
840 snapshots, veinte sorteos/memorias y todos los recibos necesarios.
Una propuesta no vacía de código inválido es rechazo medido; tres intentos
sin respuesta válida dejan el entrenamiento técnicamente incompleto.
No abrir F4 para resolver dudas de desarrollo. Recargar una biblioteca
congelada en dos procesos nuevos sin red/claves, en mundo de desarrollo.

Crear preflight completo de artefactos, hashes y pruebas antes de F4.
Auditor independiente confirma disyunción, presupuestos, campeones y
aislamiento de controles; no selecciona macros según las sondas.

## 6. Ejecutar F4 una vez y auditar

Ejecutar 100800 medidas principales nominales y 3600 de transferencia,
reutilizando únicamente identidades exactamente iguales. La reutilización
no aumenta n. Mantener 120 episodios principales por macro/configuración,
límites MiniGrid nativos y 300 pasos de transferencia. Registrar errores
técnicos sin convertirlos en éxitos ni descartarlos silenciosamente.

Publicar curvas g0…g5 por macro y agregadas, comparaciones con cinco
controles, margen B3, transferencia, p exactas/ajustadas, daño y agotamiento,
errores, consumo y duplicados. Una sola función determina el veredicto del
contrato congelado; el auditor lo recalcula con implementación independiente.
No recalibrar umbrales, prompts, piezas o muestra tras abrir F4. Un rojo
científico se publica rojo. Un defecto técnico exige conservar campaña y
documentar su invalidez, sin presentar la corrección como el mismo examen.

## 7. Informe y traspaso

Guardar informe, fuentes exactas, contrato, preflight, auditor, pruebas y
figuras junto a recibos. Actualizar traspaso/índice y explicar alcance:
CRECE observado, controles realmente distinguibles, límites por modelo,
cuota, tamaño, banco y piezas copiadas de ejemplos. No atribuir invención
a una copia ni generalizar de un banco finito a seguridad universal.

La web y cualquier publicación externa se basarán en resultados cerrados,
con sus rojos y límites. Este plan no da por realizadas esas publicaciones.
