# COMPOSE-1 v2 — horizonte útil y ejecución situada

2026-09-14. Continuación autorizada por Roger hasta cerrar COMPOSE-1.
V1 se conserva, incluido su `compose1_green=false`. Esta versión se desarrolla
y mide en carpetas nuevas. CAUSE-1 va después del cierre, no se declara aquí.

## Hipótesis y defecto a corregir

V1 puntúa todos los prefijos de una búsqueda con el mismo coste por longitud.
Un prefijo barato puede ganar antes de que el efecto posterior justifique el
desvío. V2 compara consecuencias al horizonte o al final verificable de una
opción, y vuelve a verificar sólo el siguiente movimiento ejecutable.

Se comparan horizonte cuatro y uno cambiando únicamente ese límite; ambos
conservan memoria, exploración, Q, sensores, gate y reserva. Ganar puede ser
completar más metas o gastar menos movimientos con igual éxito y seguridad.
No se exige que el control falle todas las tareas. Una ruta de varios pasos
no prueba por sí misma planificación de varios pasos.

## Contrato conservado

WSP 16 bytes como representación y acción; CAM, T y Q importadas, enteras.
Ningún LLM, nueva LIF ni hardware. Un mapa obtenido de sensores puede cambiar
en B/C aunque T y Q permanezcan congeladas. Ningún rollout escribe episodios.
El mapa verdadero, semilla, identificadores y rutas permanecen en el evaluador.
Una coordenada de misión es una hipótesis de destino, no prueba de llegada.

El cuerpo inicial compone efectos de desplazamiento y observación de accesos,
sin manipular objetos. Los efectos de movimiento se aprenden por consecuencias;
la proyección geométrica de sensores es ingeniería proporcionada. No se afirma
descubrimiento de herramientas. Se mantiene coste abstracto hasta POWER-1.

## Dos puertas acumulativas

**Funcional:** ensayos nuevos de acceso indirecto, cambio de acceso, acceso
cerrado y reserva insuficiente. Horizonte 4 con presupuestos 8/32, horizonte
1, Q reactiva, búsqueda convencional y sin caducidad. Oracle sólo evaluador.
Aprendizaje/desarrollo A: semillas 20261901–20261932. Validación B:
202619101–202619228. Confirmación C funcional: 202620101–202620228.
No abrir B/C hasta congelar código, protocolo, modelo y controles en un lock.

Publicar por condición éxitos, pasos, reserva, revisiones, candidatos, P99,
memoria e intervalos emparejados. Cero hechos falsos, colisiones, fugas y
escrituras imaginadas en el completo. Exigir mejora frente a Q y evidencia
específica frente al horizonte uno: límite inferior del intervalo 95 % de
la diferencia emparejada de éxitos >0, o de ahorro de movimientos >0 sin
pérdida de éxitos; el segundo contraste se limita a parejas que ambos completan
y publica su denominador. Bonferroni: intervalos 97,5 % en esos dos contrastes
alternativos. No presentar el bootstrap degenerado como certeza poblacional.

**SITL:** el agente consume sensores/estimación pública, pide un objetivo
acotado, PX4 vuela, y la consecuencia observada decide el siguiente paso.
Ni teletransporte ni posición verdadera como odometría. Verificar separación
de marcos ENU/NED, captura/llegada y envolvente corporal antes del banco.
Sólo una orden WSP causal; planes y explicaciones son diagnósticos auditables.
El puente no lee el plano para seleccionar destinos. Verdad se usa únicamente
para adjudicar colisión, distancia y éxito físico a posteriori.

El desarrollo SITL fijará la resolución espacial, margen, plazo y presupuesto
de habilidades con medidas de A. Publicar todos sus intentos. Antes de B/C,
añadir aquí la configuración concreta y N, preservando esta especificación
inicial en el historial del desarrollo. No modificar umbrales tras el examen.
No consumir C sellado de TRANSFER-3 ni confundir rehearsal con ese examen.

## Configuración concreta previa al lock

El desarrollo identificó dos defectos distintos: puntuar prefijos baratos y
mantener una opción antigua pese a observar un acceso mejor. V2 puntúa las
consecuencias terminales y vuelve a buscar tras **cada** observación. El
horizonte uno hace lo mismo; sólo cambia la profundidad. La persistencia de
creencias y de visitas no se borra al replantear.

El cuerpo simulado es X500 con PX4 de la imagen fijada por FLIGHT-1S v6,
incluidos sus parámetros. Se añaden cuatro vistas de profundidad de 1,6 rad,
de la misma familia de evidencia, y se conserva RGB frontal y LiDAR. No son
cuatro votos independientes ni el montaje original de SENSOR-1S sin cambios.
No se modifica el controlador de vuelo. Despegue a 2,5 m: el EKF del binario
fijado exige superar 1,5 m HAGL para completar alineación magnética en vuelo;
no se fuerza su indicador de orientación válida.

Dominio: salas de celdas de 3 m, paredes extruidas de 4 m y vuelo a una altura.
El agente recibe una coordenada de misión y sensores; no recibe la planta.
No demuestra SLAM general, navegación volumétrica libre, herramientas ni
carga eléctrica. La estación es un marcador verde en una pared, identificado
por un detector cromático proporcionado, con llegada a su celda de acceso.
El mapa se construye a partir de rayos finitos. No retorno significa desconocido.

La proyección exige pose asentada: movimiento ≤250 mm/s e inclinación ≤100 mrad.
La ejecución obtiene muestras con límites más estrictos (200 mm/s y 80 mrad),
capturas ≤200 ms, posición solicitada a <400 mm y altura 2,5 ±0,3 m. Caducidad
de evidencia 250 ms; se conservan captura, llegada y hash de la extracción.
El ejecutor vuelve a comprobar esos 250 ms antes de aceptar una traslación
o inspección; un retraso del consumidor no autoriza ejecutar evidencia vieja.
El disco libre exigido mide 900 mm de radio: cuerpo de 400 mm y margen de
500 mm. El juez usa la pose física sólo para medir envolvente, llegada y
continuidad; no se entrega como odometría al agente. Límite de velocidad
horizontal del juez: 3 m/s. Llegada independiente: error horizontal ≤1 m.

T parte de habilidades separadas aprendidas en A cinemático y recibe 56
consecuencias de desplazamiento **observadas** en el primer vuelo de desarrollo.
El modelo espacial de ese vuelo no se hereda. T/Q quedan congeladas; el mapa
sensorial de cada misión empieza vacío. Energía abstracta: 240 unidades
(30 en reserva insuficiente), 4 por desplazamiento y 1 por inspección; reserva
de retorno por ruta conocida más 10. No son julios ni una prueba de POWER-1.

**N funcional definitivo:** 128 semillas por etapa ×6 modos =768 misiones en
B y 768 en C. Se amplía la propuesta inicial de 64 antes de abrir el examen:
en A muchas parejas empatan y sólo 10/16 tienen diferencia de coste. Se exige
además un test de signos unilateral p<0,025 en el contraste que cierre la
ventaja. No se aumentará N si falla el examen. Las 48 geometrías posibles se
muestrean con reemplazo: una semilla nueva no significa una planta inédita.
Se publican los límites de esta familia; TRANSFER-3 requiere su propio examen.

**SITL definitivo:** B =202619301, 202619303, 202619304, 202619305;
C =202619403, 202619404, 202619407, 202619408. Condiciones, en ese orden:
estática, estática, cambio de abertura, reserva insuficiente. Cada una se
ejecuta con completo, horizonte uno, Q y planificador convencional: 32 vuelos.
Estas ocho geometrías se seleccionaron por identidad geométrica, sin probar
su rendimiento, excluyendo las cuatro del desarrollo SITL y repeticiones
entre B/C. Pueden coincidir con salas del desarrollo cinemático de la familia.
El examen físico comprueba ejecución y percepción, no descubrimiento de
tipos de objetos ni generalización fuera de esta familia.

Puerta física: evidencia válida y cero violaciones de envolvente/reserva en
los 32 vuelos; órdenes ejecutadas por PX4 y aterrizaje; al menos 5/6 misiones
alcanzables completadas por el agente, y más llegadas que Q. Los dos casos
de reserva insuficiente deben abortar en origen sin desplazarse. Comparar
también coste/éxito con horizonte uno y convencional, sin exigir una ventaja
física significativa con sólo seis parejas alcanzables. La ventaja causal
del horizonte se juzga en las dos etapas funcionales, no en un vídeo.

Todos los episodios se ejecutan una sola vez. Una avería o un resultado rojo
se conserva; el mismo lock no se vuelve a lanzar para elegir la mejor cadena.
La C de este banco es confirmación interna y no consume C de TRANSFER-3.
La semilla física determina la sala; no afirma reproducir exactamente el
ruido y la temporización de PX4/Gazebo. Las parejas comparten geometría,
modelo y configuración, pero tienen realizaciones físicas independientes.
Las trazas registradas sí permiten reconstruir la decisión y su auditoría.

## Auditoría y cierre

Congelar inventario transitivo, protocolo, mundo/sensores y binario PX4.
Escribir predicción antes de ejecutar; conservar comando solicitado, acuse,
observación posterior, marcas de tiempo, trazas del backend y ULog. Reconstruir
las decisiones desde la entrada pública y adjudicar consecuencias con un juez
separado. Una alteración de un informe válido tiene que invalidar evidencia.

Mutantes mínimos: horizonte sustituido, T ignorada, mapa privado, observación
caducada usada para avanzar, rollout escrito, llegada inventada, reserva
ignorada y movimiento por pose. Publicar también un fracaso controlado.
`compose1_green` requiere ambas puertas, regresiones focales y auditoría válida;
tests aislados o una misión favorable no bastan. Los límites de PX4-1,
POWER-1 y SAFE-1 quedan pendientes de sus propios contratos.
