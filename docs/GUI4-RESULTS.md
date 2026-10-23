# GUI-4 — resultados

**Estado:** hecho. 20 de septiembre de 2026.
**Tipo:** excepción de fase. **No es un hito de ECHO-3 y no emite certificado.**
ECHO-3 sigue en 14/15 antes y después de GUI-4.

Contrato: [`GUI4-DESIGN.md`](GUI4-DESIGN.md). Se cumple entero.

---

## 1. Cómo se abre

```bash
cd /home/user/REALRXOS/RXos
python3 -m echoai.gui4
```

Siete pestañas: **Casos**, **Red neuronal**, **Red · árbol**, **Dron 3D**,
**Banco**, **Evidencia** y **Tutorial**. Barra superior con Capturar (F5), Grabar, Pausa
(espacio), Paso y modo Presentación.

## 2. Visualización neuronal

NEURAL-VIZ-1 encendía cada neurona con el recuento de spikes del turno, así
que entre turnos la imagen no decía nada y no se veía la evolución. GUI-4
añade:

- **Raster de historia**: tiempo en el eje X, neurona en el Y, 200 turnos de
  ventana. Cada banco (LIF HI, LIF LO, Adaptive-LIF) se normaliza **con su
  propio pico**, porque los recuentos de los 512 LIF son mucho mayores que la
  cola de adaptación y una escala común dejaba la banda ALIF muerta.
- **Tasa de población** por banco, para ver el ritmo de conjunto.
- Separación explícita entre el **monitor** (WSP → LIF512 → Adaptive-LIF, la
  medida de CAPACITY-1) y el **camino de control** (CAM → Q → gate → acción,
  lo que `Agent.turn` usa de verdad). Son afirmaciones distintas y se dibujan
  aparte.
- Barras de Q con signo: una acción con valor negativo se pinta en rojo, así
  se distingue «prefiere fuerte» de «rechaza fuerte».

**La vista clásica se conserva.** «Red · árbol» reutiliza el `NetworkCanvas`
de NEURAL-VIZ-1 sin tocarlo: el grafo orbitable WSP → LIF HI → LIF LO →
Adaptive-LIF → CAM/Q → GATE, con actividad en vivo. El raster dice *cuándo*
disparó el monitor; el árbol dice *qué está conectado con qué*. Las dos sirven,
así que GUI-4 añade la nueva en vez de sustituir la vieja.

Los frames se dibujan con PIL, de modo que **lo que se ve y lo que se graba
son los mismos píxeles**. Se usa DejaVu real: la fuente de mapa de bits de PIL
no tiene acentos y esta GUI escribe en castellano.

Medido en vivo con el caso `cuerpo-aprende`: 200 turnos en la historia, el
agente llega a `Q[acercarse] = −12` tras recompensas de −16 y pasa a elegir
`evitar`. Es exactamente lo que el banco dice que debe ocurrir.

## 3. Catálogo de casos

17 casos. Cada uno declara qué demuestra, qué control lo contrasta y qué **no**
demuestra. **Los 17 se ejecutan en esta máquina.**

| Origen | Casos | Qué significa |
|---|---|---|
| `en vivo` | 4 | el agente real corre ahora en la ventana |
| `banco reducido` | 7 | un banco real de ECHO-3 corre ahora con menos casos |
| `evidencia sellada` | 6 | se reproduce un informe de `lab/`, sin recalcular |

### Los tres que estaban bloqueados

SIM-3, GROUND-1 y CAUSE-1 aparecían deshabilitados con el motivo «necesita el
contenedor PX4/Gazebo». Al comprobarlo, ese motivo estaba mal planteado: los
tres tienen evidencia guardada y **se pueden recalcular en el host**, sin
contenedor y sin volar nada.

| Caso | Qué recalcula ahora | Resultado | Tiempo |
|---|---|---|---|
| `atribucion` · CAUSE-1 | atribución sobre 16 vuelos guardados | **16/16** frente a **8/16** del control temporal | ~4 s |
| `mundos-abc` · SIM-3 | reconstrucción de la evidencia sellada | 416/416 comprobaciones, 24 ejecuciones recalculadas | ~7 s |
| `suelo-wsp` · GROUND-1 | integridad temporal de 30 vuelos grabados | 30/30 ciclo de vida, 30/30 etapas encadenadas | <1 s |

Esto es mejor que antes: la GUI **recalcula** en lugar de leer un número. Lo
que sigue siendo cierto es que no se vuela nada nuevo; los vuelos ya estaban
grabados.

En GROUND-1 la primera versión daba **0/30** porque asumí que el armado iba
antes del despegue. En estos vuelos PX4 ordena primero el modo de despegue y
arma después; además, un evento de driver lleva `ev="driver"` y su nombre real
en `event`, así que leer `ev` etiquetaba los 22 eventos como «driver». La
comprobación sigue a la evidencia, no a la suposición.

## 4. Banco en GUI

Cuatro bancos rápidos, ejecutando el código real de cada fase:

| Caso | Fase | Agente | Control | Techo |
|---|---|---|---|---|
| `composicion` | COMPOSE-1 | **4/4** | Q reactiva **0/4** | convencional 4/4 |
| `energia` | POWER-1 | **4/4** | porcentaje fijo **0/4** | oráculo 4/4 |
| `contencion` | SAFE-1 | 64/64 episodios | — | — |
| `evidencia` | FUSION-1 | 164/164 observaciones | — | — |

Tiempo total: ~1,7 s. Denominador y semillas siempre a la vista. «Exportar
JSON» escribe `lab/gui4/bench-<ts>.json` con caso, fase, semillas,
denominador, brazos, límite, control, versión de Python y plataforma.

El fichero lleva escrito que **no es un certificado**. Un banco reducido tiene
menos potencia que el certificado y puede salir distinto por azar; por eso van
el denominador y la semilla.

## 5. Grabación y capturas

- `Capturar` (F5) → PNG en `lab/gui4/shots/`.
- `Grabar` → un PNG por turno en `lab/gui4/rec-<ts>-<caso>/`, más
  `manifest.json` con caso, origen, semillas, número de frames y rango de
  turnos. Al parar monta el vídeo.
- **El codificador se detecta, no se supone.** El ffmpeg de Fedora viene sin
  `libx264`: el primer intento devolvió `Encoder not found`. Ahora se consulta
  `ffmpeg -encoders` y se usa el primero disponible de `libx264`,
  `libopenh264`, `libvpx-vp9`, `libsvtav1` o `mpeg4`. En esta máquina sale
  **libopenh264** y el MP4 se monta. Sin ffmpeg o sin codificador, la
  grabación sigue funcionando y deja los PNG con su manifest.
- Cada frame lleva su marca de origen en la cabecera.
- Modo **Presentación**: tipografía mayor y sin datos crudos, para grabar.

Se prefiere el volcado interno a la captura de pantalla: no depende del
compositor y cada frame corresponde a un turno concreto.

## 6. Custodia: qué no se ha tocado

**Cero ficheros nuevos bajo `nexus0/`. Cero ediciones a ficheros sellados.**
Todo GUI-4 vive en `echoai/gui4/` (7 módulos) más `tests/test_gui4.py`.

La razón está medida, no es estética: `nexus0/safe1/bench.py`,
`nexus0/power1/bench.py`, `nexus0/host1/bench.py` y `nexus0/cause1/bench.py`
sellan su inventario con `rglob('*.py')` sobre `nexus0/`. Un módulo nuevo ahí
dentro habría roto auditorías que hoy reproducen.

Comprobado tras implementar:

| Auditoría | Certificado | Resultado |
|---|---|---|
| POWER-1 | `6a05ad4c…` | `valid: true`, idéntico al de antes de GUI-4 |
| HOST-1 | `18d4a4fa…` | `valid: true`, idéntico al de antes de GUI-4 |

Ambas siembran su lock con el glob sobre `nexus0/`, así que reproducir el
mismo certificado es la prueba directa de que GUI-4 no ha añadido ni cambiado
nada ahí.

CAUSE-1 sigue fallando su auditoría por inventario dinámico, **como ya
fallaba antes de GUI-4 y antes de DRONE-3**. No es una regresión de esta fase
y no se ha intentado arreglar desde aquí.

## 7. Tests

`tests/test_gui4.py`: **32 tests, todos verdes**.

Cubren el contrato, no los píxeles:

- custodia: ningún `.py` de GUI-4 bajo `nexus0/`, y los 137 ficheros del
  `lock.json` de DRONE-3 siguen existiendo sin rastro de gui4;
- observador: el renderer no muta el snapshot que recibe;
- origen: todo caso declara origen conocido, qué demuestra, control y límite;
- catálogo: sin identificadores repetidos, sin caso huérfano, y todo caso
  bloqueado da su motivo;
- banco: el agente gana a su control con el mismo denominador, todo brazo
  tiene denominador > 0 y el export es rastreable;
- grabación: manifest con origen y rango de turnos, cierre idempotente,
  y negativa clara al montar sin frames.

Dos fallos reales encontrados por los tests y corregidos:

1. **`alif_spikes` es una máscara de bits, no una lista.** `TemporalHead.spikes`
   es un entero de 128 bits; iterarlo lanzaba `TypeError`. Ahora se expande bit
   a bit y la adaptación se dibuja como cola tenue.
2. **La ventana pequeña rompía el render.** Con poca altura el reparto de
   paneles generaba rectángulos invertidos y PIL lanzaba `ValueError`. Ahora
   el reparto sale de un presupuesto y degrada a menos paneles.

Dos más salieron probando en vivo, no en los tests:

3. **Huecos en el raster.** El bucle vaciaba la cola del motor y se quedaba
   sólo con la última fila. Ahora cada turno publicado entra en la historia.
4. **`Encoder not found` al montar el vídeo.** El ffmpeg del sistema no trae
   `libx264`. Ahora el codificador se detecta; en esta máquina es
   `libopenh264`.

Un quinto, de maquetación: las tarjetas de casos no ocupaban el ancho de la
pestaña porque la ventana interior del canvas conserva su ancho pedido. Ahora
se ajusta al canvas y la rueda del ratón desplaza.

Prueba de grabación real: 97 frames del caso `cuerpo-aprende`, turnos 1 a 173,
manifest correcto y MP4 montado.

### Aviso de aislamiento

`tests/test_nexus0.py::TestObj1::test_pulpo_still_has_its_goal_and_nobody_lost_a_report`
marca por tiempo los informes de `lab/` para comprobar que OBJ-1 no pisa el de
otra fase. Falla si **cualquier otra cosa escribe en `lab/` a la vez**. Se vio
al correr `test_gui4` y la GUI mientras la suite estaba en marcha. Aislado pasa
(1 test, 32 s, OK) y la suite limpia sale entera:

```
Ran 488 tests in 247.239s
OK (expected failures=1)
```

El fallo esperado es el `expectedFailure` histórico de WALK-1 sin resto entero,
documentado desde antes. No es una regresión de GUI-4: esa prueba no tolera
concurrencia sobre `lab/`. **No lances la GUI mientras corre la suite.**

## 8. Lo que GUI-4 no demuestra

- No demuestra inteligencia general. Enseña bancos acotados con sus controles.
- No demuestra autonomía física: no hay dron, ni jaula, ni HIL.
- Un caso en vivo es una ejecución, no una medida: n=1 no es un resultado.
- Un banco reducido no es el certificado de su fase.
- El vídeo ilustra. El certificado sale de `lab/` y de sus hashes.

## 9. Siguiente

METAVERSE-1, según `POST-ECHO3-DRONE-METAVERSE.md`. GUI-4 es la base de
GUI-METAVERSE-1: el catálogo, el sello de origen, el banco exportable y el
grabador determinista se conservan; lo que cambia es el mundo que se dibuja.

— R.N.
