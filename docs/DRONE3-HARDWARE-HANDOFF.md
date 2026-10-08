# DRONE-3 — traspaso a hardware: HIL y jaula física

2026-09-19. Documento para Roger, para cuando el hardware exista. **Hoy no hay
controlador de vuelo, dron, sensores reales ni jaula en el laboratorio.** Nada
de lo que sigue está ejecutado: es el procedimiento y lo que hace falta.
`drone3_hil_green` y `drone3_cage_green` siguen en `false` hasta que haya
evidencia real. El SITL está en [DRONE3-RESULTS.md](DRONE3-RESULTS.md) y el
contrato en [DRONE3-DESIGN.md](DRONE3-DESIGN.md).

## 0. Lo que el SITL no traslada por sí solo

Antes de comprar, tres diferencias que obligan a trabajo nuevo; no se tapan:

1. **Escala del dominio.** El SITL usa celdas de 3 m y salas de 21 × 15 m. Las
   constantes de percepción (`CELL_MM=3000`, holgura 900 mm) están congeladas en
   COMPOSE-1. Una jaula doméstica no admite esa escala. Hace falta una versión
   con tamaño de celda declarado, por ejemplo 1 m, y validarla primero en SITL
   con semillas nuevas: *DRONE-3 SITL v2 a escala de jaula*. Sin eso, un vuelo en
   jaula no examina el mismo sistema.
2. **Sensores.** El agente espera un LiDAR 2D de 360°, cuatro vistas de
   profundidad y RGB con sellos de captura y entrega. Un kit real distinto exige
   SENSOR-1H y GROUND-1H: mismas preguntas que 1S con el sensor real.
3. **Batería.** En SITL la energía es carga simulada, porque PX4 publica −1 A.
   Con hardware, POWER debe usar `mC` desde un módulo de potencia con medida de
   corriente, recalibrado en A con recibos reales (POWER-1H).

Orden recomendado, ya fijado en el plan de hardware: FLIGHT-1H → SENSOR-1H →
PX4-1H → POWER-1H → DRONE-3H (HIL y después jaula).

## 1. Lista de materiales mínima

| Elemento | Mínimo | Por qué |
|---|---|---|
| Controlador de vuelo | clase Pixhawk FMUv6 con **PX4 v1.15.4**, la versión del SITL | el mismo firmware y failsafes; otra versión exige repetir PX4-1 |
| Estructura | Holybro X500 V2 o equivalente al modelo `x500` | el SITL y los recibos A usan ese cuerpo |
| Módulo de potencia | con medida de corriente y tensión (p. ej., PM02D digital) | POWER en `mC`; sin corriente, POWER se abstiene |
| Ordenador de a bordo | Linux ARM64/x86 con Python 3.12+, bubblewrap y MAVLink por serie | agente enjaulado + supervisor + gates; nunca en el FC |
| LiDAR 2D | 360°, ≥ 10 Hz, 0,3–30 m | contrato de SENSOR-1S |
| Profundidad + RGB | cobertura de las cuatro direcciones o protocolo declarado de guiñadas | contrato de COMPOSE-1; si cambia, SENSOR-1H |
| Emisora RC | con **interruptor de parada (kill)** mapeado y probado | parada de emergencia humana, fuera del software |
| Radio de telemetría | independiente del enlace de a bordo | observador pasivo del operador |
| Verdad de terreno | captura de movimiento o cámara cenital calibrada | el juez privado necesita la pose verdadera; el agente nunca la ve |
| Jaula | red cerrada; dimensiones ≥ dominio a escala + 1 m por lado; altura ≥ 3 m | recinto físico, además de la geocerca PX4 |
| Baterías | ≥ 3 packs iguales, cargador balanceador, bolsa ignífuga | recibos A y márgenes repetibles |

## 2. Conexión

```text
[sensores] ──USB/UART──> [ordenador de a bordo]
                           ├─ jaula bwrap: agente (WSP + predicción)
                           ├─ supervisor SAFE + gates epistémico/energético
                           └─ gateway de celdas ──MAVLink serie──> [FC PX4 v1.15.4]
                                                                   └─ ESC/motores (sólo PX4)
[RC con kill] ─────────────────────────────────────────────────────> [FC]
[telemetría operador] <── MAVLink sólo lectura ── [FC]
[mocap/cámara cenital] ──> juez privado (fuera del ordenador de a bordo)
```

En **HIL** el FC corre PX4 real y el simulador del PC le entrega sensores. Hay
que confirmar en la documentación de PX4 v1.15 qué simulador soporta HITL con
este firmware; en v1.15 la vía documentada no es Gazebo Harmonic. Si hace falta
otro simulador, es una versión nueva del banco: no se reutilizan resultados
SITL como HIL.

## 3. Límites de recinto y parámetros

- Geocerca PX4 (`GF_ACTION`, `GF_MAX_HOR_DIST`, `GF_MAX_VER_DIST`), estrictamente
  dentro de la jaula. La geocerca del gateway (`GEOFENCE_*` de
  `nexus0/drone3/contract.py`) se reescala en la versión a escala.
- `COM_DL_LOSS_T=5` y `NAV_DLL_ACT=3` (aterrizar), leídos de vuelta como en
  SITL. `COM_LOW_BAT_ACT`, `BAT_LOW_THR` y `BAT_CRIT_THR` sin tocar: son la
  última autoridad de PX4.
- Altura de misión dentro de la jaula con ≥ 0,5 m de margen al techo.
- Sin parámetros de motores, PID ni estimador tocados por el agente. El operador
  configura; el agente nunca.

## 4. Lista previa (cada vuelo, firmada en el registro)

1. Firmware PX4 v1.15.4 y hash del binario anotados; parámetros exportados.
2. Hélices, brazos, fijaciones y red revisados; nadie dentro de la jaula.
3. Batería cargada y equilibrada; tensión anotada; módulo de potencia leyendo
   corriente distinta de −1 en banco.
4. Kill de RC probado con motores desarmados (arma, kill, comprobar desarme).
5. Pérdida de enlace probada en banco: cortar latido → PX4 entra en failsafe.
6. Geocerca cargada y leída de vuelta.
7. Verdad de terreno grabando, con reloj sincronizado con el ordenador de a bordo.
8. `python3 -m unittest echoai.tests.test_drone3` verde en el ordenador de a bordo.

## 5. Parada de emergencia

Orden de autoridad: **humano con kill de RC > PX4 (failsafes) > supervisor SAFE
> agente**. El kill no depende de ningún software de echoAI. Tras un veto SAFE,
el operador no envía `NAV_LAND` salvo riesgo inmediato; si lo hace, el vuelo se
registra como **intervención humana** y no cuenta como contención nativa.

## 6. Calibraciones antes de A

- Sensores: intrínsecos y extrínsecos de cámaras y LiDAR respecto al cuerpo. La
  calibración C1 transferida es de un mundo discretizado; en hardware se mide
  la montura real y se declara.
- Batería: A de POWER-1H con recibos reales (≥ 8 por fase: paso de misión,
  paso de retorno y aterrizaje), `Model.fit` sin cambios.
- Retardo sensor → agente → gateway medido; el TTL de 250 ms debe caber con
  margen o el contrato a escala debe declararlo.

## 7. Comandos

Hoy existen los del SITL:

```sh
cd RXos/echoai
PYTHONPATH=.. python3 -m unittest echoai.tests.test_drone3 -q
PYTHONPATH=.. python3 -m echoai.nexus0.drone3.bench audit
```

Para hardware harán falta, **y no existen todavía**, un runner de a bordo que
sustituya `assets/runner.py`: MAVLink por serie en lugar de UDP en contenedor,
controladores reales en lugar de tópicos Gazebo y verdad de terreno externa en
lugar de `private.jsonl` del simulador. Su contrato se escribe antes de volar,
con las mismas trazas y el mismo auditor. Comandos previstos, a crear en
DRONE-3H:

```sh
PYTHONPATH=.. python3 -m echoai.nexus0.drone3h.bench a1      # A en jaula, recibos reales
PYTHONPATH=.. python3 -m echoai.nexus0.drone3h.bench freeze
PYTHONPATH=.. python3 -m echoai.nexus0.drone3h.bench validation
PYTHONPATH=.. python3 -m echoai.nexus0.drone3h.bench confirmation
PYTHONPATH=.. python3 -m echoai.nexus0.drone3h.bench audit
```

## 8. Criterios y artefactos

Los mismos del [contrato SITL](DRONE3-DESIGN.md#criterios), con:

- **HIL:** FC real, sensores simulados. Criterios de vuelo idénticos. Denominador
  propio. ULog del FC real.
- **Jaula:** además, verdad de terreno externa para el juez. **Cero contactos con
  la red.** Cualquier kill humano = vuelo rojo con causa registrada. Energía en
  `mC`, con la reserva calibrada en A de hardware.
- Artefactos por vuelo: traza del runner, diario del agente, ULog del FC, verdad
  de terreno, vídeo sólo ilustrativo, parámetros exportados, lista previa firmada.

## 9. Procedimiento B/C (para Roger)

1. Cerrar FLIGHT-1H, SENSOR-1H, PX4-1H y POWER-1H, cada uno con su contrato.
2. Escribir y aprobar el contrato DRONE-3H: escala, sensores, energía y juez.
3. A: vuelos de desarrollo y calibración; A2 entero en verde.
4. `freeze`: lock con código, firmware, parámetros, tabla POWER y salas.
5. B una sola vez. Si es rojo, se conserva y C no se abre.
6. C una sola vez con el mismo lock.
7. Auditoría en proceso nuevo; `drone3_hil_green` o `drone3_cage_green` sólo con
   esa evidencia.
8. `drone3_green` exige SITL, HIL y jaula verdes. Sólo entonces ECHO-3 pasa a
   15/15 y puede abrirse DRONE-METAVERSE.
