# METAVERSE-1 — handoff para 2026-09-21

Este documento es el punto operativo de reanudación posterior al corte registrado en `docs/METAVERSE1-FREEZE-20260920.md`.

## 1. Lectura obligatoria antes de tocar código

Orden recomendado:

1. `CLAUDE.md`
2. `docs/05-NEXUS-0-SPEC.md`
3. `docs/METAVERSE1-FREEZE-20260920.md`
4. `docs/METAVERSE1-DESIGN.md`
5. `docs/METAWORLD2-RESULTS.md`
6. `docs/POST-ECHO3-DRONE-METAVERSE.md`
7. Código y pruebas de `metaverse1/`
8. Código y pruebas de GUI4 sólo al llegar a la integración del visor

## 2. Límites de trabajo

No hacer al reanudar:

- no crear otro thought-bus ni ampliar el WSP de 16 bytes;
- no activar un LLM para NEXUS-0;
- no añadir archivos bajo `nexus0/` para resolver visualización;
- no dar a Godot autoridad de física, control o misión;
- no modificar evidencia sellada ni mezclar `live`, `reduced` y `sealed`;
- no afirmar hardware inexistente o no demostrado;
- no contar una animación local como cierre de GUI-METAVERSE-1;
- no versionar en bloque el worktree sucio sin revisar uno por uno los archivos de alcance.

## 3. Objetivo inmediato

Reparar primero la cadena de custodia de los mundos Blender. La salida mínima aceptable es:

```text
world.declaration.json     # fuente inmutable para la construcción
world.glb                  # resultado visual
world.build-receipt.json   # herramienta, parámetros y hashes
```

El constructor debe rechazar rutas de entrada y recibo idénticas. El recibo debe incluir al menos:

- esquema y versión del recibo;
- fecha/hora y herramienta de construcción;
- ruta y SHA-256 de la declaración;
- ruta y SHA-256 del GLB;
- parámetros relevantes de Blender/exportación;
- resultado explícito de validación.

Pruebas mínimas de esta reparación:

1. La declaración fuente sigue byte a byte intacta después del build.
2. Entrada, GLB y recibo son tres rutas diferentes.
3. El recibo apunta a la declaración, no a sí mismo.
4. Los hashes registrados coinciden con los archivos.
5. Una reconstrucción headless produce un GLB importable.
6. El fallo de Blender/exportación no deja un recibo verde engañoso.

No intentar reconstruir `wide-3x2` desde el JSON sobrescrito. Primero hay que recuperar o regenerar de manera explícita su declaración y registrar que es una reconstrucción, no el original perdido.

## 4. Roadmap restante

### Etapa 0 — Custodia de assets

- Corregir los nombres y la protección contra sobrescritura.
- Añadir pruebas de regresión de la cadena declaración/artefacto/recibo.
- Recuperar o regenerar la declaración `wide-3x2` de forma auditable.
- Ejecutar Blender headless y registrar hashes nuevos.
- No sustituir silenciosamente los artefactos del corte: conservar o etiquetar la relación con los anteriores.

**Criterio de salida:** el mundo se puede regenerar sin perder su fuente y el recibo demuestra qué entrada produjo qué GLB.

### Etapa 1 — FLIGHT-2 / paridad Gazebo-PX4

- Generar el SDF ampliado a partir de la misma declaración canónica del mundo.
- Comenzar por un caso mínimo y después probar 2x2 y 3x2.
- Ejecutar la misión en Gazebo/PX4 congelado.
- Comparar pose, contactos, eventos, llegada y puntuación con los contratos actuales.
- Registrar mundo, versión, semilla, configuración y origen de cada ejecución.

**Criterio de salida:** la misión pasa en el mundo objetivo con evidencia reproducible, sin que el renderer intervenga en el resultado.

### Etapa 2 — Contrato de telemetría y TRANSFER-META-1

Crear un adaptador fuera de `nexus0/` que lea fuentes existentes y produzca un contrato común para LIVE y REPLAY. Debe normalizar como mínimo:

- timestamp monotónico y timestamp de origen;
- posición y orientación/cuaternión;
- estado/sensores necesarios;
- WSP observado;
- CAM, T, PATTERN y Q cuando estén disponibles;
- gate, setpoint, ACK, llegada y reward/score;
- hash/identidad del mundo;
- origen de datos (`live`, `replay`, `reduced` o `sealed`) sin mezclarlos;
- separación entre campos públicos y privados del operador.

El adaptador es append-only/read-only frente a vuelo. No introduce comandos laterales.

**Criterio de salida:** una misma secuencia puede reproducirse de forma determinista y alimentar un consumidor en vivo con el mismo esquema.

### Etapa 3 — Prototipo Godot de sólo lectura

Crear el proyecto bajo una ruta explícita como `metaverse1/godot_viewer/`:

- importar el GLB validado;
- documentar y probar la conversión de ejes Blender/Gazebo/Godot;
- renderizar la pose de ECHO-3 desde el adaptador, sin física propia;
- añadir cámaras libre, persecución y FPV;
- añadir trail, obstáculos y marcadores de inicio/meta;
- mostrar claramente modo LIVE o REPLAY y el origen de la telemetría.

Godot no decide colisiones, no integra dinámica, no calcula llegada y no controla PX4.

**Criterio de salida:** el mismo replay produce la misma trayectoria visible y cerrar el visor no afecta a la misión.

### Etapa 4 — Visualización en tiempo real

- Seguir el log/stream append-only de la ejecución activa.
- Definir buffering, ordenación temporal y tratamiento de eventos tardíos.
- Si el renderer no alcanza el ritmo, descartar/interpolar cuadros visuales, nunca telemetría de custodia.
- Medir latencia de extremo a extremo y jitter.
- Probar desconexión/reconexión y fin limpio de misión.

**Criterio de salida:** LIVE sigue a Gazebo/PX4 dentro del presupuesto declarado y REPLAY conserva todos los eventos.

### Etapa 5 — Timeline y GUI4

- Integrar scrub, play/pause, velocidad, salto a gate/evento y selección LIVE/REPLAY.
- Vincular marcadores visuales con ACK, gate, llegada, reward y anomalías.
- Mantener la verdad privada del operador separada de la vista pública.
- Evitar que acciones puramente visuales escriban sobre la misión.

**Criterio de salida:** un operador puede inspeccionar una ejecución completa y correlacionar escena, trayectoria y eventos.

### Etapa 6 — Decisión del renderer oficial

Resolver explícitamente el contrato de entrega:

- **VTK/GUI4:** camino más corto hacia una sola ventana Python nativa, pero exige elevar mucho la escena 3D actual.
- **Godot separado:** mayor calidad y herramientas 3D, pero sólo es aceptable como observador externo si el requisito final permite dos procesos/ventanas.
- **Integración embebida:** no asumirla; debe probarse y medirse antes de comprometer el cierre.

No declarar `GUI-METAVERSE-1` cerrado hasta documentar cuál opción cumple el requisito oficial de ventana/proceso y hasta disponer de pruebas end-to-end.

### Etapa 7 — Cierre y regresión

- Banco determinista de replay.
- Pruebas de que el visor no altera misión ni logs.
- Pruebas de coordenadas, orientación y sincronización.
- Presupuestos medidos de FPS, latencia, memoria y pérdidas visuales.
- Evidencia separada para LIVE y REPLAY.
- Documentación, recibos y hashes finales.
- Repetir regresiones de NEXUS-0, vuelo, METAVERSE-1 y GUI4 según el alcance afectado.

## 5. Arranque de mañana

Ejecutar primero comprobaciones de sólo lectura:

```bash
git status --short -- metaverse1 lab/metaverse1 tests/test_metaverse1.py gui4 tests/test_gui4.py docs
PYTHONPATH=.. python3 -m echoai.tests.test_metaverse1
PYTHONPATH=.. python3 -m echoai.tests.test_gui4
```

Recalcular el banco sin guardar y confirmar que el certificado sigue siendo el del corte:

```bash
PYTHONPATH=.. python3 - <<'PY'
from echoai.metaverse1.bench import run

result = run(save=False)
print(result)
PY
```

Resultado esperado antes de editar:

```text
green = true
certificate_sha256 = f508b10858e2a762e079106dfcb2ea3e5c3d9ac579e190482e4b19345c05d4e0
```

Después:

1. Abrir `metaverse1/assets/build_world.py` y su prueba.
2. Diseñar el cambio mínimo de nombres y validaciones.
3. Añadir primero las pruebas de no sobrescritura.
4. Implementar la reparación.
5. Ejecutar el banco y volver a calcular hashes.
6. Registrar cualquier desviación respecto al acta de congelado.

## 6. Condiciones de parada

Detenerse y documentar antes de avanzar si ocurre cualquiera de estas condiciones:

- la corrección exige modificar `nexus0/` o crear otro bus;
- no puede establecerse una única fuente canónica para mundo/SDF/GLB;
- Gazebo y el visor requieren autoridades de física distintas;
- LIVE exige escribir desde el renderer hacia PX4;
- se pierde la separación entre datos públicos y privados;
- una prueba requiere alterar evidencia sellada;
- el GLB no puede relacionarse criptográficamente con su declaración;
- el requisito de una sola ventana/proceso entra en conflicto con Godot separado y no hay decisión explícita.

## 7. Definición de éxito final

METAVERSE-1 estará listo para cierre oficial sólo cuando una misión real de ECHO-3 en Gazebo/PX4 pueda verse en tiempo real y reproducirse después desde evidencia persistida, con el mismo mundo y contrato temporal, sin que Blender/Godot/GUI creen una segunda verdad física ni modifiquen la misión.

