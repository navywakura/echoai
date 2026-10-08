# Prompt para Claude Opus 5 — DRONE-3

Trabaja directamente en `/home/roger/REALRXOS/RXos/echoai` y lleva DRONE-3 tan
lejos como permita el hardware disponible. No te limites a proponer un plan:
inspecciona, fija el contrato prospectivo, implementa, prueba, ejecuta la
campaña SITL, audita sus artefactos y documenta el resultado. Si una ejecución
larga falla, diagnostica la causa, conserva la evidencia y continúa cuando sea
posible. No me devuelvas trabajo rutinario que puedas completar tú.

## Estado de partida que debes verificar

- Hoy es 2026-09-19. TRANSFER-3 está oficialmente verde mediante la campaña
  C1 v2: certificado `8c77aead…`, B `fac69205…`, C `5d4f58de…`, con cero
  pérdidas atribuibles. ECHO-3 está en 14/15 y sólo queda DRONE-3.
- El árbol contiene mucho trabajo válido aún no versionado. Antes de tocarlo,
  ejecuta `git status --short`, inventaría lo relevante y protege el estado.
  Está terminantemente prohibido usar `git clean`, `git reset`, `git checkout`
  sobre cambios ajenos, borrados masivos o formateo global. No pierdas ni
  reescribas artefactos históricos.
- No existe AKD1000 en el laboratorio. Tampoco hay ahora un dron físico,
  controlador, sensores ni jaula de vuelo disponibles. El AKD1500 M.2 futuro
  no sustituye esos elementos.
- Usa Python 3.14.6 y las versiones locales ya fijadas de PX4/Gazebo/Podman.
  Comprueba las versiones reales; no descargues ni actualices dependencias sin
  necesidad demostrada.

Lee primero, en este orden:

1. `CLAUDE.md`
2. `docs/05-NEXUS-0-SPEC.md`
3. `docs/NOW.md`
4. `docs/ROADMAP.md`, especialmente las líneas de ECHO-3 y DRONE-3
5. `docs/ECHO-3-ACCEPTANCE.md`
6. `docs/ECHO3-STATUS-20260917.md`, teniendo en cuenta que TRANSFER-3 ya lo
   supera y está verde
7. Los diseños y resultados vigentes de SIM-3, FLIGHT-1S v6, SENSOR-1S v3,
   GROUND-1 v2, DYNAMIC-1 v2, PATTERN-1R v4, FUSION-1, COMPOSE-1 v4,
   CAUSE-1, PX4-1, POWER-1, SAFE-1 v2, HOST-1 y TRANSFER-3 C1
8. `docs/POST-ECHO3-DRONE-METAVERSE.md`, únicamente para respetar la frontera:
   Blender, renderer avanzado, motor de videojuego, GUI final, órdenes libres,
   mundos ampliados y transferencia entre morfologías todavía no se
   implementan.

Confirma los certificados y límites vigentes antes de diseñar DRONE-3. Las
auditorías históricas deben seguir siendo verificables sin modificar sus locks,
semillas, trazas, certificados o fuentes congeladas.

## Pregunta única de DRONE-3

¿Puede el sistema integrado ejecutar de principio a fin una misión de estación
de carga bloqueada usando únicamente sensores públicos, WSP, memoria/evidencia,
composición, gates de energía y seguridad y objetivos acotados aceptados por
PX4, y producir una cadena causal reconstruible desde la percepción hasta la
consecuencia, sin mapas o recetas ocultas y sin saltarse los failsafes?

La unidad experimental debe ser una **misión continua real en SITL**, no una
concatenación de replays o resultados independientes. Despegue, percepción,
decisión, inspección/desvío, llegada o aborto correcto, retorno/aterrizaje y
desarme deben ocurrir dentro de la misma sesión PX4/Gazebo. No reinicies el
estado entre capacidades para simular integración.

## Trabajo obligatorio antes del primer examen reservado

Crea `docs/DRONE3-DESIGN.md` antes de abrir B. Debe fijar:

- la pregunta anterior y el alcance exacto;
- qué componente vigente aporta cada eslabón y qué adaptadores nuevos hacen
  falta;
- entradas realmente visibles al agente y verdad privada sólo para el juez;
- misión, condiciones, controles causales, oracle usado sólo como techo,
  unidades experimentales y denominadores;
- partición de desarrollo A, validación B y confirmación C con semillas nuevas;
- regla estricta de congelación: cualquier cambio tras mirar B consume B; B
  rojo impide abrir C;
- criterios cuantitativos verdes y rojos, intervalos y contraste si procede;
- mutantes, manipulaciones de trazas y manipulaciones del informe;
- inventario por hash, esquema de artefactos y auditoría en proceso nuevo;
- estados separados `drone3_sitl_green`, `drone3_hil_green`,
  `drone3_cage_green` y `drone3_green`.

No elijas umbrales después de mirar B/C. Dimensiona el banco con potencia o
justifica el carácter funcional de cada puerta. Si el diseño descubre que una
capacidad previa no puede integrarse limpiamente, mide y documenta el hueco en
A; no lo tapes con una rama por escenario.

## Implementación

Implementa la integración de forma opt-in en `nexus0/drone3/`, con pruebas en
`tests/test_drone3.py` y artefactos nuevos bajo `lab/drone3/`. Reutiliza los
módulos certificados mediante imports o adaptadores mínimos. No copies sus
núcleos, no alteres fuentes congeladas para que encajen y no conviertas
certificados parciales en flags decorativos.

La cadena mínima ejecutada debe ser:

```text
sensores simulados con fuente y tiempo
→ adaptación física y WSP de 16 bytes
→ evidencia/FUSION con calibración C1 aplicable
→ estado, predicción y composición de la siguiente acción
→ gate epistémico + gate energético + supervisor SAFE
→ gateway PX4 de objetivos acotados
→ ACK distinto de llegada
→ consecuencia física observada
→ atribución/actualización permitida y traza causal
→ nueva planificación, retorno o aterrizaje
```

Integra comportamientos reales, no sólo imports. Como mínimo:

- COMPOSE debe decidir la ruta sin nombre de mundo, mapa, seed, coordenada
  solución ni receta; publica la predicción antes de actuar y replantea tras
  contradicción.
- La calibración transferida de C1 debe llegar como sus dos enteros congelados,
  sin mapa, episodios ni Q; verifica su procedencia y hash. No reabras ni
  modifiques la campaña TRANSFER-3.
- POWER debe decidir continuar, volver o aterrizar con coste previsto, retorno,
  aterrizaje y reserva. No sustituyas esto por porcentaje fijo.
- SAFE debe mantener lease, frescura sensorial, vida del worker, autoridad,
  recinto y fallo enclavado. Tras veto no se emiten objetivos nuevos.
- PX4 conserva PID, estimación, motores, modos y failsafes. echoAI sólo emite
  intenciones u objetivos de alto nivel ya autorizados.
- La cadena causal debe distinguir intención, publicación de predicción,
  propuesta, decisión de cada gate, envío, ACK, confirmación de movimiento,
  observación posterior, atribución y actualización. Un ACK no demuestra
  llegada.
- HOST sólo participa si hay una condición preregistrada que requiera una
  fuente; su signo no se convierte en recompensa ni hecho. El arbitraje de
  comunicación nunca desplaza un veto o una intención de vuelo segura.
- DYNAMIC/PATTERN deben tener un papel medible si se declaran integrados. Haber
  importado sus paquetes o mostrar sus flags no cuenta como ejercitarlos.

Mantén los invariantes existentes:

- un único bus cognitivo WSP de 16 bytes;
- ningún segundo thought-bus;
- paso rápido entero y funcional con córtex apagado;
- ningún LLM escribe CAM, T, Q, hechos, setpoints aceptados o actuadores;
- rollouts e hipótesis no entran en CAM como hechos;
- verdad del simulador, mapa, nombre, hash y seed fuera del proceso agente;
- cero `false_facts`, `imagined_cam_writes`, `oracle_leaks`, `gate_bypasses`,
  `PX4_failsafe_bypasses` y `unsafe_setpoints_accepted`;
- PX4 mantiene siempre la última autoridad física.

## Banco y controles

Diseña en A una matriz pequeña pero causal y después congélala. B y C deben
usar mundos o geometrías y semillas frescas dentro del dominio declarado. Cada
etapa debe incluir al menos:

1. una misión accesible que exige inspección y desvío hasta la estación;
2. una misión que debe abortarse o volver por reserva insuficiente;
3. una contradicción sensorial o de transitabilidad que obliga a replanificar;
4. un fallo integrado preregistrado que SAFE contiene y deja a PX4 aterrizar
   mediante su mecanismo nativo, sin `NAV_LAND` externo posterior al veto.

Incluye controles con las mismas observaciones y presupuesto que permitan
atribuir cada afirmación. Como mínimo considera horizonte uno/reactivo,
porcentaje fijo de batería, enlace que confunde ACK con llegada y una ablación
de un gate. Los controles peligrosos son funcionales o de replay y nunca se
envían al vehículo. Usa un oracle sólo para el techo y el juez privado.

No exijas que ECHO gane velocidad si ésa no es la hipótesis. Sí exige que las
misiones factibles terminen, las inviables se abandonen correctamente, la
reserva se respete, los fallos se contengan y cada decisión pueda reconstruirse
desde evidencia. Publica por etapa n/N, misiones, abortos correctos e
incorrectos, colisiones, distancia mínima, reserva final, activaciones de
failsafe, error de objetivo/aterrizaje, latencias P50/P95/P99, uso de memoria,
órdenes bloqueadas y todos los denominadores. No cuentes frames, rayos o ticks
correlacionados como experimentos independientes.

La auditoría debe recomputar el veredicto desde trazas crudas y ULog, comprobar
cronología y hashes, rechazar omisiones/duplicados/corrupciones, ejecutar los
mutantes y reproducir el mismo certificado en un proceso nuevo. El vídeo o la
GUI sólo ilustran; nunca sustituyen JSON, JSONL, ULog y hashes.

## HIL, jaula y veredicto honesto

El contrato vigente de `docs/ECHO-3-ACCEPTANCE.md` exige SITL, HIL y jaula
física. En este laboratorio hoy falta el hardware necesario. Por tanto:

- completa ahora todo el cierre SITL que sea posible;
- crea `docs/DRONE3-HARDWARE-HANDOFF.md` con BOM y versiones mínimas, esquema
  de conexión, límites de recinto, checklist previo, parada de emergencia,
  instrumentación de batería, calibraciones, comandos exactos, criterios,
  artefactos esperados y procedimiento B/C que pueda ejecutar Roger cuando
  exista el hardware;
- no inventes telemetría HIL, consumo físico, sensores reales ni vuelos de
  jaula;
- aunque SITL quede verde, conserva `drone3_green=false`, ECHO-3 en 14/15 y
  DRONE-METAVERSE cerrado mientras `drone3_hil_green` y
  `drone3_cage_green` no sean verdaderos con evidencia real;
- si el PC ni siquiera permite una campaña SITL válida, entrega el bloqueo
  exacto con evidencia y no rebajes el contrato.

No pidas el secreto de TRANSFER-3 y no abras una nueva campaña sellada sin que
el diseño demuestre que es necesaria. No publiques ni envíes nada fuera del
equipo. No hagas commits ni pushes salvo instrucción expresa de Roger.

## Cierre y entrega

Ejecuta primero pruebas dirigidas y después la regresión necesaria. No vueles
B hasta que A, controles, mutantes, auditor y lock estén listos. Si B pasa,
abre C una sola vez. Ejecuta una segunda auditoría de sólo lectura en proceso
nuevo.

Entrega como mínimo:

- `docs/DRONE3-DESIGN.md` prospectivo;
- `nexus0/drone3/` y `tests/test_drone3.py`;
- `lab/drone3/lock.json`, trazas, ULog, resúmenes B/C, mutaciones y recibos;
- `lab/echo3_drone3_report.json` con flags separados de SITL/HIL/jaula/final;
- `docs/DRONE3-RESULTS.md`, con números, hashes, límites y reproducción;
- `docs/DRONE3-HARDWARE-HANDOFF.md`;
- actualización factual y coherente de `docs/NOW.md`, `docs/STATUS.md`,
  `docs/ROADMAP.md` y `docs/ECHO-3-ACCEPTANCE.md`, sin borrar historia.

Al terminar, responde con: veredicto exacto; pruebas y vuelos ejecutados;
hashes de lock, informe y certificado; auditoría independiente; archivos
cambiados; límites; y el siguiente paso físico concreto. No digas “DRONE-3
verde” ni abras DRONE-METAVERSE si sólo cerraste SITL.
