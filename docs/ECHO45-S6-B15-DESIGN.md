# S6-B15 — operadores, crédito residual y evidencia numérica

Condición privada nueva, 4 de octubre de 2026. Autorización: corregir los cinco
fallos documentados de B14 y ejecutar una evaluación nueva. B14 queda cerrado
negativo, ECHO 1134 / FIJO 1134, con auditoría independiente válida. Sus 166
fuentes se verifican por hash y se conservan sin cambios. Este contrato se
congela antes de cualquier nueva llamada al modelo o partida.

La hipótesis es que el controlador desaprovechaba la capacidad ya demostrada
en desarrollo: ninguna de las 36 propuestas B14 exploró HOLD o COOLDOWN_CAP.
No se presupone que el arreglo baste para superar a FIJO ni para cerrar S6.
Los dos controles positivos de PROBE2 no entran en las peticiones, la semilla,
la política del piloto ni una lista de propuestas favorecidas.

Cambios que se miden:

1. Cada petición tiene un operador explícito. La gramática y el verificador
   de respuesta lo imponen. Cada guarda debe coincidir con una lectura real
   pertinente en al menos uno de los casos seleccionados y cambiar el control
   efectivo respecto al programa vigente. Un testigo en otra partida no basta.
   Aplicabilidad no significa que cambien acciones ni que mejore la utilidad.
2. Se registran operador solicitado, propuesto y medido, partidas con acciones
   diferentes y consumo de llamada. Los intentos V1 consumen presupuesto, pero
   no cuentan como exploración medida. Los contadores históricos se atribuyen
   al operador realmente medido, aunque la etiqueta solicitada fuera WAIT.
3. ECHO prueba primero operadores disponibles todavía no medidos. Tras ello
   refina sus objetivos propios rechazados con ganancia, hasta tres descendientes
   por raíz, o selecciona por crédito residual de la base actual:
   `(2 + max(0, ganancia observada)) / (1 + pruebas + repeticiones + pérdidas)`.
   El máximo se toma sobre intentos con el mismo hash de programa base. Los
   +13 ya incorporados siguen en el historial y desaparecen del crédito residual.
4. Dos pruebas consecutivas rechazadas de la misma familia, sin ganancia o con
   idéntico comportamiento, pausan la familia durante la siguiente llamada.
   REVALIDATE pertenece a predicción; HOLD y COOLDOWN_CAP a esperas. Cambiar
   únicamente 1 por 2 no evade esta pausa. Es una heurística de diversidad;
   no prueba que otras guardas fallen. Si solo queda esa familia se permite
   explorarla. La exclusión demostrada por certificado V3 de B14 se conserva;
   nunca se convierte un rechazo B/V4 en una prueba para excluir otros parches.
5. El resumen ordena números como números. Publica constantes, rangos numéricos
   de las variables, muestras de observaciones conjuntas reales y frecuencias
   de lecturas. No construye puntos artificiales mezclando extremos marginales.
   Los límites de contexto reducen muestras y contrastes opcionales, conservando
   programa, último recibo, objetivo y último recibo del objetivo. La lectura 14
   de la partida de desarrollo con 1787 esperas debe reaparecer en cualificación.

FIJO se refuerza: usa un calendario fijo REVALIDATE_NOOP → HOLD → COOLDOWN_CAP,
con las mismas reglas de disponibilidad, aplicabilidad y pausa de familia.
Ordena los casos compatibles por niveles e índice. ECHO decide operador y
refinamiento desde su historial y ordena además por señal de fallo pertinente.
Esta es una comparación nueva contra FIJO cíclico, no el FIJO genérico histórico.
RANDOM es un control auxiliar del piloto: muestreo uniforme de parches legales
dentro del operador del calendario fijo. No consume modelo y no sustituye los
cuatro brazos finales SEMILLA, FIJO, ECHO, SIN FILTRO.

Antes del piloto se realiza un microensayo factorial 2×2: vínculo operador/casos
activado o desactivado × resumen numérico o resumen antiguo por extremos textuales.
Se reutiliza como entrada la política de 378 niveles aceptada por B14, con su
único recibo propio inicial y las 80 observaciones A. No se pasan los intentos
posteriores ni los parches de PROBE2. El controlador debe elegir HOLD porque
REVALIDATE ya se midió; no se elige una partida mediante su identificador.

Las cuatro celdas usan la misma descripción y el mismo formato compacto; la
ablación del resumen antiguo solo omite rangos/frecuencias y selecciona los
antiguos extremos. La celda sin vínculo mantiene la gramática global B14 sin
imponer operador. Esta ablación no pretende reproducir literalmente el prompt B14.
Semillas de muestreo emparejadas: 730101, 730117, 730129. Orden por semilla:
sin vínculo/antiguo, vínculo/antiguo, sin vínculo/numérico, vínculo/numérico.
Son doce propuestas independientes; no se realimentan resultados entre celdas.
Cada propuesta válida se mide en las 80 A y se repite íntegramente. Una propuesta
inválida se registra V1, consume su llamada, no se vuelve a muestrear y no pasa
la puerta del microensayo. La base también se repite
y debe conservar los 378 niveles y el digest `4458a4c2…` exacto. Tope 2080 partidas
y 12 llamadas. La caché puede reducir ejecución física si se repite una política;
main y replay usan cachés distintas. Ni B ni el examen se abren en el microensayo.

Puerta de paso: instrumento válido, replays idénticos y al menos una propuesta
de la celda vínculo+numérico con >=2 niveles adicionales, cero pérdidas individuales
de nivel o score, y operador correcto. Es una comprobación de capacidad en A,
no una prueba de ventaja estadística: n=3 por celda. Se publican todos los casos,
incluidos los negativos. Si falla esta puerta, se cierra MICRO_NO_PROMOTION;
una discrepancia del instrumento produce BLOCKED_INSTRUMENT, nunca un negativo.

Tras el microensayo, los actores del piloto vuelven a SEMILLA y al historial
vacío. No reciben sus propuestas ni ganancias. La caché primaria puede reutilizar
mediciones idénticas bajo el mismo perfil; la auditoría independiente usa una
caché nueva y reconstruye cada solicitud, respuesta y veredicto en otro proceso.

Se conserva el modelo Qwen3-4B-Instruct-2507 Q4_K_M nativo en CPU, 4 hilos,
contexto 4096, entrada máxima 3072 tokens, salida máxima 160, temperatura 0.6,
top-k 40, top-p 0.95. No hay API de pago, GPU ni entrenamiento de pesos.
El perfil registra binarios, tokenizador, modelo, fuentes, configuración y
cualificación. No se cambia ninguna fuente del perfil mientras corre.

Desarrollo A: 80 partidas previas, versiones 2/3, semillas 0–39, 2000 acciones.
Protección B nueva: versiones 2/3, semillas 28520–28539, 40 partidas, sin diario.
Examen nuevo: semillas 28600–28659, versiones 2/3 y tres repeticiones, 360
partidas por brazo más replays y conservación del protocolo existente. No se
accede a ese examen hasta cerrar piloto y campaña con auditorías válidas.

Piloto: seis propuestas por brazo y semilla, semillas 710101, 710117, 710129.
36 llamadas LLM y 18 propuestas RANDOM. Promoción: ECHO supera el total FIJO,
gana al menos dos pares de tres, no pierde ninguno y acepta al menos una mejora.
Campaña: treinta propuestas por brazo, semilla 720101, 60 llamadas. Promoción
solo con la ventaja y aceptación exigidas por el protocolo previo. SIN FILTRO
acumula las mismas propuestas ECHO que sean seguras y ejecutables, sin V3/V4.

V1 mantiene sintaxis, límites y seguridad; V2 exige determinismo mediante replay;
V3 exige >=2 niveles A nuevos y cero pérdidas individuales de nivel o score;
V4 exige conservación individual en B. Los fallos de replay detienen la condición.
Presupuesto total: 108 llamadas (12+36+60), 64000 partidas, 4 procesos de juego.

S6 solo es verde al completar B1–B5: ECHO mejora al menos un 5% los niveles
de SEMILLA sin menor score medio, supera FIJO y SIN FILTRO, conserva las
habilidades anteriores y supera la auditoría independiente. Un microensayo o
piloto favorable nunca sustituye estas puertas. El código de puertas y del
examen se importa de la condición congelada, sin reducir umbrales.

Ejecución: `python -m seed.s6b15_qualification` → `python -m seed.s6b15 prepare`
→ `python -m seed.s6b15 follow`. El último comando encadena micro → preflight
→ piloto → auditoría → campaña → auditoría → examen, deteniéndose en la primera
puerta no superada. Usa el observador existente para A; B y examen no se instrumentan.
Las fuentes previas quedan custodiadas, las nuevas se archivan en el perfil B15.
Los resultados se documentan localmente; no hay publicación a web ni GitHub.

Limitaciones: A y la política de calibración ya orientaron el diseño. Esta
condición no demuestra transferencia por sí sola. El resumen de puntos sigue
siendo acotado; un rango marginal no prueba una relación causal. La validez de
S6 depende de la medición y la conservación protegida, no de las intenciones
del planificador ni del volumen de neuronas de otro módulo.
