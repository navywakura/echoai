# E4-SELF-1 — contrato final software v1

2026-09-22. Autorización: completar lo que falta para cerrar E4-SELF-1.
Contrato previo a ejecutar A/B/C. No cambia fuentes, bancos ni criterios
de SELF-A, SELF-B, SELF-C v1/v2, SENSATION o BOUNDARY.

## Qué se cierra

Un yo funcional **condicionado al modelo WORLD-1 declarado**: diagnosticar
alteración propia/externa/mixta, reconocer falta de evidencia, proteger
conocimiento no refutado y utilizarlo en conducta medida. Se integran las
capacidades ya implementadas; no se añade una personalidad ni otro núcleo.

La recuperación tiene dos mediciones distintas: vidas continuas con un
cuerpo alterado (SELF-C v1) y reutilización de T tras restablecer el cuerpo
por el ejecutor (SELF-C v2). No se confunden paradas con vidas completadas
ni restauración de laboratorio con autorreparación. MAINTAIN sigue después.

Se hereda el prior explícito: ecuaciones nominales conocidas, acoplamientos
binarios independientes, pulso térmico {-16,-4,0,4,16} en el primer paso y
constancia entre ensayos. No se descubre la física desde cero. Cada estado
inicial tiene su calibración; esto no es transferencia sin entrenamiento.

## Integración que falta: confirmar antes de autorizar

Una sesión de diagnóstico reutiliza `SelfAttributor`. Aunque alcance consenso,
realiza los ensayos seguros restantes del catálogo original para contrastarlo.
Hasta finalizar, su salida pública es desconocida y no autoriza recuperación
ni exposición. Contradicción, recibo inválido, cancelación o evidencia ambigua
impiden obtener un diagnóstico autorizado. No hay obligación de actuar cuando
no existe un ensayo seguro. Máximo seis ensayos, 48 pasos, un pronóstico
pendiente, 64 candidatos H y 160 térmicos; sin segunda CAM/T/Q ni historial
creciente. La sesión no recibe parámetros físicos ni etiquetas del juez.

Esto cuesta más que detenerse en el primer consenso de SELF-B. Se publicarán
ambos costes, sin reclamar una ventaja de eficiencia para esta confirmación.
La sesión no hace seguros mecanismos arbitrarios fuera del prior: esa
limitación se comprueba con controles específicos y se mantiene explícita.

## Particiones nuevas, sin reutilizar los censos anteriores

- Desarrollo A: H={60,65}, temperatura={46,67}.
- Examen B: H={61,66}, temperatura={47,68}.
- Examen C: H={62,67}, temperatura={50,71}.
- En cada fase: producto de cuatro estados iniciales, cuatro acoplamientos
  y cinco pulsos; **80 condiciones y 240 objetivos por brazo de reutilización**.
- Orden de objetivos A/B: 0,1,2; C: 2,1,0.
- Smoke: un estado de A y pulsos {-16,0,16}; no puede cerrar nada.

Todos los H están fuera de 29..40, rango del censo SELF-A/B, y de los estados
de SELF-C v1/v2. Los mecanismos nominales sí son los del prior. Hay además
pruebas físicas de mecanismos fuera de ese prior, descritas abajo.
Las recetas son públicas; B/C son nuevas ejecuciones tras congelar fuentes,
no un examen ciego custodiado por un tercero. No se ajusta nada al ver B/C.

La campaña registra A y, si falla, conserva el rojo y no abre B/C. Si A pasa,
emite un registro de congelación con hashes de fuentes, contrato y resultado
A **antes** de B. Se ejecutan B y C con las mismas fuentes aunque B falle.
Una corrección posterior a abrir B/C exige otra versión y nuevos exámenes.

## Dos tareas, controles y costes separados

### Reutilización

Se conserva exactamente el protocolo v2: 72 pasos de referencia, 24 pasos
nominales de T, 36 exposiciones y tres objetivos de un paso por condición/brazo,
con restauraciones declaradas. No enseñar sucesores contrafactuales.

Cuatro brazos: selectivo, sin protección/todo externo, congelar todo/todo
propio y el mismo aprendizaje selectivo sin consultar T al decidir. En esta
tarea «sin protección» también es el control sin atribución; no contarlo dos
veces. Exposición idéntica, objetivos idénticos, T/PATTERN/Q sin cambios en
tarea. El objetivo llega como solicitud WSP16, jamás como acción o hecho.

### Vida continua

Usar el ejecutor y controlador de v1 sin modificarlos: 24 pasos, sin resets
ni rescates dentro de la vida. Preparación v1 independiente de 72 pasos por
estado inicial, contabilizada además de la preparación v2. Ambos usan la
misma evidencia nominal y el diagnóstico confirmado de esa condición, pero
son ramas experimentales separadas, no una sola vida ininterrumpida.

Cinco brazos v1: selectivo, misma política sin protección, sin atribución,
todo externo y todo propio. El juez privado calcula viabilidad a 24 pasos.
Publicar éxitos, muertes, paradas, costes, protección y todos los inviables.
No exigir superar un techo físico ya alcanzado: la ventaja conductual se
exige en la tarea de reutilización, no se redefine el rojo de v1.

## Abstención y mecanismos nuevos

En cada estado inicial de cada fase, ejecutar por separado:

- Calor externo persistente +2 por paso, no un pulso inicial.
- Pulso externo +16 retrasado hasta el tercer paso.
- Respuesta térmica invertida al enfriar: +12, conservando su coste H real.
- Cambio físico de +32 térmicos después del primer consenso, durante una
  prueba de confirmación: el consenso previo no debe sobrevivir sin contraste.
- Interrupción tras el primer ensayo: diagnóstico todavía no autorizado.
- Recibos sin restauración, sin contexto, sin ejecución, con tiempo repetido,
  token ajeno o datos truncados: no convertirlos en avería corporal.
- Veto real del gate en el segundo paso: detener el ensayo, abstenerse y no
  reanudarlo. No es una cuarta acción.

Se exige desconocido y rechazo de autorización en estas pruebas, sin cambios
en CAM/T/Q/PATTERN/referencia. Las observaciones válidas de los mecanismos
nuevos proceden de transiciones físicas, no de paquetes inventados por el
consumidor. Se registran también los posibles terminales del ejecutor: no
ocultarlos ni ejecutar después. Estas pruebas no demuestran seguridad ante
cualquier perturbación desconocida.

Se conserva además el testigo de evidencia corta insuficiente y el veto
durante un turno nativo de recuperación, con retención de aprendizaje.

**Límite de identificabilidad fuera del prior:** una fuerza externa que
cancele exactamente cada acción puede imitar un cuerpo desacoplado. Se
ejecutarán ambos mecanismos y se publicarán sus trazas idénticas. La etiqueta
del modelo debe ser idéntica, no acertar dos causas privadas incompatibles.
La causa irrestricta queda no identificada: este testigo no se cuenta como
una atribución correcta fuera del prior. Toda salida positiva de la sesión
lleva el alcance fijo del modelo. No se usa una bandera privada de «caso OOD»
para obligar al consumidor a acertar o abstenerse.

## Criterios prospectivos por fase completa

1. Las 80 condiciones y sus denominadores completos; diagnóstico confirmado
   correcto en todas, cero falsos positivos o terminalidad diagnóstica en el
   dominio. Publicar coste y ensayos adicionales de confirmación.
2. Reutilización selectiva ≥60% total y ≥1/3 por clase; ventaja ≥5 puntos
   sobre cada control; ventaja propia frente a aprender todo y externa
   frente a congelar todo; sin pérdida nominal. Publicar pérdidas emparejadas.
3. Cero escrituras con efecto corporal en el selectivo; alguna en el control
   sin protección. Retenciones >0, todas sin alterar T/PATTERN; aprendizaje
   externo legítimo >0. Exposición idéntica y ablación no-T con igual pasado.
4. Vidas selectivas: ≥90% de los casos viables completados, cero muertes,
   al menos un éxito; sin protección ejecuta la misma política. Inviables y
   paradas se publican, no cuentan como éxito. La verdad debe sobrevivir en
   las hipótesis del selectivo y no se reescribe la referencia.
5. Todos los controles de abstención anteriores pasan, también el testigo
   de insuficiencia y el veto nativo. Publicar el testigo de indistinguibilidad
   externa sin convertirlo en certeza causal irrestricta.
6. WSP16, gate original, enteros, una CAM4096/T/Q por agente, presupuestos
   acotados, balance físico, cero hechos falsos, destrucción o córtex.
7. Fuentes congeladas, pruebas de integración y manipulación de evidencia,
   replay íntegro en proceso nuevo y revalidación completa de las seis cadenas
   previas: SENSATION, BOUNDARY, SELF-A, SELF-B, SELF-C v1 roja y SELF-C v2.

Los fallos mixtos de v2 no desaparecen: todos se desglosan y se conserva el
umbral previo de 1/3; no se exige falsamente un éxito universal ni se reduce
el listón al abrir B/C. Cierre significa satisfacer este dominio limitado.

El informe de campaña solo concede `closure_eligible`; `self1_green=false`
hasta auditoría completa. Solo el recibo de replay con padres válidos puede
dar `self1_green=true`. Smoke nunca. Cualquier criterio rojo mantiene el
cierre abierto; no se cambian los umbrales para aprobarlo.

Después del cierre: CONTINUITY. Hardware después del software; METAVERSE-1
último. Ningún certificado de este programa demuestra conciencia subjetiva.
