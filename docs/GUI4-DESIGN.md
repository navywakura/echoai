# GUI-4 — contrato prospectivo

**Estado:** contrato escrito antes de implementar. 20 de septiembre de 2026.
**Tipo:** excepción de fase pedida por Roger. **No es un hito de ECHO-3.**
**Sucesor previsto:** METAVERSE-1 (ver `POST-ECHO3-DRONE-METAVERSE.md`).

---

## 1. Qué es y qué no es

GUI-4 es la capa de **presentación y demostración** de echoAI. Sustituye
visualmente a NEURAL-VIZ-1 / GUI-3.5 sin borrarla: `nexus0/neural_viz_gui.py`
se conserva intacta y GUI-4 la importa.

GUI-4 **no emite certificados**. ECHO-3 sigue en 14/15 antes y después de esta
fase. Ningún número que aparezca en pantalla cambia el estado de ningún hito.

Lo que sí debe conseguir:

1. Visualización neuronal mejor que la actual: el monitor de 512 LIF + 128
   Adaptive-LIF legible, con historia temporal, no sólo brillo instantáneo.
2. Un catálogo de **casos de uso** accesible por botones, que demuestre las
   funcionalidades software de ECHO-3.
3. Un **banco en GUI**: ejecutar bancos reales acotados en directo y mostrar
   agente frente a control, con su denominador a la vista.
4. **Grabación y capturas** aptas para publicar: frames deterministas, modo
   presentación, marca de agua de procedencia.

## 2. Dónde vive (invariante de custodia)

Todo el código nuevo va en **`echoai/gui4/`**. Cero ficheros nuevos bajo
`echoai/nexus0/`.

Razón medida, no estética: `nexus0/safe1/bench.py`, `nexus0/power1/bench.py`,
`nexus0/host1/bench.py` y `nexus0/cause1/bench.py` sellan su inventario con
`rglob('*.py')` sobre `nexus0/`. Un `.py` nuevo ahí dentro cambia ese
inventario y rompe auditorías que hoy reproducen. CAUSE-1 ya falla por esa
causa desde antes de DRONE-3; GUI-4 no puede empeorarlo.

Invariantes de custodia:

- Cero ediciones a los 137 ficheros del `lock.json` de DRONE-3.
- Cero ficheros nuevos bajo `nexus0/`.
- Tras GUI-4, `px41`, `safe1_v2`, `power1`, `host1`, `fusion1` y `compose1_v4`
  siguen dando `valid: true` con el mismo certificado.
- GUI-4 importa de `nexus0` en sólo lectura. Nunca al revés.

## 3. Invariante de observador

La GUI no decide. Heredado de NEURAL-VIZ-1 y no negociable:

- La GUI nunca elige una acción ni pulsa `approach`/`avoid`/`wait`.
- La GUI nunca escribe CAM, T, Q, PATTERN ni evidencia.
- La GUI nunca inyecta observaciones en el agente.
- Lo que se dibuja sale de un snapshot inmutable publicado por el worker.
- Si un panel no tiene dato, dice «sin dato». No interpola ni inventa.

Un test comprueba esto por construcción: el snapshot es un `dict` y la capa de
render recibe una copia de sólo lectura.

## 4. Los tres orígenes de un número

Cada cifra en pantalla lleva su origen visible. Sin excepción.

| Origen | Etiqueta en GUI | Qué significa |
|---|---|---|
| **VIVO** | `en vivo` | el agente real corre ahora en esta ventana |
| **BANCO** | `banco reducido · n=N` | un banco real de ECHO-3 corre ahora con denominador recortado para caber en una demo |
| **EVIDENCIA** | `evidencia sellada · <sha8>` | se reproduce un informe cerrado de `lab/`; no se recalcula nada |

Prohibido en GUI-4:

- Presentar un `banco reducido` como si fuera el certificado.
- Mostrar un agregado que mezcle los tres orígenes en una sola cifra.
- Enseñar resultados SITL como si corrieran en directo: DRONE-3, PX4-1,
  COMPOSE-1 SITL y FLIGHT-1S necesitan contenedor y **son EVIDENCIA** salvo
  que el usuario arranque el contenedor explícitamente.
- Cualquier animación que atribuya al agente una decisión que no tomó.

## 5. Catálogo de casos

Un botón «Todos los casos» abre el catálogo completo. Cada caso declara:
identificador, fase de origen, tipo (VIVO/BANCO/EVIDENCIA), qué demuestra, qué
control lo contrasta, cuánto tarda y qué **no** demuestra.

Cobertura objetivo, por fase de ECHO-3:

| Caso | Fase | Tipo | Qué debe verse |
|---|---|---|---|
| `cuerpo-aprende` | ECHO-1/2 | VIVO | Q parte de 0 y cambia por consecuencia |
| `muerte-herencia` | GEN-1f | VIVO | muerte, respawn, hijo con memoria nueva |
| `sueño` | SLEEP-2 | VIVO | consolidación sin reescribir CAM/T/Q |
| `mundos-abc` | SIM-3 | BANCO | la evidencia sellada se reconstruye entera |
| `suelo-wsp` | GROUND-1 | BANCO | integridad temporal sobre 30 vuelos grabados |
| `identidad` | PATTERN-1R | EVIDENCIA | 4591/4866 identidades, 45 confusiones, 230 desconocidos |
| `dinamica` | DYNAMIC-1 | EVIDENCIA | seguimiento de normal desde hover |
| `evidencia` | FUSION-1 | BANCO | procedencia, caducidad y conflicto conservados |
| `composicion` | COMPOSE-1 | BANCO | agente completo 6/6 frente a Q reactiva 0/6 |
| `atribucion` | CAUSE-1 | BANCO | 16/16 frente a 8/16, recalculado sobre vuelos guardados |
| `energia` | POWER-1 | BANCO | metas factibles frente al porcentaje fijo |
| `contencion` | SAFE-1 | BANCO | veto, enclavamiento y aterrizaje nativo PX4 |
| `autoridad` | HOST-1 | BANCO | autoridad de fuentes actualizada por consecuencias |
| `transferencia` | TRANSFER-3 | EVIDENCIA | B 38/0 y C 48/1, campaña sellada |
| `mision` | DRONE-3 | EVIDENCIA | 12/12 y 12/12, cadena completa por vuelo |
| `enlace` | PX4-1 | EVIDENCIA | 48/48 intentos inválidos bloqueados |

Un caso que no pueda ejecutarse en la máquina actual aparece **deshabilitado
con su motivo escrito**, no oculto. Hoy no hay ninguno: los 17 se ejecutan.

## 6. Banco en GUI

Pestaña «Banco». Ejecuta en directo, con barra de progreso y cancelación:

- agente completo frente a su control, sobre las mismas semillas;
- denominador visible y semillas visibles;
- resultado como tabla, no como veredicto;
- un botón «exportar» que escribe `lab/gui4/bench-<ts>.json` con semillas,
  denominador, versión y origen, para que el número sea rastreable.

El banco de GUI **no** abre campañas selladas, no toca `lab/drone3/`,
`lab/transfer3/` ni ningún `lock.json`.

## 7. Grabación y capturas

- Tecla de captura: escribe PNG de la ventana o del visor 3D en `lab/gui4/shots/`.
- Grabación: volcado de frames PNG numerados y determinista por tick, más un
  `manifest.json` con tarea, semilla, turno inicial y final.
- `ffmpeg` se usa sólo para montar el vídeo a partir de los frames, si existe.
  Si no está instalado, la grabación sigue funcionando y deja los PNG.
- Modo presentación: tipografía grande, paneles esenciales, sin datos crudos.
- Modo ingeniería: todo visible.
- Marca de origen en cada frame grabado: `VIVO` / `BANCO` / `EVIDENCIA`.

Se prefiere el volcado interno a la captura de pantalla: no depende del
compositor y cada frame corresponde a un tick concreto.

## 8. Criterios de cierre de GUI-4

GUI-4 queda hecha cuando:

1. `python3 -m echoai.gui4` abre la ventana y corre un caso VIVO sin bloquear.
2. El catálogo lista los 16 casos con tipo, control y límite; los ejecutables
   se ejecutan y los no ejecutables explican por qué.
3. El banco en GUI produce agente-frente-a-control con denominador visible y
   exporta JSON rastreable.
4. La grabación produce PNG numerados y un manifest; con `ffmpeg` produce MP4.
5. `tests/test_gui4.py` pasa, incluyendo: invariante de observador, etiquetado
   de origen obligatorio, catálogo sin caso huérfano y export con semillas.
6. La suite completa sigue verde y `px41`, `safe1_v2`, `power1`, `host1`,
   `fusion1` y `compose1_v4` reproducen su certificado.
7. Ningún fichero bajo `nexus0/` ha cambiado ni se ha añadido.

## 9. Lo que GUI-4 no demuestra

- No demuestra inteligencia general. Enseña bancos acotados con sus controles.
- No demuestra autonomía física: no hay dron, ni jaula, ni HIL.
- Un caso VIVO es una ejecución, no una medida: n=1 no es un resultado.
- Un `banco reducido` tiene menos potencia que el certificado y puede salir
  distinto por azar; por eso lleva denominador y semilla a la vista.
- El vídeo ilustra. El certificado sigue saliendo de `lab/` y sus hashes.

— R.N.
