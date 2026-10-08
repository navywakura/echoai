# PATTERN-1R v2 — corregir el banco antes de juzgar la identidad

**2026-09-14. Implementación autorizada tras el cierre de DYNAMIC-1 v2.**
Estado inicial: desarrollo, sin lock ni verde. El código y los vuelos originales
de PATTERN-1R se conservan: están incluidos en el lock de DYNAMIC-1 v2.
Esta revisión vive en `nexus0/pattern1r_v2/` y `lab/pattern1r-v2/`.

## Defectos comprobados

1. El consumidor emite siluetas con al menos cuatro ecos; el evaluador avanza
   por todas las de tres o más. Una omisión desplaza las etiquetas del resto
   del vuelo. En `honest-w0`: 3.477 siluetas, 3.446 firmas, 31 omisiones y
   2.583 emparejamientos temporales incorrectos. Ese vuelo además no acabó el
   reconocimiento. Corregir sólo la alineación deja cuatro de los otros cinco
   vuelos con identidad aceptable; no arregla todos los fallos ni cierra la fase.
2. El arco de 5 m invade la envolvente horizontal de 400 mm del X500 en los
   doce mundos: separación mínima muestreada 155–366 mm. Varias trazas salen
   muy lejos del suelo del mundo. No se atribuye una colisión concreta sin
   sensor de contacto, pero el recorrido no respeta la envolvente declarada.
3. Una pista podía asignarse a varias siluetas; los huecos se representaban
   mediante un intervalo contiguo ficticio y el corte angular podía duplicar
   una silueta. Son defectos de correspondencia, no evidencia de aprendizaje.
4. El control quitaba `survey` de la configuración, pero la sesión lo activaba
   por defecto. El agregador incluía esos controles como reconocimientos
   positivos. Además, sumaba confusión con un denominador ausente (siempre cero)
   y exigía al mutante constante fallar acierto, aunque su fallo es el colapso.

Los diagnósticos retrospectivos se guardan bajo `lab/pattern1r-v2/review/`.
No son una evaluación independiente ni sustituyen los resultados originales.

## Cambios y pregunta

Se mantiene la pregunta: formar familias anónimas con firmas enteras de 16 bits
y reconocer los mismos objetos en vistas posteriores, con memoria congelada,
sin recibir identidad, posición, plan de vuelo ni verdad del mundo.

- Segmentación circular una sola vez, con índices de ecos reales. Cada firma
  queda vinculada en el evaluador a **su emisión concreta y sus haces**, sin
  desplazar una lista global al omitir una observación. Esa procedencia es
  instrumentación del evaluador; el aprendiz sigue recibiendo sólo la firma.
- Correspondencia por proximidad entre barridos, con una sola asignación por
  pista. Se mantienen tamaño máximo observado, código termómetro, pasos de
  300 mm y memoria `InvariantPatternMemory` de ECHO-2, importada y sin cambios.
  No se afirma compensación general del movimiento propio ni recuperación de
  identidades tras oclusiones largas.
- Reconocimiento rectangular de 48 objetivos alrededor de las barreras, con
  1.200 mm de separación nominal, altura 1.500 mm, llegada de 500 mm, sin
  parada y máximo de 12 s por tramo. Empieza por el objetivo más cercano al
  spawn. Antes de volar se comprueba la envolvente de 400 mm, el suelo y el
  tramo inicial. El arnés conoce la geometría para preparar el experimento;
  el consumidor y el aprendiz no reciben ese recorrido.
- PX4 sigue ejecutando objetivos acotados a 1 m/s. No cambian PID, imagen,
  sensores ni controlador. Se registra también la separación observada de las
  barreras durante el reconocimiento: una invasión de la envolvente es roja.
- El control sin reconocimiento envía explícitamente `survey=false`. Debe
  volar sano y traducir sensores, pero no acreditar diversidad de vistas.
- Confusión agregada calculada con conteos reales. Cada objeto evaluado debe
  tener al menos 20 observaciones de escuela y 20 de examen. Se publican las
  observaciones sin correspondencia y las ambiguas; no se convierten en aciertos.

## Criterios antes de vuelos nuevos

Se conservan acierto ≥0,75, confusión ≤0,15, pureza escolar ≥0,60, dos objetos
en familias distintas, al menos 90 % de los 48 tramos alcanzados y memoria
sin escrituras en examen. Escuela: posiciones 0–31; examen: 32–47.
Los grupos heredados de sensores y GROUND siguen siendo obligatorios.
El nuevo criterio geométrico y la cobertura por objeto no relajan esos límites.

Mutantes: `constant_family` debe fallar `objects_separated`; `range_leak` y
`beam_index`, el reconocimiento; `replay`, recomputación de firmas;
`frozen_write`, memoria congelada; `extra_channel`, cable único. Cada mutante
necesita vuelo sano y gemelo honesto aprobado. Se probarán también informes
manipulados partiendo de un informe válido.

Primero desarrollo conservado en los seis mundos usados para diagnóstico.
Sólo si el candidato funciona se congela una cadena: A con 8 vuelos + 2
controles sin reconocimiento; banco con 12 vuelos + 6 mutantes. Una corrida
por mundo y etapa. Sin selección retrospectiva de episodios ni reintentos
posteriores al tratamiento; se hereda sólo la política de reinicio previo al
tratamiento de FLIGHT-1S v6. Semillas de etapa: 20261411 y 20261412.

Antes del lock se ejecutan las pruebas específicas v2 y las regresiones
PATTERN-1R/DYNAMIC-1 v2. La regresión previa de DYNAMIC (652 pruebas) y sus
inventarios preservados respaldan el núcleo que no se modifica. Cada cambio
posterior exige revisar su alcance; tests verdes no sustituyen vuelos nuevos.

## Alcance

La familia es la misma de doce mundos rehearsal; las semillas de etapa no
crean salas reservadas. El examen separa vistas dentro del vuelo, no demuestra
transferencia conductual entre mundos. Sólo hay paredes grises distinguibles
por longitud: no semántica de objetos, estación de carga, manos ni herramientas.
El agente no decide el vuelo; córtex apagado y hardware ausente. No se abre C
sellado, no hay segundo bus cognitivo y no se modifican WSP, Q, T ni CAM.
Las firmas se extraen en el consumidor aislado durante el vuelo. La memoria
de familias se entrena y examina mediante replay en el evaluador; no dirige el
vehículo en vivo. El verde de este banco, si llega, acreditará ese componente
sensorial y su examen, no integración causal con la política de navegación.

## Candidato 2, declarado antes de sus vuelos

La primera tanda completa queda **roja** y conservada en `development-report.json`:
cuatro mundos verdes, uno con confusión 0,1867 y otro con sólo 38/48 objetivos
alcanzados por pérdida de altura. El nuevo recorrido sí mantuvo separación.
El código de ese candidato se guarda en `review/candidate1-code/`.

Se adoptan tres cambios, sin relajar umbrales ni repetir sólo los fallos:

1. **Madurez de familia: 32 observaciones**, mediante el parámetro existente
   `InvariantPatternMemory(min_hits=32)`. No cambia el núcleo de ECHO-2 ni la
   formación de prototipos. El replay preregistrado 4 frente a 32 sobre los seis
   vuelos reduce confusión; el peor caso queda en 0,1390 con acierto 0,8112.
   Los desconocidos siguen contando. No son observaciones independientes y el
   replay no es confirmación. Es el único presupuesto alternativo ensayado.
2. **Altitud explícita.** En esta versión de PX4 el navegador usa `param7` de
   DO_REPOSITION como altitud absoluta. El ULog muestra objetivo global 1,5 m,
   aunque la casa está a 0,272 m y el despegue sí se refería a ella. El runner
   nuevo declara `MAV_FRAME_GLOBAL_INT` y fija una conversión constante al
   comenzar el recorrido: altitud GLOBAL_POSITION_INT menos z del modelo.
   Después manda `z_objetivo + offset`; no recalibra usando la pose verdadera
   durante el recorrido. Es el mismo tipo de alineación inicial que ya existía
   para latitud/longitud. Se registra la referencia privada usada.
3. **`EKF2_HGT_REF=0` (barómetro)** para el perfil de reconocimiento largo.
   El primer candidato conservaba GPS como referencia vertical: el sesgo
   barométrico estimado pasó de −0,426 m a −0,984 m entre 40 y 200 s en w5,
   mientras el cuerpo se alejaba del objetivo. Cambia esta referencia del
   estimador, no PID, sensores, ruido, imagen ni autoridad PX4. Su efecto debe
   validarse en vuelos nuevos; no lo cubre automáticamente el verde FLIGHT-1S.

También se corrige el examen de mutantes: una firma equivocada con su emisión
y timestamp bien alineados debe poder puntuarse contra su objeto, aunque falle
la recomputación honesta. El evaluador anterior devolvía antes de medir identidad,
por lo que no podía atribuir el rojo al mutante constante o al de distancia.
Una emisión desalineada o mal formada sigue siendo inválida, sin puntuación.

El candidato `maturity32-baro` volará nuevamente los seis mundos completos,
semillas de desarrollo 20261421–20261426. Consumidor, contrato, sesión,
evaluador y runner quedan fijados durante esa tanda. Se conservan sus planes,
logs y resultados separados. Sólo una tanda completa verde permite congelar A.
Las semillas, muestra y criterios de aceptación descritos arriba se mantienen.

### Corrección de interfaz previa al vuelo

`maturity32-baro` terminó con seis errores `unexpected flight parameter`, cero
frames y cero despegues: faltaba `EKF2_HGT_REF` en la lista permitida del driver.
Su plan, informe y runner se conservan. No mide reconocimiento ni la hipótesis
barométrica. Se añade ese parámetro y una prueba que ejecuta la clase real contra
la configuración completa, comprueba lectura posterior y rechazo de parámetros
ajenos. Sin otro cambio de tratamiento, `maturity32-baro-driver` repetirá los seis
mundos con semillas 20261431–20261436. También se conserva el replay de mutantes:
los cinco errores algorítmicos disparan su caso nominado sobre desarrollo; esto
no sustituye sus vuelos de aceptación.

`maturity32-baro-driver` tampoco despegó: PX4 devolvió `param types mismatch`
para `EKF2_HGT_REF`. El driver anterior enviaba todos los parámetros como REAL32.
Se conserva íntegramente la tanda; se envía y decodifica ese entero con INT32
(codificación bytewise de PX4), con lectura posterior obligatoria. La prueba
de interfaz exige ahora el tipo correcto. `maturity32-baro-int` repite todos
los mundos con semillas 20261441–20261446 y los mismos criterios y tratamiento.

Durante esa tanda se detectó otra colisión en el coordinador heredado: el grupo
`frozen` de hashes del código sobrescribía al `frozen` del examen sin escrituras.
El primero se llama ahora `integrity`, tanto en construcción como en auditoría.
Una prueba con escritura real en la memoria verifica que la integridad correcta
del código no puede ocultar ese rojo. No cambia ninguno de los cinco archivos
del candidato en vuelo ni su evaluación por episodio; se corrige antes del lock.
