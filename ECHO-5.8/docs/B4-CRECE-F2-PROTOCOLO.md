# CRECE F2 · protocolo previo de desarrollo

21/10/2026. Se fija después de F1 y antes de F2. F1 pasó por 26→33 éxitos
en 96 partidas, sin regresión familiar/daño; la pieza copió el ejemplo
no_repick. Dos de tres llamadas dieron error HTTP. Esto prueba viabilidad
técnica, no invención ni aportación de las fichas.

## Diseño y presupuesto

Principal gemini-3.5-flash y réplica gemma-4-31b-it, informados por separado.
Dos macros (1,2), cinco generaciones, siete brazos de la enmienda 1. Cada
brazo comienza con CORRECTED sobre start_memory(m), sin aprendizaje
persistente nuevo. g0 no tiene piezas, excepto la referencia piezas_b3.

En cada generación: una propuesta por brazo crece, sin_fichas y sin_relevo.
Se permite un máximo de tres intentos HTTP para obtener ESA propuesta;
solo ante error de transporte/HTTP o respuesta vacía, pausas de 10 y 20 s.
No reparar código en F2. Los intentos se reservan en disco antes de llamar;
un intento cuyo resultado se perdió se cuenta como consumido, nunca se borra.
Mismo máximo para los tres brazos. Por modelo: 30 propuestas, ≤90 intentos
HTTP; dos modelos ≤180. Cache hits separados de llamadas reales.

Temperatura 0, máximo 3000 tokens de salida según el endpoint. Ficheros
privados cacheados por solicitud completa. No cambiar modelo, presupuesto
o API silenciosamente ante una caída. Una propuesta fallida conserva el
campeón y se registra; no se considera evidencia de que el algoritmo falle.

`acepta_azar` reutiliza las cinco candidatas de crece de su misma macro y
modelo. Al cerrar las cinco generaciones, selecciona uniformemente tantos
índices mecánicamente válidos como promociones consiguió crece. Los aplica
en su orden original y construye g0…g5. Esta selección retrospectiva está
declarada; no usa resultados del examen ni vuelve al modelo.
Cada aparición válida conserva su índice, aunque repita código. Las elegidas
se instalan como instancias distintas (mismo objeto de código, identificador
por generación y contadores NOTE propios), en orden. Así el número de
instancias coincide con las promociones sin sesgar el sorteo a la primera
aparición. Un duplicado activo no se promociona en crece pero permanece en
la población del sorteo. Aclaración fijada antes de lanzar F2, tras revisión.

`azar_gramática` recibe una propuesta por generación de un menú finito de
reglas sobre la misma API: veto de repetición con umbral entero, veto de
coger tras repetición, movimiento ocioso a celda menos visitada, veto hasta
progreso al recoger lo soltado. Distribución uniforme de plantillas y
umbrales 1…4, semilla fija por macro/generación. No pretende representar la
distribución de todos los programas posibles. Pasa mecánica y la misma puerta.

## Datos, semillas y medida

Familias de entrenamiento/validación/sonda: las ocho de F0/F1 (solo desarrollo).
Para modelo principal b=0; réplica b=50_000_000; macro m=1,2; generación g=1…5:

- Fichas: semillas `b + 11_000_000 + 100_000*m + 1_000*g + i`, i=0…4.
  Tres fallos por señales distintas cuando existan; si hay menos fallos se
  entregan los existentes. Ningún éxito se transforma en fallo ficticio.
- Puerta: `b + 12_000_000 + 100_000*m + 1_000*g + i`, i=0…7, por familia,
  compartidas entre brazos para emparejar, nunca entre generaciones.
- Sonda: `b + 13_000_000 + 100_000*m + i`, i=0…11, por familia, la misma
  para g0…g5. No decide promociones ni se devuelve al LLM.
- RNG del control de azar: `b + 14_000_000 + 100_000*m`, guardado.

La ficha de crece contiene el fallo de su campeón y sus piezas activas.
sin_relevo ve siempre g0 y valida una pieza sobre g0; cada snapshot g refleja
el último aspirante aceptado, pero no alimenta la siguiente propuesta.
sin_fichas recibe solo API, ejemplos y número de generación/macro/modelo,
sin fichas, resultados de puertas ni piezas activas. El número identifica
la solicitud; no codifica características del mundo.

Puerta: éxito agregado estrictamente mayor; éxito por familia no menor;
daño por familia no mayor; cero errores del enchufe. Sin poda en cinco
generaciones. Se prueban candidatos contra el campeón fijo de esa generación
con memoria idéntica por episodio. Misma cota natural de pasos que los mundos
originales; se conserva la distinción éxito/daño/agotamiento.

## Cierre

Para el principal, la suma de fallos de sonda de las dos macros debe bajar
en al menos dos transiciones consecutivas de generación. Publicar curvas
de todos los brazos y de la réplica, incluyendo empates. Esta puerta de
desarrollo no sustituye las comparaciones del contrato científico.

Antes de F3 se comprueba persistencia de snapshots/biblioteca en un proceso
sin API. Si la puerta no pasa, F2 queda rojo y no se examina ese protocolo.
Correcciones de software se documentan; un nuevo diseño necesita versión y
datos nuevos. Nunca ajustar con resultados de examen.
