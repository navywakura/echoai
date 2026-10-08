# E4-SENSATION-1 — contrato predictivo v1

2026-09-21. Fijado antes de ejecutar la campaña predictiva. Complementa,
sin modificar, la auditoría temporal exhaustiva ya publicada.

## Pregunta y alcance de cierre

¿La historia sensorial mejora la predicción aprendida de la siguiente
observación WSP, sin acceder al cuerpo exacto y distinguiendo incertidumbre
de error? El cierre es **predicción sensorial en WORLD-1 nominal**, no
eliminación del aliasing, mantenimiento, atribución causal ni conciencia.
Integración opt-in en la predicción del Agent; no cambia su política Q.

## Algoritmo fijado

Reutilizar `Cam`, `World` y `PatternMemory` originales, sin modificarlos.
T aprende la transición instantánea. PATTERN aprende consecuencias en
contextos de observaciones y acciones ejecutadas; solo responde tras ocho
observaciones y ninguna contradicción, según su regla existente. Si no
hay regla temporal, se utiliza T, indicando su confianza. Sin vecino
aproximado ni hash tratado como identidad.

Un registro exacto acotado asigna un índice local a cada historia. El índice
solo identifica la fila predictiva; no es un nuevo WSP, hecho ni segundo
bus. 2.048 contextos, longitud máxima 84 bytes; sin desalojo ni sustitución.
PATTERN tiene 8.191 entradas fijas. Al llenarse se cuenta el descarte y se
recurre a T. CAM conserva 4.096 ranuras; una CAM llena devuelve desconocido,
nunca la ranura 0 como sustituto de un miss. Modelos siempre estimaciones.

Tres brazos con iguales límites de memoria y datos: T instantánea (0),
historia 2 (**primario**) e historia 4 (diagnóstico, no elegida según examen).
El predictor solo recibe WSP y acción ejecutada. La terminalidad se usa
para acabar/reiniciar explícitamente cada episodio, no como entrada o
objetivo predictor oculto. El objetivo es el paquete siguiente, no H/theta.

Presupuesto: CAM y T históricos más 8.191 filas PATTERN de cinco enteros,
2.048 claves exactas de hasta 84 bytes, ventana de hasta 84 bytes y una
predicción pendiente. Índices/contadores se acotan; se reportan ocupación,
descarte y tamaño de objetos Python medido, no se afirma Heap-0 C.

## Orden de un paso

`anticipate(acción ejecutada)` registra la predicción antes del resultado.
`observe(WSP siguiente)` puntúa contra esa predicción y luego aprende,
salvo en modo congelado. Rechazar dobles anticipaciones, resultados sin
predicción y entradas inválidas sin mutar. Reinicio entre vidas explícito.

Error: distancia L1 entre los códigos sensoriales U/B; cualquier cambio en
otro byte también cuenta como discrepancia. Etiqueta: 00 exacto, 01 error
pequeño (hasta 32 unidades de código), 10 mayor, 11 evidencia insuficiente
(confianza menor que 3). Error y confianza se conservan por separado: 11
no borra un error conocido. Nada atribuye una causa externa o daño propio.
Las etiquetas son un resumen diagnóstico, no una nueva señal de control.

## Campaña y separación de datos

Sin viabilidad/oráculos en el generador ni en el predictor. Dinámica original
WORLD-1; acciones uniformes 0..2 y arranques vivos. Episodios de hasta 24
acciones, deteniéndose al morir, sin selección por éxito o duración.
Los índices corporales iniciales se particionan por resto módulo 4:
entrenamiento 0/1, validación B 2, confirmación C 3. El predictor no recibe
índices, particiones ni semillas. Se aprende solo en entrenamiento.

- Entrenamiento: 8.192 episodios, semilla 41001.
- B: 2.048 episodios, semilla 41002.
- C: 2.048 episodios, semilla 41003.

Las semillas son prospectivas pero públicas: no se afirma custodia ciega.
Trayectorias B/C no se ejecutan hasta fijar fuentes y pasar pruebas de
desarrollo. Estados intermedios/contextos observados pueden repetirse: se
evalúan nuevas trayectorias del mismo dominio, no física desconocida.
Hay evaluación por episodio y recuento de victorias/derrotas emparejadas.
Una abstención cuenta como fallo para precisión global; no seleccionar
solo los casos donde el predictor temporal responde.

## Umbrales prospectivos (ambos, B y C)

1. Al menos 10.000 transiciones por etapa.
2. Primario con al menos 0,5 puntos porcentuales más de aciertos globales
   que T: `200 * (aciertos2 - aciertos0) >= transiciones`.
3. Cobertura de predicción al menos 98%; cobertura de confianza alta al
   menos 5%; precisión en confianza alta al menos 95%.
4. Modelo congelado: CAM/T/PATTERN/registro idénticos antes/después; solo
   avanza la ventana sensorial de cada episodio.
5. Cero slots destruidos, hechos falsos y llamadas al córtex. Entradas solo
   públicas; memoria acotada. Los tres T instantáneos deben ser idénticos.
6. Integración real en `_predict` del Agent, predicción anterior al paso,
   gate conservado, errores/etiquetas consistentes y regresiones intactas.
7. Informe y trazas reproducibles en proceso nuevo; auditor recalcula la
   campaña completa y rechaza reportes/trazas alterados. Pruebas negativas
   de capacidad, secuencia, aprendizaje en examen y dependencias prohibidas.

No cambiar umbrales, semillas o algoritmo para reinterpretar un examen rojo.
Si hace falta revisión, conservar v1 y emitir contrato/version nuevos con
nuevas trayectorias reservadas. B/C no entrenan ni seleccionan parámetros.
