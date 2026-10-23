# echo-nexus 0.1.0 — arnés oficial separado de ECHO

Fecha: 2026-09-29. Developer: rxlabs. Copyright © 2026 RxLabs.

## Publicación

- Web: https://www.rxlabs.org/echo-nexus
- Guía ES / EN / CA: https://www.rxlabs.org/docs/echoai/echo-nexus
- Instalador: https://rxlabs.org/echo-nexus.sh
- Repositorio **solo arnés**, MIT: https://github.com/navywakura/echo-nexus
- Release: https://github.com/navywakura/echo-nexus/releases/tag/v0.1.0
- Commit del arnés: `19040c2`.
- Commit web: `8e9ef02`; estado Vercel `success / Deployment has completed`.
- Wheel SHA-256: `b6b24dda611c3c394d990ec7e2627094239de8ed44033a647d2bed299e3b80a2`.

El repositorio independiente está en `harness/echo-nexus/`. Sus 18 archivos
publicados contienen interfaz, transportes, contratos, instalador, licencia y
tests. No se copiaron módulos ECHO, pesos, datos ni exámenes. El wheel incluye
solo `echo_nexus/` y su metadata. La licencia MIT no se extiende al motor ni
concede derechos de marca. No se afirma que el nombre nuevo esté registrado.

## Funciones

TUI púrpura oscuro, negro y blanco con estrellas decorativas desactivables,
banner, ayuda de sintaxis y autocompletado con Tab. F2 amplía árbol y mundo.
Los sistemas que declaran `NO_COLOR` mantienen esa preferencia.

`/devtest` ejecuta desarrollo; `/backend` carga un manifiesto del operador;
`/watch` lee diarios existentes; `/image` muestra PNG/JPEG con medias celdas;
`/logs` localiza registros; `/stop` cancela solo procesos propios.

Neocórtex opcional por API Chat Completions, Anthropic Messages o GGUF servido
por llama-server en loopback. Las claves se leen del entorno; no se guardan en
la configuración. El modelo conversa y propone: no puede ejecutar herramientas
ni escribir hechos/motores. NEXUS-0 sigue con LLM OFF.

MCP stdio negocia protocolo y permite listar y llamar herramientas explícitamente.
La detección de CLI instaladas no las arranca. Codex app-server no se presenta
como servidor MCP. No se conecta ningún agente automáticamente.

## Adaptador PRIVADO del laboratorio

`harness/local_bridge.py` NO está dentro del repo público. Usa las interfaces
existentes y genera `lab/echo-nexus/backend.json`. Configuración:

```sh
python3 harness/local_bridge.py manifest lab/echo-nexus/backend.json
echo-nexus --backend /home/user/REALRXOS/RXos/echoai/lab/echo-nexus/backend.json
```

Para guardar la conexión, dentro de la TUI:

```text
/backend /home/user/REALRXOS/RXos/echoai/lab/echo-nexus/backend.json
/devtest
```

Catálogo: 26 entradas, 14 de desarrollo, 11 informes/inventarios de lectura y
una demo antigua de córtex bloqueada para mantener NEXUS-0 OFF. Incluye los 17
casos del catálogo GUI existente con su tratamiento correspondiente, integridad,
ARC3-GYM, capacidades sintéticas, regresión de observación e informes ARC,
S6 y EGO-MEMORIA. El inventario de tests de código no autoriza su ejecución
indiscriminada ni abrir campañas selladas.

El conjunto predeterminado ejecuta integridad, ARC3-GYM, pruebas unitarias de
observación/comparación y cuerpo-aprende. Las demás pruebas de desarrollo se
seleccionan por ID o `all`. No se han certificado todos los bancos antiguos con
esta nueva interfaz: los fallos y dependencias ausentes se muestran y detienen
la secuencia. Los informes no se recomputan.

Los nuevos runs se escriben en directorios únicos de
`lab/observability/echo-nexus/`. El diario canónico sigue siendo `thought.jsonl`
o `arc-decisions.jsonl`; stdout solo transporta su vista. El monitor LIF512 y
Adaptive-LIF128 ya existente se distingue de la política CAM/Q/gate. Las capas
z del cuerpo son una proyección del entorno real que nunca vuelve al agente.
ARC3-GYM emite frames reales del env en desarrollo; no es una evaluación ARC
oficial. No se fabrica un monólogo interno ni activación neuronal de un LLM.

## Verificación realizada

- Diez tests automatizados del arnés: manifiestos, rechazo de exámenes sellados,
  lectura incremental y rotación de registros, permisos/redacción de credenciales,
  procesos reales, timeout, negociación/paginación/call MCP, GGUF inválido,
  contrato API con transporte simulado y TUI a 80×30 con Tab/F2/demo.
- MCP real de ECHO: initialize, ocho herramientas y `echo_receipts`, sin error.
- Cuerpo ECHO real: 48 turnos por run, cero llamadas LLM, muestras del monitor.
- ARC3-GYM v3, semilla de desarrollo 0, v5.7 y 120 decisiones: 0/5 niveles,
  122 acciones contando resets. Es una demo observada, no una mejora ni examen.
- Capturas obtenidas del render real de Textual; versiones de escritorio y móvil
  de la web comprobadas con agent-browser, imágenes cargadas y sin overflow.
- Botón copiar, pestañas de comandos, navegación y documentación comprobados.
- `npm run build`, comprobación de whitespace y publicación Vercel correctas.
- Instalador descargado desde producción idéntico al revisado; instalación
  limpia desde la URL pública con hash correcto y detección de herramientas.
- El paquete instalado desde producción ejecutó `/devtest` con sus cuatro
  procesos predeterminados: integridad, ARC3-GYM, regresión unitaria y cuerpo.
  Los cuatro terminaron con exit 0 y sin errores del arnés. Recibo y logs:
  `lab/echo-nexus/verification.json`, `installation.log`, `default-devtest.log`.
- Comprobación de las 190 fuentes protegidas intacta después del desarrollo.

No hubo inferencia de pago ni carga completa de un GGUF durante la validación.
Los contratos API se probaron con respuestas simuladas. Linux/Python 3.14 fue
el sistema ejecutado; macOS y WSL son objetivos del instalador sin ensayo local
en esos sistemas. MCP HTTP y control autónomo de herramientas por el chat no
forman parte de 0.1.0.

## Separación de S6

No se modificó ninguna fuente congelada ni se reabrieron exámenes. La actividad
de esta TUI no convierte S6 en verde: B1–B5 y sus auditorías siguen decidiendo
ese resultado. El coordinador S6 independiente siguió ejecutándose durante el
desarrollo del arnés.


## Actualización 0.1.1 — 2026-09-29

El fallo GGUF original no era simplemente un timeout: `coredumpctl info 72635`
registró SIGABRT en `libggml-hip`, `ggml_backend_cuda_graph_compute`, durante
`common_init_from_params`. Cero capas GPU no desactivaba otras operaciones HIP.
El arnés ahora desactiva dispositivos, capas y host-operation offload, usa
contexto 2048, lotes 256/64, cuatro hilos y muestra progreso con plazo real de
300 s. Cada intento conserva su log y los errores incluyen señal/código.

Qwen3-4B Q4_K_M cargó en 2,08 s y respondió en 31,31 s totales. La versión
publicada se instaló desde rxlabs.org con checksum verificado; se abrió una
ventana real de echo-nexus 0.1.1 y Qwen quedó listo en 2,1 s. Son observaciones
de este equipo, no una garantía universal de rendimiento.

Perfiles persistentes: `/connections`, `save`, `use`, `remove`, `default`.
Configurados localmente `qwen-local` (por defecto), `openrouter` (openrouter/free)
y el manifiesto privado de 26 entradas. La clave OpenRouter solo fue localizada
por nombre y enlazada mediante su ruta; no fue leída ni enviada durante el setup.
El conector lee archivos de credenciales únicamente al efectuar una petición.
La API real queda pendiente de su primer mensaje. Los tests usan credenciales
ficticias y verifican lectura diferida, ocultación y persistencia entre sesiones.

12 pruebas pasan. GitHub arnés `b17aa51`, web `67cae50`, release `v0.1.1`;
Vercel confirma success. Guía actualizada en ES/EN/CA. Instalación anterior
conservada por el instalador. No se modificaron fuentes ni campañas de S6.
Recibo: `lab/echo-nexus/verification-0.1.1.json`.

## Actualización 0.1.2 — actividad, agentes y visor de desarrollo

El arnés incorpora streaming del texto público del neocórtex, fases reales de la
petición, duración y cancelación. `/why` resume los registros recibidos de ECHO;
no inventa pensamientos ni expone razonamiento privado de proveedores. Los campos
reasoning y tool_calls quedan fuera de las respuestas mostradas y del historial.

`/agent` lista `echo-4.0-cognitive-agentic` y `echo-4.5-adaptative-agentic` en esta
instalación. El adaptador privado `harness/dev_bridge.py` selecciona política ARC
v2 frente a la configurada (actualmente v5.7) y biblioteca inicial frente al solver
refinado de desarrollo. Son perfiles de componentes, no una nueva integración
certificada de todos los módulos ni una imagen binaria congelada de ECHO-4.0.
Los ensayos comunes del cuerpo siguen compartidos. El chat Qwen es independiente.

Cada `/devtest` relee el manifiesto y cada proceso importa el código local actual.
`lab/echo-nexus/live-agent.json` fija política, biblioteca y presupuestos; solo se
cambiará la biblioteca por un estado validado, sin adoptar candidatos S6 por su
nombre. Cada ejecución conserva una huella de fuentes y su propio diario.

- `/devtest dev-world`: mundo editable en `lab/echo-nexus/dev-world.json`.
  Una ejecución llegó a la meta en 56 pasos, cero reinicios, presupuesto 240.
- `/devtest arc-gym`: tres semillas públicas de desarrollo (0, 1, 2), 600 pasos
  por escenario. Las tres agotaron el presupuesto con 0/5 niveles; no se corrigió
  esa capacidad del agente mediante cambios cosméticos. Los contadores aclaran
  casos, resueltos, niveles, pasos, reinicios y motivo de parada.
- `/devtest arc1-train`, `arc2-train`, `arc-capabilities`: desarrollo visible.
  En el primer caso público ARC-1, 007bbfb7, el adaptador 4.5 acertó y el inicial
  no. Una sola tarea y presupuestos distintos no prueban mejora general.
- `/devtest arc1-replay`, `arc2-replay`, `arc3-replay`: archivo oficial de
  2026-09-28. Los dos primeros muestran entrada, predicción archivada y solución
  publicada; ARC-3 reproduce acciones y exige hashes de frames idénticos.
  Se verificó un registro de cada dominio; ARC-3 produjo 2017 eventos válidos.
  No se ejecutó un nuevo examen ni se reabrieron campañas.

Coordenadas, brújula y flecha usan metadatos separados del visor. `/cell X Y`
centra/inspecciona la rejilla, F2 amplía, `/view coords off` da una vista compacta.
El cuerpo 3D muestra dirección real y mapeo XYZ; el gym muestra el último
movimiento cuando existe, marcado como tal. Si no hay orientación disponible,
no se inventa. Nada del overlay se devuelve a la observación del agente.

18 pruebas automatizadas pasan. Cuerpo real: 48 frames con orientación y cero
llamadas LLM. El selector cambia los comandos efectivos y mantiene la conexión
lingüística. La validación también cubre streaming incompleto, cancelación y
superposición sin modificar las rejillas originales. Las 190 fuentes protegidas
siguen intactas y el candidato S6 no está listo. La distribución pública incluye
solo el arnés; perfiles privados, adaptadores, motor y credenciales quedan locales.

Publicación final: arnés `918f1ab`, web `731eb03`, release `v0.1.2`, despliegue
Vercel success. Instalación desde la URL pública con hash coincidente. El paquete
instalado ejecutó de nuevo el mundo personalizado: 1/1, 56/240 pasos, cero errores
y reinicios. La ventana real se abrió con 32 entradas, perfil 4.5 seleccionado y
Qwen local listo en 2,1 s. Las demos del cuerpo indican expresamente su ventana de
48 turnos; terminar esa observación no significa que el agente muera. Capturas
reales, OG y thumbnail publicados, rutas sociales de página/guía verificadas en
los tres idiomas, assets en producción HTTP 200. Recibo completo:
`lab/echo-nexus/verification-0.1.2.json`. La copia local de la web quedó sincronizada,
conservando sus dos capturas sin seguimiento anteriores.


## 1.5 beta · integración verificada

N15.1–N15.5 VERDE. [Resultado y límites](ECHO45-HARNESS15-RESULTS.md).
Conexión predeterminada local: `openrouter`; `openrouter-fast` y Qwen preservados.
