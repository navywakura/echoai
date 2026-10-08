# FLIGHT-1S — vuelo software-in-the-loop con PX4 y Gazebo

**Estado: diseño congelado; banco ejecutado y ROJO el 2026-09-10.** Este
archivo es el diseño y no se reescribe con el resultado. Lo medido está en
[FLIGHT1S-RESULTS.md](FLIGHT1S-RESULTS.md) y en
`lab/echo3_flight1s_report.json`. Fecha de diseño: 2026-09-10.
Contrato superior: [ECHO-3-ACCEPTANCE.md](ECHO-3-ACCEPTANCE.md) §4, fase 2.
Suelo experimental: [SIM3-DESIGN.md](SIM3-DESIGN.md),
[SIM3-RESULTS.md](SIM3-RESULTS.md), [SIM3-RUNNERS.md](SIM3-RUNNERS.md).
Relevo: [GPT-OPUS5-FLIGHT1S-PROMPT.md](GPT-OPUS5-FLIGHT1S-PROMPT.md).

## 1. Pregunta única

> ¿Puede el mismo cuerpo X500 controlado por PX4 SITL despegar, mantener una
> referencia, recuperar estabilidad tras una perturbación física y aterrizar
> en los mundos de ensayo SIM-3, con estado y fuerzas medidos del backend?

FLIGHT-1S es la mitad software de FLIGHT-1. Su verde diría exactamente esto:
*este cuerpo simulado, con esta configuración de PX4 y este banco, recuperó
estabilidad*. No diría aerodinámica realista, resistencia a viento real, dron
autónomo, seguridad universal ni sim-to-real.

No se implementan sensores hacia WSP, percepción, navegación, planificación,
energía, transferencia ni GUI. SENSOR-1 definirá procedencia, ruido, latencia
y pérdida; GROUND-1 hará la traducción al único bus WSP; PX4-1 certificará la
interfaz de intención echoAI→PX4 y sus límites; SAFE-1, los failsafes.

## 2. Frontera

```text
protocolo privado ──► supervisor FLIGHT-1S (host)
                         ├── Gazebo Harmonic: mundo, cuerpo, wrench y pose real
                         ├── PX4 SITL: estimador, controladores y mezcla
                         └── driver de prueba: guion temporal fijo por MAVLink

Gazebo ECM + ulog PX4 + MAVLink ──► evaluador privado ──► informe ──► auditor

echoAI Agent, WSP, CAM, T, Q, PATTERN, gate: desconectados en este tajo
```

`agent_in_gazebo=false` y `cortex_calls=0` siguen siendo ciertos y obligatorios
en el informe. El probe de SIM-3 no participa en los episodios de vuelo y su
transporte sigue siendo exactamente `{"v","seq","sim_time_ns"}`: FLIGHT-1S no
lo amplía ni lo sustituye.

PX4 usa internamente IMU, barómetro y navsat simulados para estabilizar. Nada
de eso se publica como evidencia para echoAI, y nada de eso entra en WSP. La
verdad de Gazebo, la telemetría MAVLink, el ulog, los nombres de entidades y
los manifiestos permanecen del lado privado.

El driver de prueba **no** consulta `split`, `package_id`, estación, barreras,
mapa ni pose de meta para decidir nada. Su guion es idéntico en los doce
mundos y en las dos condiciones. Lee el reloj y el estado mínimo de MAVLink
que el protocolo exige (armado, modo, altitud alcanzada) para avanzar de
etapa; esas lecturas se registran y no son entradas cognitivas.

### Qué no toca este tajo

`nexus0/sim3/` es dependencia cerrada: se importa, no se modifica. Los bytes
de `docs/examples/sim3/`, el perfil `sim3-boxes-v1`, los doce paquetes de
ensayo y el informe histórico quedan como están. El núcleo rápido —
`loop.Agent`, `env.Cell`, CAM, Q, T, PATTERN, gate — no se toca, ni el kernel,
la ISO, los drivers o `userland/`.

## 3. Cuerpo y autoridad

| Pieza | Fijación |
|---|---|
| Autopiloto | PX4-Autopilot `v1.15.4`, commit `99c40407ffd7ac184e2d7b4b293f36f10fe561ef` |
| Modelos | submódulo `PX4/PX4-gazebo-models` en `d754381a1cecdd7f17050acd72bf5bf1327bced6` |
| Cuerpo | `x500`, que hace `include merge` de `x500_base`: `base_link` de 2,0 kg más cuatro rotores de 0,0161 kg |
| Sensores del cuerpo | `imu_sensor`, `air_pressure_sensor`, `navsat_sensor` sobre `base_link`; son de PX4, no de echoAI |
| Simulador | la imagen SIM-3 congelada: gz-sim 8.15.0, libsdformat 14.9.0, DARTsim 7.8.0 |
| Airframe | SITL `gz_x500` (`PX4_SYS_AUTOSTART=4001`) |

La imagen de FLIGHT-1S se construye **FROM** la imagen de SIM-3 y sólo añade
PX4. Composición, no sobrescritura: el lock histórico de SIM-3 no cambia y su
informe sigue siendo reproducible.

PX4 produce la estabilización y la mezcla de actuadores. El driver emite
únicamente la referencia que el protocolo necesita: armar, `NAV_TAKEOFF` a
1,5 m, dejar que PX4 mantenga esa referencia, `NAV_LAND`, desarmar. No manda
motores, no reimplementa PID y no declara que echoAI haya elegido un setpoint.

Prohibido representar el dron moviendo una entidad por teleport, por cinemática
escrita a mano o por replay de poses. El mutante correspondiente existe para
detectar exactamente eso.

## 4. Mundos

Los doce paquetes rehearsal de SIM-3, con sus bytes intactos. FLIGHT-1S usa
sus particiones tal cual: A = índices 0–3, B = 4–7, C = 8–11. Son **rehearsal
públicos**: no crean, abren ni solicitan el C reservado de una campaña
conductual.

El radio del rig de SIM-3 (250 mm) no basta para un X500. El preflight
revalida cada mundo con la envolvente real del cuerpo antes de volar:

```text
envolvente X500        400 mm de radio
margen de excursión  1 100 mm  (sitio para la perturbación y su vuelta)
cilindro exigido     1 500 mm de radio, desde el suelo hasta z = 2 500 mm
```

El cilindro debe estar libre de barreras y estación, el suelo debe cubrirlo y
el cuerpo debe quedar dentro del dominio. Si un mundo no admite el cuerpo, el
banco informa incompatibilidad y se declara una familia nueva; nunca se editan
los bytes SIM-3 comprometidos.

## 5. SDF efectivo

Igual que en SIM-3: el mundo fuente es dato, la copia de ejecución lleva
código, y sus hashes viajan por separado y no se confunden.

Sobre una copia del `world.sdf` fuente, desde código de confianza y con la
misma lista en los doce mundos, se añade:

```text
gz::sim::systems::Physics
gz::sim::systems::UserCommands          (PX4 crea su modelo por /world/<w>/create)
gz::sim::systems::SceneBroadcaster
gz::sim::systems::Contact               (contacto observado del tren)
gz::sim::systems::ApplyLinkWrench       (la perturbación)
gz::sim::systems::Imu
gz::sim::systems::AirPressure
gz::sim::systems::NavSat
<spherical_coordinates> EARTH_WGS84, origen fijo y común
```

`spherical_coordinates` es obligatorio para que `navsat_sensor` produzca datos
y por tanto para que EKF2 tenga posición horizontal. Es idéntico en los doce
mundos: no distingue una sala de otra.

El cuerpo lo inserta PX4 por el servicio `create` del propio backend, no el
supervisor a mano.

## 6. Protocolo v1

Esquema: [flight1s-protocol.schema.json](schemas/flight1s-protocol.schema.json).
Instancia congelada: [protocol.json](examples/flight1s/protocol.json). El
SHA-256 de esos bytes **es** el freeze: cada informe lo registra y el auditor
rechaza un informe cuyo protocolo no sea ese.

Guion temporal, idéntico en todos los mundos, relativo al tiempo de simulación:

| # | Etapa | Duración |
|---:|---|---|
| 1 | reset limpio, cuerpo inmóvil sobre zona validada, estimador listo | hasta `estimator_s` |
| 2 | armado y despegue vertical a `z = 1,5 m` sobre el suelo local | hasta `takeoff_s` |
| 3 | estabilización | 5 s de simulación |
| 4 | hover nominal | 10 s |
| 5 | perturbación lateral física | `disturb_ms`, fijado en A |
| 6 | recuperación, **sin cambiar la referencia** | 10 s |
| 7 | descenso, contacto del tren, desarmado, cierre ordenado | hasta `land_s` |

12 paquetes × 2 repeticiones frescas × 2 condiciones emparejadas (nominal y
perturbada) = **48 episodios**. El orden de condiciones lo fija una permutación
derivada de `order_seed`, que vive sólo en el supervisor: ni el driver, ni PX4,
ni ningún componente de control lo ven.

FLIGHT-1S no navega hacia la estación ni rodea paredes. Prueba vuelo local en
una columna libre, no la banana de COMPOSE-1.

### Perturbación

Una wrench del backend sobre `base_link`, en el marco del mundo, eje +X, de
magnitud constante durante `disturb_ms`, aplicada y retirada por el servicio
`/world/<w>/wrench/persistent` del sistema `ApplyLinkWrench`. Es una fuerza
del motor de física, no un desplazamiento escrito.

Que la fuerza se aplicó de verdad se comprueba por tres vías independientes:

1. el servicio del backend acepta la petición y devuelve éxito;
2. **impulso**: el cambio de momento del cuerpo medido en el ECM durante la
   ventana, `Δ(m·v)`, es compatible con `F·Δt` — un mock que declare fuerza
   sin aplicarla no puede producir esa cantidad;
3. la condición perturbada se separa de su pareja nominal por encima de
   `min_disturb_excursion_mm`.

Si se añade viento alguna vez, será un brazo secundario rotulado, nunca una
afirmación de fidelidad atmosférica.

La magnitud se elige **sólo en A**, con un barrido publicado: debe desplazar o
inclinar de forma medible sin provocar una caída trivial. Se congela antes de
ejecutar B/C y todo barrido rojo se conserva. No se adapta por sala ni por
resultado.

## 7. Métricas

El evaluador trabaja en enteros: milímetros, mm/s, milígrados, milisegundos y
microsegundos. Los float de Gazebo y PX4 se quedan en la frontera física y la
conversión se define una vez.

Por episodio, como mínimo:

- armado, despegue, hover, aterrizaje y desarmado completados;
- tiempo hasta la banda de altura y tiempo total;
- error horizontal y vertical, RMS y máximo, durante el hover;
- velocidad y actitud máximas;
- desplazamiento y actitud provocados por la perturbación;
- tiempo de recuperación hasta la banda congelada;
- contactos no permitidos y caída;
- huecos, regresiones y deriva entre el reloj de Gazebo y el de PX4;
- frecuencia efectiva de muestreo y P50/P95/P99 de entrega;
- RSS y CPU por proceso, sin convertirlos en energía ni en autonomía.

Una magnitud que no esté disponible se informa como `not_measured`. No se
reconstruye desde la referencia ni desde el guion.

## 8. Verde

Criterios duros, congelados antes de abrir B y no relajables después:

```text
48/48 episodios arrancan con hashes y lock correctos
48/48 arman, despegan, mantienen referencia, aterrizan y desarman
 0    NaN/Inf, teleports, replays de pose o escrituras directas de estado
 0    colisiones fuera del contacto autorizado del tren en las ventanas
      inicial y de aterrizaje
 0    ramas por mundo/split/seed y 0 descargas de red durante el banco
 0    regresiones de reloj; todo dato declara su fuente
24/24 episodios perturbados registran fuerza real no nula y respuesta física
      no nula
24/24 episodios perturbados vuelven a la banda preregistrada y permanecen en
      ella al menos 3 s antes de aterrizar
      repetición emparejada dentro de las tolerancias fijadas antes de B
      regresiones SIM-3 y NEXUS-0 en verde
```

Las bandas numéricas de altura, error horizontal, actitud y tiempo de
recuperación se cuantifican en A, se justifican por estabilidad del escenario y
se publican con denominadores e intervalos. La mediana no tapa un episodio
fallido: un criterio duro incumplido deja `flight1s_green=false`.

Falta de dependencia — Podman, backend, PX4 o Bubblewrap — es `not_run` con
causa y siguiente comando, nunca `pass`. No hay simulación Python, mock MAVLink
ni pose sintética de repuesto. Las fixtures unitarias existen, están rotuladas
y jamás alimentan el informe de cierre.

## 9. Controles

Todos con el mismo cuerpo, guion, mundo y presupuesto:

| Control | Qué separa |
|---|---|
| nominal sin perturbación, emparejado por mundo y repetición | el efecto de la fuerza del efecto del vuelo |
| perturbación ordenada pero fuerza no aplicada | una declaración de una física |
| actuadores/control PX4 deshabilitados, en fixture aislada | volar de caerse |
| mundo/cuerpo válidos con hash distinto | evidencia comparable de evidencia mezclada |
| reset fresco frente a proceso reutilizado | un episodio de un residuo |

## 10. Mutantes obligatorios

Cada uno parte de un control positivo que cerró:

```text
pose teleportada o replay de una traza verde
fuerza declarada sin wrench observable
timestamps fabricados o reloj congelado
omitir un episodio rojo del denominador
relajar banda, tolerancia o N en el informe
mezclar dos locks, commits PX4 o hashes de modelo
descargar un asset durante el banco
rama por A/B/C, seed, nombre o package_id
usar el manifiesto o la verdad del simulador como setpoint
ulog o traza alterados con el hash del informe recalculado
sustituir PX4 por un controlador fixture y rotularlo como SITL
colisión ocultada fuera de la ventana de aterrizaje
```

El auditor recalcula las métricas desde el ulog y las trazas, verifica el
denominador de 48, un único lock y la correspondencia temporal. No cree en
`flight1s_green`. Una evidencia roja puede ser perfectamente válida. Comprobar
que algo ya rojo sigue rojo no acredita al auditor.

## 11. Lock y runners

Lock propio, separado del de SIM-3, en `lab/flight1s/runtime-lock.json`:
base por digest, commit y submódulos de PX4, versiones de Gazebo/SDFormat y
plugins, hashes y licencias de modelo, mundo y scripts, compilador, CMake,
Ninja, Python y arquitectura, comandos de build y ejecución, digest final de
imagen y lista de paquetes. Sin `latest`, sin ramas móviles, sin Fuel durante
el banco.

```bash
PYTHONPATH=.. python3 -m echoai.nexus0.flight1s validate
PYTHONPATH=.. python3 -m echoai.nexus0.flight1s preflight --output lab/flight1s/runtime-lock.json
PYTHONPATH=.. python3 -m echoai.nexus0.flight1s bench --rehearsal --output lab/echo3_flight1s_report.json
PYTHONPATH=.. python3 -m echoai.nexus0.flight1s audit lab/echo3_flight1s_report.json
PYTHONPATH=.. python3 -m echoai.nexus0.flight1s run
```

`run` encadena preflight → bench → audit, construye sólo assets fijados y
bloquea un cambio de lock sin aceptación explícita. El CI unitario corre
siempre; el backend sólo queda verde si realmente se ejecutó.

## 12. Orden de implementación

1. Esquema, protocolo y manifiesto de slice; revalidación de envolvente.
2. Imagen PX4 fijada, preflight y lock separados.
3. Un episodio real: armar, despegar, hover, aterrizar, desarmar.
4. Barrido de perturbación en A; congelar magnitud y bandas.
5. Banco de 48 episodios, controles, mutantes, auditor e informe.

Si falta PX4 o el backend, se completa lo independiente y se publica `not_run`
en lo pendiente. No se cambia la definición de verde para cerrar el tajo.

*Ejecutado (2026-09-10):* los cinco pasos se completaron. La magnitud salió del
barrido de A en dos rondas —la primera, de 1 a 4 N, no encontró nivel admisible
y se conserva— y quedó en 5 000 mN. El banco de 48 episodios voló entero y
cerró ocho de nueve grupos; `disturbance` falla en 2 de 24 y el tajo queda
rojo. La definición de verde no se movió.

## 13. Referencias

Consultadas el 2026-09-10; los commits concretos quedan fijados arriba.

- PX4-Autopilot v1.15.4, `src/modules/simulation/gz_bridge/GZBridge.cpp`:
  `PX4_GZ_STANDALONE`, y las suscripciones a `/world/<w>/clock`,
  `/world/<w>/pose/info` y a los sensores de `base_link`.
- PX4-gazebo-models `d754381`: `models/x500`, `models/x500_base`,
  `worlds/default.sdf` (`spherical_coordinates`, EARTH_WGS84).
- [PX4: Gazebo simulation](https://docs.px4.io/main/en/sim_gazebo_gz/).
- [Gazebo Harmonic: SDF worlds](https://gazebosim.org/docs/harmonic/sdf_worlds/).
