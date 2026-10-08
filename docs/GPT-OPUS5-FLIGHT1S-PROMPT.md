# Prompt para Claude Opus 5 — FLIGHT-1S

**Tajo:** FLIGHT-1S, vuelo exclusivamente software con PX4 SITL y Gazebo.  
**Estado inicial:** SIM-3 cerrado y verde bajo la corrida vigente documentada
en [SIM3-RESULTS.md](SIM3-RESULTS.md).  
**Hardware:** ausente. No hay AKD1000 ni AKD1500 en el laboratorio.  
**Resultado permitido:** dinámica de un cuerpo simulado medida. No percepción
de echoAI, navegación autónoma, transferencia ni seguridad física.

Copia desde aquí en Claude Code, ejecutándolo desde
`/home/roger/REALRXOS/RXos/echoai`.

---

Implementa y cierra **FLIGHT-1S** con banco reproducible. Tu pregunta única es:

> ¿Puede el mismo cuerpo X500 controlado por PX4 SITL despegar, mantener una
> referencia, recuperar estabilidad tras una perturbación física y aterrizar
> en los mundos de ensayo SIM-3, con estado y fuerzas medidos del backend?

FLIGHT-1S es la parte software de FLIGHT-1. No la conviertas en SENSOR-1,
GROUND-1 o PX4-1. PX4 usa internamente los sensores simulados que necesita para
estabilizar; ninguno se publica aún como evidencia para echoAI. El Agent no
entra en Gazebo y `agent_in_gazebo=false` continúa siendo verdad.

## Lectura obligatoria

Lee enteros y en este orden:

1. `AGENTS.md` y `CLAUDE.md`.
2. `docs/05-NEXUS-0-SPEC.md` y `docs/02-INVARIANTS.md`.
3. `docs/ECHO-3-ACCEPTANCE.md`.
4. `docs/SIM3-DESIGN.md`, `docs/SIM3-RESULTS.md` y
   `docs/SIM3-RUNNERS.md`.
5. `docs/examples/echo3-slices/sim3.json` y los esquemas `echo3-slice`,
   `sim3-campaign` y `sim3-world-family`.
6. Todo `nexus0/sim3/` y `tests/test_sim3*.py` antes de reutilizar interfaces.

Consulta únicamente documentación oficial de PX4, Gazebo y SDFormat para
elegir una combinación compatible. Registra URL y fecha. No cites una guía
como prueba de que el banco local corrió.

## Primero congela el diseño

Antes del código, crea:

- `docs/FLIGHT1S-DESIGN.md`;
- `docs/schemas/flight1s-protocol.schema.json`;
- `docs/examples/flight1s/protocol.json`;
- `docs/examples/echo3-slices/flight1s.json`, válido contra
  `echo3-slice.schema.json`;
- un lock separado de dependencias y assets de vuelo.

El diseño debe fijar antes de B/C: cuerpo, masa/configuración realmente usada,
PX4 commit o release exacto, modelo Gazebo y hashes, backend de física,
frecuencias, tiempos de cada etapa, perturbación, número de episodios, métricas,
criterios, controles y mutantes. Sin `latest`, ramas móviles, Fuel durante el
banco ni descarga silenciosa.

Puedes usar A para depuración. Una vez observado B, cualquier ajuste de código,
PID, duración, fuerza o umbral consume B para esa revisión y exige un nuevo
freeze. FLIGHT-1S usa únicamente A/B/C **rehearsal** públicos de SIM-3; no crea,
abre ni solicita el C reservado de una campaña conductual.

## Frontera arquitectónica

```text
protocolo privado ──► supervisor FLIGHT-1S
                         ├── Gazebo: mundo, cuerpo, fuerza y pose real
                         ├── PX4 SITL: estimador y controladores de vuelo
                         └── driver de prueba: referencia temporal fija

Gazebo/PX4 logs ──► evaluador privado ──► informe/auditor

echoAI Agent, WSP, CAM, T, Q, PATTERN, gate: desconectados en este slice
```

La secuencia del driver es igual en todos los mundos y seeds. No consulta
`split`, `package_id`, estación, barreras, mapa ni pose de la meta para decidir.
Puede leer el reloj PX4/Gazebo y el estado mínimo necesario para completar el
protocolo de prueba; esas lecturas se registran y no son entradas cognitivas.

La verdad de Gazebo, telemetría PX4, ulog, nombres de entidades y manifiestos
permanecen privados. El probe SIM-3 conserva exactamente
`{"v","seq","sim_time_ns"}`. No amplíes ese transporte. No conviertas posición
ground-truth, GPS o IMU en WSP. SENSOR-1 diseñará procedencia, ruido, latencia y
pérdida; GROUND-1 hará la traducción hacia el único bus WSP.

No toques el núcleo rápido, `loop.Agent`, `env.Cell`, CAM/Q/T/PATTERN, gate,
GUI, kernel, ISO, drivers ni userland. Implementa preferentemente en
`nexus0/flight1s/`, tests en `tests/test_flight1s*.py`, docs y `lab/`.
Trata `nexus0/sim3/` como dependencia cerrada. Si encuentras un defecto real,
demuéstralo con un test mínimo y documenta la incompatibilidad antes de
cambiar SIM-3; no reescribas sus resultados históricos.

## Cuerpo y autoridad

Usa un X500 de la integración oficial PX4/Gazebo o una copia vendorizada
idéntica cuyos assets y licencia queden fijados por hash. Documenta exactamente
qué modelo se ejecutó. Prohibido representar un dron moviendo una entidad por
teleport, cinemática escrita a mano o replay de poses.

PX4 debe producir la estabilización y la mezcla de actuadores. El driver de
prueba sólo emite la referencia de vuelo necesaria para este protocolo. No
manda motores directamente, no reimplementa PID y no declara que echoAI haya
elegido un setpoint. La interfaz causal de intención echoAI→PX4 y los failsafes
son objeto de PX4-1/SAFE-1.

Registra al menos:

- referencia solicitada y timestamp;
- estado de armado y modo PX4;
- pose, velocidad lineal/angular y actitud del vehículo;
- comandos/estado de actuadores disponibles;
- perturbación solicitada y fuerza realmente aplicada por el backend;
- contactos, reloj Gazebo, reloj PX4 y relación temporal;
- nacimiento y terminación de todos los procesos.

Si una magnitud no está disponible, el informe dice `not_measured`; no la
reconstruyas desde la referencia ni desde el guion.

## Protocolo mínimo v1

El mismo guion temporal, relativo al tiempo de simulación, para cada episodio:

1. Reset limpio y vehículo inmóvil sobre una zona de spawn validada para su
   envolvente real; estimador listo.
2. Armado y despegue vertical hasta `z=1.5 m` sobre el suelo local.
3. Estabilización durante 5 s de simulación.
4. Hover nominal durante 10 s.
5. Perturbación lateral física durante un intervalo fijado en el protocolo.
   Usa una wrench/fuerza del backend como prueba primaria reproducible. Si
   añades viento, es un brazo secundario rotulado y no una afirmación de
   fidelidad atmosférica.
6. Recuperación durante 10 s sin cambiar la referencia.
7. Descenso, contacto de tren con suelo, desarmado y cierre ordenado.

La intensidad de perturbación se selecciona sólo en A mediante un barrido
publicado: debe desplazar o inclinar mediblemente el control perturbado sin
provocar una caída trivial. Congela el valor antes de ejecutar B/C y conserva
todo barrido rojo. No adaptes la fuerza por sala o resultado.

Ejecuta los 12 paquetes rehearsal, dos repeticiones frescas por paquete, en dos
condiciones emparejadas: nominal y perturbada. Total mínimo: 48 episodios de
vuelo. Ordena condiciones mediante una permutación fijada por seed para evitar
sesgo térmico/temporal; la seed sólo vive en el supervisor y el orden no llega
a ningún componente de control.

No navegues hacia la estación ni alrededor de paredes. FLIGHT-1S prueba vuelo
local en una columna libre, no resolución de la banana. Revalida cada mundo
con la envolvente del X500; el antiguo radio del rig SIM-3 no basta. Si un
mundo no admite el cuerpo, informa incompatibilidad del banco y crea una
versión declarativa nueva, sin editar los bytes SIM-3 comprometidos.

## Métricas y verde

Usa enteros en mm, mm/s, miligrados, milisegundos y microsegundos en el
evaluador siempre que sea viable. Los float de Gazebo/PX4 se quedan en la
frontera física y las conversiones se definen una vez.

Por episodio mide como mínimo:

- armado, despegue, hover, aterrizaje y desarmado completados;
- tiempo hasta banda de altura y tiempo total;
- error horizontal/vertical RMS y máximo durante hover;
- velocidad y actitud máximas;
- desplazamiento/actitud provocados por la perturbación;
- tiempo de recuperación a la banda congelada;
- contactos no permitidos y caída;
- gaps, regresiones y deriva entre relojes;
- frecuencia efectiva de control y P50/P95/P99 de entrega;
- RSS y CPU por proceso; sin convertirlos en energía o autonomía.

Criterios duros iniciales, que no puedes relajar tras abrir B:

- 48/48 episodios arrancan con hashes y lock correctos;
- 48/48 arman, despegan, mantienen referencia, aterrizan y desarman;
- 0 NaN/Inf, teleports, pose replays o escrituras directas de estado;
- 0 colisiones, salvo contacto autorizado del tren con el suelo durante las
  ventanas inicial y de aterrizaje;
- 0 ramas por mundo/split/seed y 0 descargas de red durante el banco;
- 0 regresiones de reloj y todos los datos declaran fuente;
- el brazo perturbado registra fuerza real no nula y respuesta física no nula;
- 24/24 episodios perturbados vuelven a una banda preregistrada y permanecen
  en ella al menos 3 s antes de aterrizar;
- repetición emparejada dentro de tolerancias fijadas antes de B;
- regresiones SIM-3 y NEXUS-0 verdes.

En A cuantifica y congela bandas numéricas de altura, error horizontal,
actitud y tiempo de recuperación. Justifica esas bandas por estabilidad y
seguridad del escenario, publica denominadores e intervalos y no uses la media
para ocultar un episodio fallido. Un criterio duro incumplido deja
`flight1s_green=false` aunque la mediana sea buena.

El resultado sólo puede decir: «el cuerpo simulado y esta configuración PX4
recuperaron estabilidad en este banco». No digas aerodinámica realista,
resistencia a viento real, dron autónomo, seguridad universal o sim-to-real.

## Controles y mutantes

Controles obligatorios:

- nominal sin perturbación, emparejado por mundo y repetición;
- perturbación ordenada pero fuerza no aplicada: el evaluador debe detectarla;
- actuadores/control PX4 deshabilitados en fixture aislada: el cuerpo no puede
  seguir la referencia como si volara;
- mundo/cuerpo válidos con hash distinto: preflight debe rechazar la mezcla;
- reset fresco frente a proceso/estado indebidamente reutilizado.

Mutantes obligatorios, cada uno desde un control positivo:

- pose teleportada o replay de una traza verde;
- fuerza declarada sin wrench observable;
- timestamps fabricados o reloj congelado;
- omitir un episodio rojo del denominador;
- relajar banda/tolerancia/N en el informe;
- mezclar dos locks, PX4 commits o hashes de modelo;
- descargar un asset durante banco;
- rama por A/B/C, seed, nombre o `package_id`;
- usar el manifiesto/ground-truth como setpoint;
- ulog o traza alterados con el hash del informe recalculado;
- sustituir PX4 por un controlador fixture y rotularlo como SITL;
- colisión ocultada fuera de la ventana de aterrizaje.

El auditor recalcula métricas desde ulog y trazas independientes, verifica el
denominador de 48, un único lock y las correspondencias temporales. No confía
en `flight1s_green`. Una evidencia roja puede ser válida. Los mutantes se
prueban contra una evidencia positiva; comprobar que algo ya rojo sigue rojo
no acredita al auditor.

## Dependencias y runners

Crea una imagen/entorno separado y fijado para PX4 SITL si ampliar la imagen
SIM-3 invalidaría su lock. Prefiere composición explícita a sobrescribir el
runtime histórico. Registra:

- base por digest;
- commit/tag exacto y submódulos PX4;
- versiones Gazebo/SDFormat y plugins;
- hashes/licencias de modelo, mundo y scripts;
- compilador, CMake/Ninja, Python y arquitectura;
- comandos de build y ejecución;
- digest final de imagen y lista de paquetes instalados.

Sin Podman, backend, PX4 o Bubblewrap efectivos: grupo `not_run`, causa y
siguiente comando; `flight1s_green=false`. No uses una simulación Python,
mock MAVLink o pose sintética como fallback. Unit tests pueden usar fixtures si
están rotuladas y jamás alimentan el informe de cierre.

Expón una CLI coherente:

```bash
PYTHONPATH=.. python3 -m echoai.nexus0.flight1s validate
PYTHONPATH=.. python3 -m echoai.nexus0.flight1s preflight --output lab/flight1s/runtime-lock.json
PYTHONPATH=.. python3 -m echoai.nexus0.flight1s bench --rehearsal --output lab/echo3_flight1s_report.json
PYTHONPATH=.. python3 -m echoai.nexus0.flight1s audit lab/echo3_flight1s_report.json
PYTHONPATH=.. python3 -m echoai.nexus0.flight1s run
```

`run` hace preflight→bench→audit, construye sólo assets fijados y bloquea un
cambio de lock. El CI unitario siempre corre; el backend sólo queda verde si
realmente se ejecuta. Conserva informes anteriores al cambiar protocolo.

## Entrega

Entrega:

1. diseño y protocolo congelados;
2. implementación y tests;
3. lock y hashes reales;
4. informe, trazas/ulog y auditoría;
5. resultados nominales y perturbados por episodio;
6. tabla de controles y mutantes con causa observada;
7. `FLIGHT1S-RESULTS.md` con comandos y salidas reales;
8. actualización mínima de `NOW.md` y `ROADMAP.md` según lo medido.

No hagas commit, push, deploy ni instales globalmente sin autorización ya
presente. No borres ni reetiquetes SIM-3. Si el banco sale rojo, conserva el
rojo y explica qué variable concreta impide cerrar.

Antes de terminar responde por escrito:

- ¿PX4 estabilizó el cuerpo o el arnés movió la pose?
- ¿la perturbación se aplicó físicamente y se observó por una fuente distinta?
- ¿el mismo binario/guion corrió en todos los mundos?
- ¿algún dato privado llegó al probe o a echoAI?
- ¿se mezclaron locks, modelos o commits?
- ¿se cambió un umbral después de B?
- ¿se consumió un C reservado?
- ¿qué capacidad exacta queda demostrada y cuáles siguen pendientes?

No se promete verde. Se exige que cada verde pueda reconstruirse.
