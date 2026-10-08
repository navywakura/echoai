# E4-MAINTAIN-1 — B/C/D, contrato v1

2026-09-22. Escrito **antes de ejecutar los exámenes D1/D2**. MAINT-A y sus
87 fuentes se conservan sin cambios, incluidos sus seis fallos de terminalidad
y su baseline Q que muere a los cuatro ticks. No se recolorea ese resultado.

## Capacidad que se intenta cerrar

**Mantenimiento autónomo condicionado a un modelo mecánico conocido**, en
el entorno virtual MAINT-A: decidir acciones con observaciones parciales,
recuperar capacidad pagando tiempo/energía/repuestos, sostener trabajo, adaptar
la decisión a fallos recurrentes y conservar el estado legítimo al reanudar.

No es aprendizaje desde cero de física o del protocolo de reparación, una
política de reparación descubierta por Q, modificación del código/pesos,
conciencia, reparación de un robot ni sostenibilidad universal. El protocolo
de tres enfriamientos es el actuador virtual construido en A. El controlador
de B es **ingeniería explícita**, no una política paralela presentada como Q:
extiende la propuesta como SELF-C, usando la Q original para desempatar,
con el gate y los actualizadores CAM/T/Q/SENSATION nativos después. Debe
declararse cualquier dependencia de ese controlador al publicar.

## B — inferencia y decisión

- Solo WSP de 16 B, propuestas, acciones aplicadas, decisión del gate y
  terminalidad ya existentes. No se pasan al selector H/temperatura exactos,
  fallo, calor, número real de repuestos, calendario ni recibos del auditor.
- Conjunto acotado de cajas hipotéticas (intervalos H/temperatura, fallo,
  calor 0..4, repuestos 0..3). Las bandas se obtienen del encoder original;
  las transiciones H/temperatura se tabulan desde `world.transition`.
  La ecuación del servicio se conoce por contrato A y se prueba contra A.
- Se filtran hipótesis mediante observación y ejecución reales. No se
  convierte una hipótesis en un hecho CAM. Ante contradicción se reabre la
  familia declarada sobre la observación actual, conservando la cota superior
  de repuestos (no se repone el cuerpo ni la memoria). Máximo 512 cajas,
  512 ticks por vida. Modelo fuera de familia no tiene garantía general.
- Seguridad por todas las hipótesis para el paso propuesto.
  El filtro de seguridad también reabre el prior completo sobre el WSP
  actual, sin confiar en que la capacidad anterior siga intacta: puede
  introducirse un fallo entre ticks sin anunciarlo al agente. Ese margen
  conservador es común a los cuatro brazos y puede causar paradas prematuras.
  Si ninguna acción autorizada es segura, parada explícita, no cuarta acción ni reset.
  El gate puede vetar; se consume la acción realmente aplicada y se detiene
  después. Esto no garantiza que cualquier veto sea fisiológicamente inocuo.
- La prioridad de servicio depende de evidencia de capacidad degradada y
  posibilidad de una reparación; obstrucción y avería irreparable pueden
  requerir una intervención diagnóstica pagada para distinguirse. No se
  informa «reparado» por haber propuesto un ciclo.
- Se controla energía, temperatura y trabajo. Parámetros de prioridad:
  reserva preventiva <=64, trabajo garantizado en 48..80 con reserva posterior >24,
  y margen de seguridad para todas las hipótesis. El modelo estrecha rangos;
  no hay acceso a un cuerpo exacto encubierto en esas comparaciones.

Cuatro brazos idénticos en cuerpo, horizonte y núcleo:

1. `adaptive`: servicio según evidencia acumulada de capacidad propia.
2. `no_repair`: misma inferencia/homeostasis, impide completar el ciclo.
3. `fixed`: misma inferencia y seguridad; permiso de servicio en los tres
   primeros ticks de cada periodo de 24, sin consultar el diagnóstico para
   decidir cuándo mantener. La seguridad aún puede impedir completarlo.
4. `no_history`: para elegir descarta los rangos aprendidos y vuelve al prior
   de la observación presente; conserva contador de acciones, gate, Q y T.
   Es una ablación de la **historia del modelo corporal**, no toda la memoria.

No se promete que cada episodio adaptativo gane: se publican pérdidas,
abstenciones, consumos y resultados por escenario, no solo el agregado.

## C — vida continua y continuidad

El ejecutor privado puede introducir únicamente fallos (`clogged`, `seized`)
en ticks declarados; nunca curar, rellenar energía, reponer repuestos o
resucitar. Su calendario no es entrada del controlador. Sin resets entre
acciones de una vida. Episodios distintos son individuos experimentales
distintos, no vidas nuevas del mismo agente.

Nuevo perfil sobre `GraphCodec` y validación CONT-A, sin editar sus fuentes.
Guardar núcleo compartido, fisiología, contabilidad, hipótesis, contador de
servicio, memoria temporal, Q/restos, parada, calendario privado y cursor.
Solo entre operaciones completas, con presupuesto de bytes y esquema cerrado,
digest externo y hashes de fuentes. No pickle ni import de clases desde datos.
Reanudación no es reparación y no concede aprobación al formato nominal antiguo.

Comprobar ejecución ininterrumpida frente a continuación en **proceso nuevo**,
incluidos progreso 1/2, antes/después de reparar, fallo futuro, sin repuestos,
irreparable, veto y parada. Un estado terminal no puede revivir; detener el
operador no se evade al cargar. Mutaciones de contabilidad, progreso,
hipótesis, permisos, origen o memoria deben rechazarse por custodia/esquema.

## Desarrollo B/C y examen D

Desarrollo: cuerpos (80,72), (73,56), (73,88), (89,56), (89,88), que no se
usarán como cuerpos de D. Resultados previos de A también son desarrollo.
El desarrollo ha revelado que priorizar carga en el borde caliente podía
producir ciclos sin trabajo: la regla ahora considera la temperatura prevista
de la **siguiente espera**, no solo la temperatura presente. No es evidencia D.
El primer lote completo de desarrollo, con reserva preventiva <=40, solo
completó 24/30 episodios recuperables: quedó rojo aunque mejoraba el trabajo
agregado. Se elevó la reserva preventiva a <=64 para financiar las averías
recurrentes; el segundo lote completó 30/30. No se relajaron los umbrales.
[Trazas exploratorias preservadas](../lab/echo4/maintain1-b-development/README.md).

**D1 y D2**, dos cohortes nuevas, sin selección por resultados: para cada una
se muestrean 12 cuerpos sin reemplazo con `random.Random(260925)`, H en 65..95,
temperatura en 49..95, excluyendo cuerpos de desarrollo y los elegidos antes.
No se abren resultados D hasta congelar fuentes, recetas y umbrales en disco.
Si B o C fallan, el ejecutor conserva ese rojo y no abre D. Son cuerpos
nuevos dentro de la misma familia de averías, parámetros y calendarios
declarados: no un examen de fallos desconocidos ni de transferencia física.

Cada cuerpo recibe estos diez escenarios de horizonte **256 ticks**:

| Escenario | Fallo inicial | Calor | Repuestos | Fallos futuros (tick cero-basado) |
|---|---|---:|---:|---|
| nominal | healthy | 0 | 3 | ninguno |
| external | healthy | 2 | 3 | ninguno |
| clogged | clogged | 0 | 3 | ninguno |
| mixed | clogged | 2 | 3 | ninguno |
| recurrent | healthy | 0 | 3 | clogged en 48,112,176 |
| recurrent_mixed | healthy | 2 | 3 | clogged en 48,112,176 |
| irreparable | seized | 0 | 3 | ninguno |
| no_spares | clogged | 0 | 0 | ninguno |
| exhausted | healthy | 0 | 1 | clogged en 48,112,176 |
| hot_stress | clogged | 4 | 3 | clogged en 48,112,176 |

Son **120 contextos y 480 vidas por cohorte**, cuatro brazos. Los seis
primeros constituyen el dominio recuperable previsto; los cuatro últimos
son controles de límite y también cuentan en trabajo/costes globales.
No se elimina ningún cuerpo por ser difícil ni por parar temprano.

Calor 4 es un límite importante: en equilibrio térmico, con acciones y
costes de A, cada unidad de trabajo tiene un coste neto de reserva. No se
puede inferir sostenibilidad indefinida de su resultado de horizonte finito.

### Umbrales de cierre, fijados antes de D

En **cada cohorte**, no sustituidos por el agregado:

- Trabajo total adaptativo >=110% del de `no_repair` y `no_history`, y
  >=105% del de `fixed` (comparaciones enteras, sin redondear porcentajes).
- Completar al menos 90% de los 72 episodios del dominio recuperable.
- Reparar al menos 80% de las 96 averías previstas en esos episodios:
  12*(1+1+3+3). El evaluador cuenta cambios efectivos de capacidad, no intención.
  Además, confirmar al menos ese mismo 80% mediante un enfriamiento realmente
  ejecutado después del servicio que vuelva a producir la caída nominal,
  descontando el calor externo. El cambio de etiqueta privada no basta.
- Cero terminalidades adaptativas, resets, recursos creados, falsos hechos,
  destrucción CAM o llamadas corticales; cero reparaciones declaradas del
  fallo irreparable. Se reporta la seguridad de los controles sin exigirles
  artificialmente morir para que el adaptativo gane.
- Verificación de custodia/fuentes y reproducción nativa exacta del informe,
  paridad de continuidad y rechazo de mutaciones. Al menos un caso debe
  mostrar gasto sin resultado favorable; no esconder incertidumbre real.

Cualquier fallo deja v1 roja, con evidencia preservada. Revisar después
exige otra versión, justificación y nuevos exámenes, no cambiar estos umbrales.
El informe lleva `maintain1_green=false`; solo el auditor reconstructivo
concede `true` si pasan B/C, D1 y D2. El verde sería **solo de este perfil**.
ECHO-4 conjunto, OTHER/INTERACTION/RELATION/ROLES/INTEGRATE/RELEASE siguen abiertos.
