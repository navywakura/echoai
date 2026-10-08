# Prompt de implementación para Claude — SIM-3

Copia el bloque siguiente en Claude Code desde el directorio `echoai/`.

---

Implementa SIM-3 conforme a `docs/SIM3-DESIGN.md`. No diseñes otro agente ni
adelantes fases posteriores para producir una demo. Trabajas en el repositorio
local de echoAI; no publiques en la web ni hagas push salvo petición expresa.

Lee primero `CLAUDE.md`, `docs/05-NEXUS-0-SPEC.md` y las lecturas obligatorias
indicadas en `CLAUDE.md`. Después lee `docs/ECHO-3-ACCEPTANCE.md`,
`docs/SIM3-DESIGN.md`, ambos `docs/schemas/sim3-*.schema.json` y los tres
ejemplos de `docs/examples/sim3/`. Inspecciona `nexus0/loop.py`, `env.py`,
`world.py` y los comandos reales de test antes de cambiar nada.

Tu pregunta de cierre: mismo ejecutable, mundos declarativos diferentes,
física Gazebo observada y verdad inaccesible al consumidor. No es todavía
aprendizaje ni vuelo de echoAI. Hardware y Akida ausentes; córtex apagado.

### Alcance y archivos

- Implementación nueva preferentemente en `nexus0/sim3/`, herramientas del
  propio slice, tests en `tests/test_sim3*.py`, evidencia en `lab/` y assets
  pequeños del slice. Conserva los ejemplos de docs como fixtures públicas.
- No tocar WSP, CAM, Q/T/PATTERN, gate, GUI, kernel, ISO ni drivers. No cambiar
  el significado de `greedy=True`. Si necesitas hacerlo, documenta dependencia
  y detente sólo en ese punto; no amplíes el tajo unilateralmente.
- Añade dependencias aisladas y reproducibles; evita instalaciones globales.
  Registra herramientas reales y permisos. Sigue la política de autorización
  del entorno si una instalación o contenedor requiere aprobación.
- No sustituir Gazebo por Body3D, un array de cajas o un replay. Puedes tener
  fixtures unitarias explícitas; no sirven como certificado del backend.

### Ejecución por cortes

1. Valida esquemas, JSON estricto, hashes y perfil SDF cerrado. Implementa las
   comprobaciones semánticas que JSON Schema no expresa. Verifica con
   libsdformat real además del parser propio. Rechaza campos/XML no soportados.
2. Implementa preflight y `runtime-lock.json`; usa Gazebo Harmonic compatible
   con versiones fijadas. Inyecta únicamente plugins/rig de confianza y guarda
   SDF efectivo. Demuestra caída, contacto y avance de 1.000 pasos reales.
3. Separa supervisor, evaluador y consumidor con permisos efectivos. Probe
   sin Agent, contrato tick/ACK, proceso limpio, canal acotado y namespaces.
   Ningún manifiesto, seed, rol, entidad o mapa visible al consumidor.
4. Genera las 12 fixtures rehearsal con el mismo código. Valida conectividad,
   diferencias geométricas y pares metamórficos. Implementa compromiso,
   apertura y consumo de particiones usando exclusivamente secretos de ensayo.
5. Ejecuta banco, mutantes, auditor y regresión relevante. Publica un informe
   honesto por caso, con comandos reproducibles y errores conservados.

Puedes paralelizar tareas independientes en archivos separados si dispones de
agentes, pero integra y revisa cada resultado. No gastes razonamiento de modelo
en resumir miles de líneas: scripts para conteos y tablas; inspecciona fallos.

### Candados del examen

- NO abras ni generes C final en un directorio accesible a desarrolladores.
  Todo C usado aquí se llama rehearsal-C. Custodio final: Roger.
- Mismo hash de ejecutable/configuración pública entre A/B/C; no ramas por
  sala, rutas, nombres o seeds. El protocolo privado construye/evalúa el mundo;
  nunca se convierte en input cognitivo.
- No entregues `Cell.kind` derivado de la verdad del simulador como sensor.
  El Agent actual se valida en su regresión separada. No simules integración.
- No cambies N, tolerancias ni umbrales después de mirar un rojo. Una corrección
  técnica se registra y repite; una revisión del contrato requiere una versión
  nueva visible y no borra la evidencia anterior.
- El auditor debe rechazar mutantes partiendo de evidencia positiva; comprobar
  que un informe que ya era rojo sigue rojo no demuestra detección.
- Sin dependencias: `not_run`, `sim3_green=false`, causa y siguiente comando.
  Continúa las partes ejecutables; no fabriques números ni afirmes aislamiento
  físico a partir de mocks. Hardware seguirá `not_available` aunque SITL pase.

### Interfaz CLI objetivo (todavía no existe)

Desde `echoai/`, ofrece una CLI equivalente a:

```bash
PYTHONPATH=.. python3 -m echoai.nexus0.sim3 validate --package docs/examples/sim3 --protocol docs/examples/sim3/protocol.json
PYTHONPATH=.. python3 -m echoai.nexus0.sim3 preflight --output lab/sim3/runtime-lock.json
PYTHONPATH=.. python3 -m echoai.nexus0.sim3 bench --rehearsal --output lab/echo3_sim3_report.json
PYTHONPATH=.. python3 -m echoai.nexus0.sim3 audit lab/echo3_sim3_report.json
```

`bench` debe exigir o generar y congelar el lock antes de medir, incluir las
pruebas preregistradas y devolver exit code distinto de cero si no cierra.
Los comandos definitivos y requisitos se documentan con su salida real.
El paquete de ejemplo no reemplaza los 12 paquetes del banco.

### Entrega y revisión

Entrega archivos cambiados, tests/comandos ejecutados, informe, estado de cada
grupo y limitaciones. Actualiza NOW/ROADMAP sólo con lo que esté medido; no
marques FLIGHT-1 ni transferencia como completas. Conserva resultados rojos.

Antes de terminar, revisa: ¿alguna rama mira la sala?, ¿el consumidor puede
leer la verdad?, ¿el reloj viene del backend?, ¿los hashes se verifican contra
artefactos y compromisos?, ¿algún test espera el mismo valor que su mock acaba
de inventar?, ¿has consumido un examen reservado?, ¿cambiaste el núcleo?

La revisión posterior por Codex será independiente: inspección de límites,
repetición de pruebas seleccionadas y mutación de evidencia. No se promete
verde de antemano: se exige que el verde signifique el contrato medido.
