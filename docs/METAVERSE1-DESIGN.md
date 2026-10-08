# METAVERSE-1 — contrato de apertura

**Estado:** fase abierta el 20 de septiembre de 2026 por decisión de Roger.
**Tipo:** excepción de puerta. El roadmap pedía ECHO-3 completo y estamos en
14/15. Se abre igual, y esta excepción queda escrita, no implícita.
**Origen del diseño:** `POST-ECHO3-DRONE-METAVERSE.md` (9/09/2026), donde la
fase se llama **DRONE-METAVERSE**. Ese documento no se reescribe: manda él.

---

## 1. Qué se abre exactamente

METAVERSE-1 no es «hacer bonito el simulador». Es ampliar fidelidad, escala e
instrumentación del laboratorio ya cerrado, **sin tocar lo certificado**.

Ocho sub-fases, en el orden del documento de origen:

| Sub-fase | Qué amplía | Depende de |
|---|---|---|
| **META-WORLD-2** | escala y fidelidad visual del mundo | SIM-3, COMPOSE-1 |
| **FLIGHT-2** | dinámica de mayor fidelidad | FLIGHT-1S v6 |
| **SENSOR-2** | más sensores y condiciones | SENSOR-1S v3, GROUND-1 |
| **PX4-2** | extensión del control de vuelo | PX4-1, DRONE-3 |
| **COMMAND-1** | órdenes humanas verificadas | HOST-1, SAFE-1 |
| **TRANSFER-META-1** | escala y transferencia entre cuerpos | TRANSFER-3 |
| **GUI-METAVERSE-1** | visor, timeline, tutorial y replay | GUI-4 |
| **CHIMP-1** | herramienta con física y tarea compuesta | todas |

**Se empieza por META-WORLD-2.** El documento de origen lo dice literalmente:
«el primer trabajo será fijar el contrato de escala de META-WORLD-2 sin
reabrir ni contaminar los exámenes B/C ya publicados».

## 2. La excepción de puerta, dicha entera

ECHO-3 está en 14/15. Lo que falta de DRONE-3 es **físico**: HIL y jaula, que
necesitan hardware que no existe en el laboratorio.

Consecuencia que no se negocia: **METAVERSE-1 no puede cerrar DRONE-3 ni subir
ECHO-3 a 15/15.** Ningún resultado de esta fase cuenta como hardware. Trabajar
en simulación más rica mientras se espera la plataforma es razonable; declarar
por ello el hito cerrado, no.

Banderas que siguen en `false` pase lo que pase aquí:
`drone3_hil_green`, `drone3_cage_green`, `drone3_green`.

## 3. Invariantes heredados

Del documento de origen §7, vigentes sin cambios:

- Un solo WSP cognitivo de 16 bytes. No se crea un segundo thought-bus.
- El paso rápido sigue siendo entero y funciona sin LLM.
- El córtex propone; VERIFY y el gate verifican y vetan.
- Q/T/CAM no se escriben desde la GUI, el LLM, PX4 ni el renderer.
- El renderer muestra telemetría real o una reproducción marcada como tal.
- Los mundos se configuran fuera del núcleo y no contienen recetas de éxito.
- No se afirma aerodinámica, IMU, cámara ni hardware hasta que el backend
  correspondiente esté conectado y medido.
- AKD1500 M.2 sigue fuera de esta fase.

De GUI-4, que también aplican aquí:

- **Cero ficheros nuevos bajo `nexus0/`.** `safe1`, `power1`, `host1` y
  `cause1` sellan su inventario con `rglob('*.py')` sobre esa carpeta.
  METAVERSE-1 escribe en `echoai/metaverse1/`.
- Tres orígenes, nunca mezclados: `en vivo`, `banco reducido`,
  `evidencia sellada`.

## 4. Lo que no se toca

Contaminar un examen ya publicado es el riesgo principal de esta fase, porque
amplía mundos que ya sirvieron de banco. Reglas duras:

1. **No se reabren los exámenes B/C de ninguna fase cerrada.** Sus semillas,
   salas y geometrías quedan como están.
2. **No se reutiliza una geometría ya volada** para un banco nuevo. DRONE-3 ya
   pagó ese error una vez: el revisor encontró que la partición de validación
   incluía una geometría de los pilotos, y hubo que rehacerla.
3. **No se edita ningún fichero sellado.** Los 137 del `lock.json` de DRONE-3
   y los 69 de TRANSFER-3 son evidencia.
4. **El backend físico congelado no cambia** dentro de META-WORLD-2: subir
   detalle visual no puede alterar trayectorias, eventos ni puntuación.

Comprobación obligatoria al cerrar cada sub-fase: `px41`, `safe1_v2`,
`power1`, `host1`, `fusion1` y `compose1_v4` siguen reproduciendo su
certificado, y la suite sale verde.

## 5. Herramientas elegidas, con el motivo

Medido contra la máquina real el 20/09/2026: AMD Renoir integrada, Mesa
25.3.6, OpenGL 4.6, **sin CUDA**, X11/Cinnamon, 176 GB libres.

| Pieza | Elección | Por qué |
|---|---|---|
| Física y vuelo | **Gazebo Harmonic + PX4 v1.15.4**, en las imágenes podman ya fijadas | es el backend que certificó FLIGHT-1S, SENSOR-1S, PX4-1, COMPOSE-1 y DRONE-3; cambiarlo obligaría a recertificar cinco fases |
| Modelado 3D | **Blender** por script (`--background --python`) | libre, exporta glTF/Collada para SDF, y permite generar geometría de forma reproducible en vez de a mano |
| Render de presentación | **VTK 9.6.2** hoy; **Godot 4.7** como visor separado si hace falta | el documento de origen permite un renderer separado «sólo si mejora presentación sin alterar física o logs» |
| Vídeo | **ffmpeg** con `libopenh264` | el ffmpeg del sistema no trae `libx264`; el codificador se detecta, no se supone |

Descartados y por qué: **Isaac Sim** (exige RTX y no es libre), **Unreal**
(EULA y esta iGPU), **O3DE** (demasiado peso para lo que aporta), **Webots**
(bueno, pero es cambiar de backend físico y tirar certificados).

Instalación: Blender de `dnf` quedó roto por un desajuste de ABI con MaterialX
(`undefined symbol: _ZTVN17MaterialX_v1_39_46OutputE`). Se usa la versión
Flatpak, que trae sus dependencias y no depende del estado del sistema.

## 6. META-WORLD-2 — primer contrato

Lo que esta sub-fase debe responder:

> ¿Se puede aumentar extensión, densidad y variedad del mundo sin cambiar
> trayectorias, eventos ni puntuación bajo el backend físico congelado?

Criterios de cierre, del documento de origen:

- las variantes ampliadas conservan aislamiento A/B/C y reproducibilidad;
- no aparecen ramas por nombre de mundo en el núcleo ni en la GUI;
- `seq` de 8 bits no se rompe: sigue identificando estado local, y la
  jerarquía de región/voxel/orientación vive fuera;
- aumentar detalle visual **no** cambia trayectorias, eventos ni puntuación.

Control que hace falsable el cierre: correr el mismo conjunto de semillas
sobre el mundo mínimo y sobre el ampliado con el mismo backend congelado, y
exigir **trazas idénticas** donde la geometría no cambió. Si difieren, la
ampliación tocó la física y el cierre es rojo.

Qué **no** demuestra META-WORLD-2: nada sobre hardware, nada sobre vuelo real,
y nada sobre inteligencia nueva. Es una ampliación del escenario.

## 7. Dónde se escribe

```
echoai/metaverse1/          código nuevo de la fase
echoai/metaverse1/assets/   scripts de Blender y mallas generadas
echoai/lab/metaverse1/      evidencia y trazas
echoai/docs/METAVERSE1-*.md contrato y resultados por sub-fase
echoai/tests/test_metaverse1.py
```

Cero ficheros bajo `nexus0/`. Cero ediciones a `lab/drone3/`,
`lab/transfer3/` o cualquier `lock.json`.

## 8. Estado al abrir

Este documento es el contrato, no el resultado. META-WORLD-2 **no está
cerrado**: no se ha comparado todavía mundo mínimo contra mundo ampliado bajo
el backend congelado, que es su criterio.

Lo verificado hoy, que sí es un hecho:

**Herramientas, instaladas y ejecutadas**

| Pieza | Versión | Comprobación |
|---|---|---|
| Blender (Flatpak) | 5.2.0 LTS | `--background --python` ejecuta y `bpy` responde |
| Godot (Flatpak) | 4.7.2 stable | `--headless --version` responde |
| Gazebo Harmonic | imagen `echoai-sim3-gz:harmonic` | ya fijada desde SIM-3 |
| PX4 | v1.15.4, imagen `echoai-flight1s-px4` | ya fijada desde FLIGHT-1S |

El Blender de `dnf` (5.1.2-2.fc43) **está roto** en esta máquina:
`symbol lookup error: undefined symbol: _ZTVN17MaterialX_v1_39_46OutputE`.
Se usa el Flatpak, que trae sus dependencias. Ambos se instalaron a nivel de
usuario, sin `sudo`; hizo falta añadir el remoto `flathub` al ámbito de
usuario porque el del sistema está filtrado.

**Modelado por script, funcionando**

`metaverse1/assets/build_room.py` genera la sala desde su declaración, no a
mano: 21 × 15 m, celdas de 3 m, paredes de 2,5 m y celdas bloqueadas enteras
—nunca media celda, porque el agente razona en celdas—. Exporta GLB y escribe
un JSON con semilla, celdas bloqueadas y sha256 de la malla.

Reproducibilidad medida: semilla 1 generada dos veces da la **misma malla byte
a byte** (`78166fac299bf54e…`); semilla 7 da otra distinta
(`07c4b479493e9ab7…`). Una sala se puede regenerar desde su declaración, que
es lo que META-WORLD-2 necesita para no depender de ficheros opacos.

`metaverse1/assets/render_room.py` saca la vista previa. La primera versión
apuntaba la cámara con ángulos de Euler a mano y salía el frame **en blanco**;
ahora usa una restricción Track To.

**Lo que esto no es:** geometría, no física. La malla no ha entrado todavía en
Gazebo, no hay vuelo, y nada de esto toca el agente ni ninguna puntuación.

— R.N.
