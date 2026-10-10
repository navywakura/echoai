# METAVERSE-1 — acta de congelado

**Corte:** 2026-09-20, Europe/Madrid  
**Estado:** congelado para reanudación; no se declara cerrado  
**Objeto:** preservar el estado técnico y las decisiones necesarias para continuar la visualización en tiempo real del entorno donde vivirá ECHO-3.

## 1. Declaración del corte

En este corte no se ha cambiado código, certificados ni artefactos de METAVERSE-1. Este documento registra el estado observado y verificado.

METAVERSE-1 sigue **abierto por excepción**. La base `META-WORLD-2` está verde dentro de su alcance actual, pero el visor oficial en tiempo real todavía no existe. De las ocho subfases identificadas, una está hecha y siete permanecen pendientes:

| Subfase | Estado al congelar | Nota |
|---|---:|---|
| META-WORLD-2 | HECHA / verde | Mundo procedural, SDF, declaración y banco determinista. |
| FLIGHT-2 | PENDIENTE | Paridad del vuelo en Gazebo/PX4 sobre el mundo ampliado. |
| SENSOR-2 | PENDIENTE | Telemetría/sensores necesarios para el visor y el replay. |
| PX4-2 | PENDIENTE | Integración y evidencia de la misión en el mundo objetivo. |
| COMMAND-1 | PENDIENTE | Contrato completo de comando, ACK y llegada. |
| TRANSFER-META-1 | PENDIENTE | Adaptador de transferencia hacia visualización/replay. |
| GUI-METAVERSE-1 | PENDIENTE | Visor oficial integrado y verificable. |
| CHIMP-1 | PENDIENTE | Cierre posterior; fuera del corte actual. |

La situación global de ECHO-3 permanece en **14/15** según la documentación de estado existente: METAVERSE-1 es la excepción aún abierta.

## 2. Hecho y verificado

### META-WORLD-2

- Existe el paquete `metaverse1/` con modelo de mundo, generador SDF, declaración y banco.
- Existe una tubería Blender para construir y previsualizar salas/mundos.
- Existen artefactos GLB y PNG en `lab/metaverse1/`.
- El certificado recalculado por `bench.run(save=False)` coincide con el guardado:

```text
certificate_sha256 = f508b10858e2a762e079106dfcb2ea3e5c3d9ac579e190482e4b19345c05d4e0
green = true
```

- Pruebas de METAVERSE-1 ejecutadas en el corte: **23/23 OK**, 4.519 s.

### Base de interfaz y telemetría

- GUI4 existe y sus pruebas pasan: **32/32 OK**, 19.352 s.
- Su vista VTK actual representa una pose `Body3D` discreta. No es todavía una reproducción continua del mundo ECHO-3/Gazebo.
- DRONE3/SITL ya produce fundamentos reutilizables: `trace.jsonl`, `private.jsonl`, ULog, SDF y journal.

### Herramientas disponibles

- Blender: paquete Flatpak 5.2; existen artefactos y recibos que prueban ejecuciones anteriores.
- Godot: paquete Flatpak 4.7.2.
- No existe todavía un proyecto Godot en el repositorio: no se encontraron `project.godot`, escenas `.tscn` ni scripts `.gd`.
- En el entorno aislado de esta revisión, el lanzamiento directo de Flatpak no pudo reservar un identificador de instancia. Esto no invalida los artefactos Blender ya generados; sí impide afirmar una nueva ejecución GUI durante este corte.

## 3. Decisiones arquitectónicas congeladas

Estas reglas siguen vigentes al reanudar:

1. Hay un único thought-bus WSP de 16 bytes. No se crea un segundo bus.
2. NEXUS-0 no usa LLM y no se modifica para alojar el visor.
3. Gazebo/PX4 es la autoridad causal de física, dinámica y misión.
4. Blender es la herramienta de autoría de geometría y materiales exportables.
5. Godot o el renderer de GUI es un observador de sólo lectura. No simula una segunda física, no decide misión y no envía control implícito.
6. Q/T/CAM y los demás streams observados no escriben de vuelta sobre el estado de vuelo.
7. LIVE y REPLAY deben consumir el mismo contrato de eventos; cambia la fuente/reloj, no la semántica.
8. La verdad pública del visor y la verdad privada del operador se mantienen separadas.
9. No se hacen afirmaciones de hardware no demostrado. No existe AKD1000 en el laboratorio.
10. No se mezclan orígenes `live`, `reduced` y `sealed`, ni se alteran artefactos sellados.

Flujo de autoridad congelado:

```text
Blender (autoría GLB)
        |
        v
Gazebo/PX4 (física y misión autoritativas)
        |
        v
logs/telemetría append-only
        |
        +--> replay
        +--> adaptador live
                  |
                  v
       Godot/GUI (render de sólo lectura)
```

## 4. Defecto de custodia descubierto

Hay un defecto crítico de nombres en `metaverse1/assets/build_world.py`: el recibo se escribe como `out/<name>.json`. Cuando la declaración de entrada tiene el mismo nombre y vive en el mismo directorio, el recibo sobrescribe la declaración fuente.

Consecuencia observada: `lab/metaverse1/worlds/wide-3x2.json` contiene ahora un recibo que se referencia a sí mismo y ya no contiene los campos de declaración originales (`schema`, dominio, sólidos, inicio y meta). El GLB existe, pero su fuente declarativa actual no permite demostrar una regeneración íntegra.

Este defecto:

- no invalida el certificado funcional actual de META-WORLD-2, porque ese banco no certifica la tubería Blender;
- sí bloquea una afirmación fuerte de custodia/reproducibilidad del artefacto `wide-3x2.glb`;
- debe repararse antes de ampliar el mundo o iniciar el visor Godot oficial.

Convención ya decidida para la reparación:

```text
<world>.declaration.json
<world>.glb
<world>.build-receipt.json
```

El recibo deberá contener el hash de la declaración y nunca compartir su ruta.

## 5. Autoría y trazabilidad

- Claude Opus 5 fue usado/asignado explícitamente en trabajo de DRONE3.
- No se puede atribuir con rigor la autoría de los archivos actuales de META-WORLD-2 a un modelo concreto: esos archivos están sin seguimiento y no existe un commit que lo demuestre.
- El encargo de DRONE3 dejó Blender, renderer avanzado, game engine y GUI final fuera de alcance; por ello no deben contarse como ya realizados.
- En el momento del corte, `metaverse1/`, `lab/metaverse1/`, `tests/test_metaverse1.py`, GUI4 y sus documentos aparecen como archivos sin seguimiento en Git. El congelado documental no sustituye su revisión y versionado posterior.

## 6. Manifiesto SHA-256 del corte

Los hashes siguientes identifican exactamente los archivos revisados; no implican por sí mismos que estén versionados:

```text
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  metaverse1/__init__.py
e57fee3c6ea7b138d34ec13f718bfc065c350ce9a69597a51049601a131625fb  metaverse1/world.py
17cfd9c02a563640ec8e43a5a18bcf4895fedabfe79dfcc34298820cdc64c90f  metaverse1/sdf.py
ce9af63b498ac1b42f587b1f96a0ae50b2a00b24d0aaad8e4f9cb6f47aea4be2  metaverse1/declare.py
06232a38b3fcb909b8d65f429af4e3c0c96f6142517c6782097446e96b106b52  metaverse1/bench.py
5cc41f844f07410701e5d785071bb7c48ef18e2eeffde0a0fdcd4d4ddc07c0dd  metaverse1/assets/build_room.py
b4fd518beacda79efe0206a6aa29469ad22355d6d39538e0c904f66325f4e8e2  metaverse1/assets/build_world.py
a3f40dca415f49679d37fe0fd7e820549ce21b868e3496779cf782e355291b47  metaverse1/assets/render_room.py
76321f9210841ee8cd78d349510166a874824fa5e287c2e46a5ca34e5f2ac2ca  tests/test_metaverse1.py
1baf1f6b4e13924afbce35f4224c1e51acd73b8bddcd3d2f5722ffb214f0c9b7  docs/METAVERSE1-DESIGN.md
929eaba74211dd70f020da0a62374c0cb68d0a4b09d302f632cedb291d9ee41f  docs/METAWORLD2-RESULTS.md
52e0e35c49505c73e4839008e1d2be3b1ee3c994b8933f6a92207da30810ecdc  docs/POST-ECHO3-DRONE-METAVERSE.md
19cebdcb9a0fd36b72cf43933a7dbadc11f20e4392581f2a73fcb226564ed759  lab/metaverse1/metaworld2-report.json
78166fac299bf54eaa507ab31b4148783af29069db18a5c69b0eac6bb495f86a  lab/metaverse1/rooms/sala-01.glb
8fcc61f0a2abe0592c09d938cdfc8883a39d937eaa67e11de5b4c2b4e23daa5c  lab/metaverse1/rooms/sala-01-preview.png
89dd499e09baf5d852f12d9c05e944cdd2427c93e83fac960405ee4775b2ee85  lab/metaverse1/worlds/wide-3x2.glb
d2d89135db0066cdb13d86d46145ea9fcedd21e959841349345684ce9c9fc35d  lab/metaverse1/worlds/wide-3x2-preview.png
8d4cc7566ac56ddf99e51e5361627949f0a36588b2cc8dcc56a01492547ec11f  lab/metaverse1/worlds/wide-3x2.json
```

## 7. Punto exacto de reanudación

Mañana no se empieza por el acabado visual. Se empieza por reparar la cadena de custodia declaración → GLB → recibo y demostrar que una reconstrucción headless conserva la declaración, produce un recibo separado y genera un artefacto verificable. Después se avanza hacia la paridad Gazebo/PX4 y sólo entonces hacia el adaptador y el visor.

La custodia de la etapa 0 se documenta en
[METAVERSE1-CUSTODY-RESULTS.md](METAVERSE1-CUSTODY-RESULTS.md).

