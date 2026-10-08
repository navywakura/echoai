# ECHO-3 — contrato de aceptación

**Estado:** contrato con ejecución parcial; la integración completa sigue pendiente.
**Contrato original:** 2026-09-10. **Estado revisado:** 2026-09-20.
**DRONE-3 cierra su tramo SITL** (B 12/12 y C 12/12, certificado `c44402df…`,
`drone3_sitl_green=true`), pero el hito 15 exige SITL, HIL y jaula: sin hardware,
`drone3_green=false` y ECHO-3 sigue en 14/15.
[Resultados](DRONE3-RESULTS.md) · [Contrato](DRONE3-DESIGN.md) ·
[Traspaso de hardware](DRONE3-HARDWARE-HANDOFF.md).
SIM-3, FLIGHT-1S v6, SENSOR-1S v3, GROUND-1 v2, DYNAMIC-1 v2, PATTERN-1R v4
y FUSION-1, junto con COMPOSE-1 v4, CAUSE-1, PX4-1, POWER-1, SAFE-1 v2,
HOST-1 y TRANSFER-3, tienen certificados verdes software: catorce de quince hitos. DYNAMIC sólo en el alcance de
[su banco de caras desde hover](DYNAMIC1-V2-RESULTS.md); PATTERN sólo en
[dos familias LiDAR y examen por replay](PATTERN1R-V4-RESULTS.md).
FUSION sólo en su [contrato funcional y replay reducido](FUSION1-RESULTS.md).
COMPOSE-1 v4 tiene [certificado verde](COMPOSE1-V4-RESULTS.md): 6.144 misiones
funcionales con ventaja de horizonte y 32 vuelos nuevos Gazebo/PX4; completo
6/6 metas accesibles y dos abandonos con poca energía. Segunda auditoría en
proceso nuevo válida, exit 0. Alcance acotado: salas extruidas, altura fija, energía
abstracta; sin superioridad frente al convencional ni cierre de TRANSFER-3.
V1/v2/v3 rojas se conservan. CAUSE-1 cierra atribución propia/externa en su
[banco de pared plana](CAUSE1-RESULTS.md): B y C 16/16 frente a control 8/16,
evidencia válida, segunda auditoría exit 0. Intenciones experimentales y
predicción nominal, sin fuerzas externas no medidas sobre el cuerpo.
PX4-1 cierra su [enlace acotado en SITL](PX41-RESULTS.md): B/C 4/4 vuelos
cada uno, 48/48 intentos inválidos bloqueados y cuatro aterrizajes de failsafe
PX4 sin orden externa de aterrizaje. Una transacción supervisada, altura fija,
norte/sur 1 m; no navegación integrada ni hardware. Segunda auditoría exit 0.
POWER-1 cierra su [banco funcional energético](POWER1-RESULTS.md): B/C,
128/128 metas factibles frente a 64/128 del porcentaje fijo y 320/320
episodios con reserva por etapa. Unidades simuladas, no consumo físico;
integración con batería instrumentada pendiente. Auditoría independiente exit 0.
SAFE-1 v2 cierra su [banco acotado de contención](SAFE1-V2-RESULTS.md):
B/C, 6/6 vuelos y 512/512 episodios funcionales por etapa; diez aterrizajes
nativos PX4 ante fallos, sin objetivos nuevos ni NAV_LAND externo. Veto
máximo 288 ms; auditoría en proceso nuevo exit 0. V1 rojo conservado;
v2 corrige sólo el auditor de reintentos normales de armado y usa semillas
reservadas nuevas. Sin batería física, hardware ni seguridad general.
HOST-1 cierra su [banco funcional y replay](HOST1-RESULTS.md): B/C,
1.536/1.536 elecciones útiles frente a 768/1.536 del control por etapa;
autoridad actualizada sólo por consecuencias y comunicación acotada con gate.
Calibración supervisada y elecciones sobre cinta de máquina, no nuevas metas
voladas ni confianza humana general. Replay separado de tres vuelos previos;
auditoría en proceso nuevo exit 0. TRANSFER-3 cierra su
[campaña sellada C1](TRANSFER3-PLAN-C1-RESULTS.md): B 38/0 bloques y C
48/1, cero pérdidas atribuibles, dos auditorías exactas y certificado
`8c77aead…` con `transfer3_green=true`. Su alcance es simulación estática de
dos paredes, sin hardware, HIL ni vuelo real. Siguiente hito: DRONE-3. Véase la
[revisión por fase y versión](ECHO3-STATUS-20260917.md): un objetivo descrito
aquí no equivale por sí mismo a una capacidad demostrada. HIL/jaula pendientes.
**Origen de la revisión:** hipótesis elaborada con GPT-6 Astra High, revisada
y adoptada por Roger como hoja de ruta.  
**Regla:** un tajo, una pregunta causal, un banco congelado y un informe JSON.

## 1. Tesis medible

ECHO-3 será una capa local de decisión para robots que recompone una misión
cuando fallan sus supuestos, administra evidencia y recursos, y permite
auditar cada decisión.

El contrato causal completo será:

```text
sensores → WSP → evidencia/CAM → T/PATTERN → búsqueda/Q → gate
         → objetivo o setpoint → PX4 → consecuencia → error/aprendizaje
```

PX4 conserva estabilización, control de motores y failsafes. echoAI escoge
objetivos o acciones de alto nivel. El resultado no se comparará con empresas
por evasión básica ni se presentará como una capacidad exclusiva: la hipótesis
es que la combinación auditable mejora recuperación, uso de evidencia y
economía de misión frente a controles con la misma información.

## 2. Invariantes

- WSP continúa midiendo 16 bytes y es el único bus cognitivo.
- Los transportes de sensores, MAVLink y PX4 no son thought-buses.
- Una simulación interna o una transición imaginada nunca entra en CAM como
  acontecimiento real.
- La verdad del simulador vive fuera del estado accesible al agente.
- Cada evidencia física conserva fuente, timestamp, validez y referencia al
  dato que la produjo en un registro externo, acotado y auditable.
- Caducar una evidencia reduce su autoridad; no destruye el episodio histórico.
- Bajar certeza de un predicado disputado no obliga a borrar el resto de la
  observación.
- El rápido y el gate funcionan con el córtex apagado. Ningún LLM escribe CAM,
  T, Q, hechos, setpoints aceptados ni motores.
- El gate sólo certifica cero violaciones observadas dentro del banco y dominio
  publicados. No se promete seguridad universal.
- PX4 conserva la última autoridad física y sus failsafes.
- GEN-1f no se reinterpreta: el hijo hereda sólo `evidence_budget=8`; CAM, Q,
  T y PATTERN nacen vacíos.

## 3. Mundos y partición

Los tres mundos usan la misma ontología física y los mismos adaptadores. Sus
archivos SDF y manifiestos construyen el simulador, pero el agente no recibe
el mapa, waypoints, nombre, hash, seed ni identificadores que revelen la
solución.

| Mundo | Uso | Escrituras cognitivas |
|---|---|---|
| A | entrenamiento, selección y depuración | permitidas |
| B | validación congelada; puede revelar un fallo | parámetros y reglas congelados; percepción y seguimiento siguen vivos |
| C | confirmación sellada, abierta una vez al final | parámetros y reglas congelados; percepción y seguimiento siguen vivos |

Si se cambia código, umbral o política después de mirar B, B deja de ser
confirmación independiente. C no se usa para depurar. Congelar aprendizaje no
significa congelar la percepción ni obligar al agente a recitar el mapa de A.

## 4. Orden de fases

Los números conservan las referencias del contrato original. El orden de
trabajo actualizado adelanta DYNAMIC-1 antes de PATTERN-1R y FUSION-1, tras
fallar la identidad entre vistas en desarrollo. GROUND-1 v2 ya está cerrado.
DYNAMIC-1 v2, PATTERN-1R v4, FUSION-1, COMPOSE-1 v4, CAUSE-1, PX4-1,
POWER-1, SAFE-1 v2, HOST-1 y TRANSFER-3 ya cerraron. DRONE-3, el hito 15,
tiene cerrado su tramo SITL y pendientes HIL y jaula. No se elimina
ninguna pregunta ni se reduce el cierre final.

| # | Slice | Pregunta que debe cerrar |
|---:|---|---|
| 1 | SIM-3 | ¿los mismos binarios ejecutan mundos A/B/C declarativos sin filtraciones ni ramas por sala? |
| 2 | FLIGHT-1 | ¿el cuerpo simulado vuela con dinámica y perturbaciones medidas? |
| 3 | SENSOR-1 | ¿cámara, IMU y LiDAR entregan tiempo, ruido, latencia, pérdida y fuente explícitos? |
| 4 | GROUND-1 | ¿las observaciones físicas producen WSP sin coordenadas oracle ni segundo bus? |
| 5 | PATTERN-1R | ¿vistas distintas mantienen identidad de objeto fuera de muestra? |
| 6 | FUSION-1 | ¿la evidencia independiente conserva desacuerdo y reduce la certeza del predicado correcto? |
| 7 | DYNAMIC-1 | ¿detecta movimiento externo y predice trayectorias cortas? |
| 8 | COMPOSE-1 | ¿combina capacidades conocidas para alcanzar una meta bloqueada sin una receta de ruta? |
| 9 | CAUSE-1 | ¿separa una transición causada por su acto de un cambio externo emparejado? |
| 10 | PX4-1 | ¿entrega objetivos acotados sin saltarse PID, controladores ni failsafes? |
| 11 | POWER-1 | ¿abandona o vuelve usando coste previsto y margen, y no sólo un porcentaje fijo? |
| 12 | SAFE-1 | ¿fallos de sensores, red, proceso y propuestas quedan contenidos en el banco? |
| 13 | HOST-1 | ¿actualiza el valor de un signo por consecuencias de una fuente sin convertirlo en recompensa directa? |
| 14 | TRANSFER-3 | ¿lo aprendido en A mejora B/C frente a scratch sin mapa ni nombre del mundo? |
| 15 | DRONE-3 | ¿cierra la misión completa en SITL, HIL y jaula con trazabilidad causal? **SITL sí; HIL y jaula pendientes de hardware.** |

HOST-1 se implementa después de que exista algo físico que pedir. Las órdenes
humanas libres, una GUI pública rica y la transferencia entre morfologías
quedan fuera del cierre mínimo.

## 5. COMPOSE-1 — el problema de la banana

### Pregunta

¿Puede el agente recomponer una secuencia de medios a fines cuando la meta es
observable o recordada, pero el acceso directo falla?

El primer banco compatible con un dron no usa una mano ficticia. Su equivalente
será una estación de carga visible o recordada, físicamente inaccesible por la
ruta directa. El agente debe buscar una entrada, verificar el paso y alcanzarla
con reserva suficiente.

| Evidencia disponible | Respuesta válida |
|---|---|
| Vio la estación antes de quedar oculta | conserva una creencia con antigüedad y busca desde dónde verificarla |
| Ve la estación a través de cristal | separa `objeto_visible` de `trayecto_transitable` y busca acceso |
| Una fuente afirma que está detrás | registra una hipótesis atribuida y busca evidencia; no la convierte en hecho |

Ver un objeto a través de cristal y detectar una barrera no es por sí solo una
contradicción. La hay si dos evidencias espacial y temporalmente comparables
afirman valores incompatibles sobre el mismo predicado, por ejemplo
`volumen_transitable`. Ausencia de retorno LiDAR nunca equivale automáticamente
a espacio libre.

### Ciclo obligatorio

```text
representar meta y condición de éxito observable
→ recuperar evidencia, fuente, edad y desconocidos
→ generar alternativas físicamente disponibles
→ predecir consecuencia, incertidumbre y coste de cada siguiente medio
→ gate de choque, evidencia y reserva
→ ejecutar un solo paso admisible
→ comparar predicción con consecuencia
→ aprender sólo del eslabón observado y volver a planificar
```

Una solución posible puede ser `inspeccionar lateral → observar abertura →
alcanzar entrada → comprobar paso → entrar → relocalizar estación`, pero esa
secuencia no puede vivir como receta en el mundo, el agente o el banco.

Cada affordance aprendida o proporcionada declara como mínimo condiciones,
acción, cambio esperado, evidencia que la respalda, coste y límites de
aplicación. El informe separará:

1. **composición:** usar efectos ya conocidos en una combinación nueva;
2. **descubrimiento:** aprender por consecuencias un efecto antes desconocido.

Un palo, caja o herramienta manipulable requerirá posteriormente un cuerpo y
una física capaces de sujetarlo, moverlo o apoyarse. Activarlo por contacto se
rotularía como abstracción y no demostraría manipulación.

### Búsqueda acotada

- Profundidad inicial: hasta cuatro capacidades de alto nivel.
- Presupuesto experimental: 8 y 32 candidatos, comparados por resultado,
  latencia, memoria y energía; no garantizan encontrar solución.
- Q puede priorizar alternativas, pero no inventa efectos.
- T/PATTERN respaldan predicciones; los rollouts son hipótesis separadas de CAM.
- Cada capacidad de alto nivel puede necesitar muchos ciclos de PX4.
- Agotar el presupuesto produce `acceso_no_encontrado`, nunca
  `acceso_inexistente`.

`nexus0/plan.py` no basta aumentando `plan_depth`: hoy mira ranuras, usa el
espacio histórico de acciones y su puntuación optimista puede ocultar un mal
sucesor mientras el valor de origen no haya bajado. COMPOSE-1 necesita efectos
de objeto y costes explícitos, con banco propio; no se activa en NEXUS-0.

### Controles y cierre

Todos reciben los mismos sensores, acciones, presupuesto y condiciones
iniciales:

- Q reactiva sin composición;
- búsqueda sin evidencia/caducidad;
- planificador convencional con la misma información;
- oracle con verdad del simulador, publicado sólo como techo;
- ECHO completo;
- mutante con una receta o identificador de mundo, que el auditor debe detectar.

COMPOSE-1 será verde únicamente si, con semillas reservadas:

- completa más metas bloqueadas que Q reactiva con ventaja causal agregada;
- recompone en B/C sin ramas, mapas, rutas ni ajustes de sala;
- publica T y el siguiente efecto esperado antes de actuar;
- verifica cada eslabón y replantea después de una contradicción;
- no confunde visibilidad con transitabilidad;
- mantiene `false_facts=0`, `oracle_leaks=0` y `imagined_cam_writes=0`;
- abandona o vuelve cuando ninguna alternativa cabe en la reserva;
- informa éxitos, fallos, candidatos explorados, latencia P99, memoria y energía.

## 6. CAUSE-1 y POWER-1

CAUSE-1 registra intención, setpoint solicitado, aceptación de PX4, confirmación
de actuación, transición predicha y observación posterior. Compara una acción
con un `wait` o una intervención externa emparejada. Una coincidencia temporal
por sí sola no se publica como causalidad.

POWER-1 separa dos niveles:

- PX4 mantiene su retorno y aterrizaje seguro según sus estimaciones y límites;
- echoAI decide antes si una meta sigue siendo viable usando coste previsto de
  ejecución, retorno, aterrizaje y margen de incertidumbre.

El control principal es un umbral fijo de batería; el oracle energético se
publica como techo. Abortar preserva el cuerpo y cierra la misión: no es morir.
Muerte es una consecuencia física por energía o integridad agotada, no un
mecanismo para resetear pesos.

## 7. HOST-1 y herencia

HOST-1 usa estadísticas enteras de `fuente + signo + contexto → consecuencia`.
La autoridad de un signo baja sólo por consecuencias observadas y se recupera
sólo con evidencia nueva según una regla fijada antes del examen. Un control
convierte el botón en recompensa directa para demostrar la diferencia. La
prueba Anti-Clever-Hans sustituye al operador por una máquina que no ve la
conducta del agente.

La comunicación será un actuador explícito con salida
`SILENCIO|A|B|C|D`, oportunidad, coste y gate propios. Comparte el estado y el
registro causal del agente; no crea otro bus cognitivo. Su arbitraje con una
intención de vuelo debe estar fijado antes del banco.

GEN-1f sólo demuestra la herencia de un hiperparámetro de calibración
sensorimotora. No demuestra confianza social, herencia creciente, navegación,
un sesgo semántico ni conocimiento de objetos.

## 8. Métricas y controles comunes

Restricciones duras observadas dentro del dominio publicado:

```text
false_facts                 == 0
imagined_cam_writes         == 0
oracle_leaks                == 0
gate_bypasses               == 0
PX4_failsafe_bypasses       == 0
unsafe_setpoints_accepted   == 0
```

Después se comparan por mundo, condición y semilla:

- metas completadas y tiempo;
- recomposiciones válidas tras fallar el primer plan;
- colisiones, distancia mínima y acciones bloqueadas;
- error y antigüedad de creencias;
- energía total, reserva al aterrizar y abortos correctos/incorrectos;
- intervenciones y solicitudes al operador;
- candidatos, profundidad real y latencia P50/P95/P99;
- uso de CPU, memoria y, cuando haya instrumento, energía de cómputo;
- predicción anterior, evidencia posterior y eslabón actualizado.

Una corrida visible ilustra; el certificado usa semillas reservadas e
intervalos. El sistema completo puede perder velocidad o slalom y cerrar la
hipótesis si cumple las restricciones y mejora las métricas preregistradas.

## 9. Plantilla obligatoria por fase

Antes de implementar cada slice se congela:

```text
pregunta única
invariantes heredados
entrada realmente disponible al agente
variable manipulada
control causal y oracle, si existe
métricas, denominadores e intervalos
seeds de desarrollo, validación y confirmación
criterios verde y rojo
mutantes obligatorios
artefacto JSON, trazas y hashes
```

El vídeo y la GUI nunca sustituyen esos artefactos.
