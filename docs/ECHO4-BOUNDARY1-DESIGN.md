# E4-BOUNDARY-1 — contrato v1: influencia causal observable

2026-09-21. Autorizado por el usuario tras SENSATION. Fijado antes de la
campaña. No modifica WORLD-1, SENSATION ni contratos históricos.

## Pregunta y alcance

Estimar qué códigos sensoriales puede modificar una acción ejecutada,
frente a una referencia de espera, bajo intervenciones emparejadas. Es un
laboratorio virtual con restauración y perturbaciones controladas. No es
atribución de una causa individual en condiciones arbitrarias, autonomía
experimental, pertenencia corporal, mantenimiento ni conciencia.

La validez causal depende de la restauración exacta y del mismo programa
externo en ambos brazos. El ejecutor garantiza esto y el auditor lo
reproduce. **Igualdad de WSP por sí sola no prueba comparabilidad.** Fuera
de este protocolo, sin recibo de emparejamiento, la respuesta es desconocido.
No se supone que un futuro robot disponga de este acceso experimental.

## Experimento, sensor y recibos

Dos ticks por ensayo, con observaciones t=0/1/2. WORLD-1 aporta la física
entera original. Una envoltura experimental puede desacoplar cada actuador
del canal H/temperatura, añadir calor externo común o retrasar hasta t=2
la aplicación de la orden. Desacoplado significa que ese canal sigue la
dinámica de wait. No se cambia la transición original ni se reescribe su
historial de resultados. Los recursos siguen siendo unidades abstractas.

Tratamiento: una orden approach/avoid, espera en el resto de ticks.
Referencia: wait en ambos ticks. Se permuta el orden de los brazos.
Cada uno es un ensayo restaurado explícitamente, no una vida autónoma
rescatada. El gate original puede vetar la orden; un veto no equivale a
haber ensayado una acción sin efecto. No hay actos después de terminalidad.

El consumidor recibe solo WSP original de 16 bytes, timestamps enteros de
captura, intención, acción aplicada por tick, resultado del gate, token de
emparejamiento y recibo público de restauración. No recibe H/theta exactos,
acoplamientos, perturbaciones, escenario, semilla ni etiqueta del juez.
Estos recibos son metadatos de procedencia experimental, no otro bus de
pensamiento. WSP sigue siendo la representación sensorial única.

Se estudian U y B (bytes 8 y 9), no bits de metadatos/átomos que cambian
por formato. Cada contraste es la diferencia entre cambios de código:

`d[j,t] = (WSP_trat[t,j] - WSP_trat[0,j]) - (WSP_ref[t,j] - WSP_ref[0,j])`.

Se interpreta B como int8. Se ignoran tiempos anteriores a la aplicación
confirmada; nunca se atribuye a una acción aún en cola. Ventana máxima dos
ticks: no se concluye nada sobre retardos mayores. Estado terminal en
cualquier brazo invalida la comparación de horizonte completo.

## Aprendizaje y presupuesto

CAM existente: observaciones reales, sin convertir estimaciones en hechos.
SENSATION se reutiliza para predecir antes de cada paso, aprender del WSP y
registrar error/confianza; **su error no decide causalidad**. T y CAM no se
duplican dentro de BOUNDARY.

Mapa acotado a 128 filas de `(slot CAM inicial, acción)`, con contadores
enteros de signo positivo/negativo/cero para dos canales y dos retardos.
Máximo 4.096 pares ingeridos por instancia; IDs estrictamente crecientes
evitan doble conteo. Llenado o datos inválidos no borran ni sustituyen filas.
No se guarda una traza creciente dentro del consumidor. Las trazas extensas
pertenecen al evaluador externo.

Mínimo ocho pares válidos por fila/horizonte. Influencia detectada si al
menos 7/8 contrastes tienen el mismo signo y ninguno signo contrario;
sin efecto observable si todos son cero; el resto queda desconocido.
Esto es un criterio de replicación finito, no una probabilidad calibrada ni
una prueba de ausencia física de efecto bajo cuantización.

Salida: máscaras de 16 bits `influence`, `no_observed_effect`, `unknown`,
signos y primer retardo con efecto sostenido. Solo bytes 8/9 son elegibles.
Los demás permanecen desconocidos. No existe una salida «esto soy yo».
El mapa se congela tras identificación; la evaluación no lo actualiza.

## Casos y evaluación prospectiva

Once familias privadas: acoplamiento completo, solo H, solo temperatura,
solo calor externo, propio más externo, retardo de dos ticks, veto, recibo
de ejecución ausente, comparación no emparejada, captura caducada y efecto
subbanda invisible. En esta última, no detectar efecto no significa que
el canal físico sea incontrolable.

Puntos de prueba cercanos a límites sensoriales, declarados para que el
efecto de las acciones sea observable sin ampliar sensores: approach parte
de H=29/30/31 en desarrollo/B/C; avoid de H=35. Temperatura inicial
48/50/52 respectivamente. Variación de calentamiento común y orden de
brazos según la semilla. Son bancos locales de identificabilidad, **no**
muestreo representativo de todos los cuerpos posibles.

Cada bloque usa una instancia nueva (sin mezcla de acoplamientos ocultos),
ocho pares de identificación y cuatro de evaluación por acción. Se congela
CAM/T/PATTERN/mapa entre identificación y examen. Al evaluar se consulta el
mapa antes de recibir el nuevo resultado. Otras condiciones requieren nueva
identificación; no se usa el nombre privado de familia como clave.

- Desarrollo: 2 bloques por familia, semilla 42001.
- Validación B: 16 bloques por familia, semilla 42002.
- Confirmación C: 16 bloques por familia, semilla 42003.

C solo se abre si B pasa. Semillas públicas prospectivas, no custodia ciega.
El juez compara máscaras y retardo con la intervención privada del protocolo;
las etiquetas nunca entrenan. Todas las familias y desconocidos se informan.
Baseline: atribuir a la intención cualquier U/B que cambie después.
Ablación: quitar el recibo de emparejamiento; debe abstenerse.

## Umbrales antes de B/C

Por separado en cada etapa: ≥95% de máscaras completas correctas, ≥90% por
familia; cero influencias falsas en solo externo, subbanda y casos inválidos;
100% de abstención sin recibos válidos y 100% de retardo correcto en los
casos nominal y retrasado; más aciertos que coincidencia temporal por ≥10
puntos. El desconocido cuenta como fallo cuando se exige una estimación.
Congelación exacta, cero hechos falsos/slots destruidos/córtex y memoria
acotada. Datos, acciones y recibos invalidables se prueban por separado.

Pruebas: conexión nominal al Agent/SENSATION real; invalidez sin mutación,
capacidad y repetición; contraste independiente; causalidad espuria; cambio
de signo; fuentes y recibos alterados. Reproducción íntegra en proceso nuevo
con rechazo de informe o traza manipulados y conservación de SENSATION.
Código propio en `echo4/boundary*.py`; CLI separado para no invalidar el
certificado SENSATION que incluye su CLI anterior. Si B falla, conservar
el rojo y no abrir C ni cambiar retrospectivamente los umbrales.
