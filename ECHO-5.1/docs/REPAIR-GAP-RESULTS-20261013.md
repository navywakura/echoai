# PCWORLD-1: resultados de la brecha de reparación · 2026-10-13

Estado: implementación validada; ECHO-5.1 continúa abierto. Rama local
`research/echo-5.1-pcworld1`; no publicación ni push.

## Cambios comprobados

- Feedback de entrada, salida observada y esperada, ligado a recibos no finales.
- Dos intentos de reparación; ejemplo público y casos anteriormente correctos
  primero. Rechazo de regresiones y restauración mediante compare-and-swap.
- E congela el crítico al confirmar un contraejemplo. No se cambia el oráculo
  ni se inventa cobertura de dos categorías.
- Plazos configurables: 300 s por llamada y 900 s por episodio en estos ensayos.
- Los errores de ejecución incorporan stderr observado (máximo 2.048 caracteres),
  conservando estado `unknown`: una excepción no se convierte en refutación de valor.
- Un error posterior no borra la salida esperada de un ejemplo público ya comprobado.
- Modo opcional `contract_only`: reconstruir desde contrato/testigos sin copiar
  el programa original; el parche rechazado permanece como evidencia para corregirlo.

## Resultados locales reales

| Ensayo de desarrollo | Reparaciones que pasan todos los casos | Tokens observados | Auditoría |
|---|---:|---:|---:|
| r1: feedback estructurado | 0/2 | 5,645 | 140 válidos |
| r2: instrucciones explícitas | 0/2 | 7,741 | 154 válidos |
| Reconstrucción con testigo suministrado | 1/2 | 2,846 | 108 válidos |

r1 y r2 son episodios completos sobre Registros y Rutas, semilla 43. Ninguno
sufrió timeout ni cargo por uso desconocido. No se presenta su fracaso como
ventaja: el 7B repitió la lógica defectuosa pese al feedback. En r2, Registros
produjo cuatro sondeos duplicados antes de refutar; los episodios no aíslan
causalmente el cambio de presentación.

Un diagnóstico intermedio de dos propuestas sin fuente cambió los algoritmos,
pero falló en ejecución: faltaba importar `sys` y en Rutas el protocolo de
entrada no correspondía al contrato. Se conservaron esos resultados (0/2).

La reconstrucción final reutiliza los contraejemplos observados de r1 y vuelve
a ejecutarlos antes de reparar. No hay crítico activo: `seeded_diagnostic=true`
identifica un ensayo de reparación aislada, nunca una victoria del brazo E.
Registros pasa todos los casos tras dos propuestas (1.441 tokens); Rutas sigue
fallando tras dos propuestas (1.405 tokens). No se corrigió código candidato
a mano. Los resultados sin reparación también se conservan.

185 tests PCWorld pasaron (63,632 s). Incluyen recuperación de regresiones,
rollback, errores Python, ausencia de datos finales en prompts, límites,
contabilidad, ejecución aislada del parche importado y rechazo de un resultado
GPU vinculado a otras entradas. Esta suite prueba software, no superioridad.

## GPU privada

Se cumple el requisito de una reparación local comprobada. Se envió un
microensayo de dos propuestas, exclusivamente inferencia, a
`navywakura/echo51-repair-proposer14b-20261013` (versiones 1, 2 y 3).
La lectura posterior de metadatos confirma `is_private=true` y `NvidiaTeslaT4`.
No es la campaña interactiva S/I2/F/E: Kaggle no ofrece la frontera local
Bubblewrap/cgroups. Las propuestas se ejecutarán aquí, en el rootfs fijado.

Modelo: Qwen2.5-Coder-14B-Instruct GGUF Q4_K_M, revisión
`d0a692ef765eefbf2fabb130b3cb2e8917e3d225`, SHA-256
`c1e659736d89ac1065fb495330fb824d94001974a4bfa78e7270e43476a8d940`.
llama.cpp b11577 CUDA 12.8; descargas fijadas y verificadas. El worker exige
prueba de capas cargadas en GPU y no vuelve silenciosamente a CPU. Límite de
50 minutos en el worker externo y 60 minutos en Kaggle; no se prometen tiempos
por llamada antes de medir. Cuota previa observada: 25,92 horas GPU.

La versión 1 terminó antes de inferir: 127,009 s de worker, cero propuestas.
El guard de GPU no encontró la línea de offload. El log predeterminado (nivel
3) oculta mensajes internos GGML de nivel 4. Se conserva este fallo de
infraestructura; no se cuenta como error del modelo. La versión 2 activa nivel
4, selecciona CUDA0 explícitamente y registra memoria/procesos GPU antes de
exigir evidencia de offload. No hay fallback a CPU.

La versión 2 terminó correctamente: 49/49 capas en GPU, unos 9.161 MiB
ocupados en CUDA0, 163,170 s de preparación y 227,864 s de worker total.
Las llamadas tardaron 53,403 s (Registros, 574 tokens) y 10,837 s (Rutas,
472 tokens). No se confirma la estimación de dos segundos por llamada.

Verificación local fresca: **1/2**, auditorías válidas (Registros 29 recibos,
Rutas 29). Registros se repara a la primera. Rutas implementa la normalización,
pero espera `{input: ...}` y devuelve `{output: ...}`; el contrato exige recibir
una cadena JSON y emitir otra. El prompt de reparación había omitido el esquema
que sí conoce el conector. Se añade el esquema de entrada y se distingue el
valor de salida de la envoltura usada para representar ejemplos.

La versión 3 contiene **solo el segundo intento de Rutas**. Su preparación
reejecuta únicamente los casos públicos para decidir el reintento y generar
feedback; no usa resultados reservados. Conserva el error TypeError observado,
el parche rechazado y el testigo inicial. Reserva los 24.528 tokens restantes,
descontando los 472 del primer intento. Registros no se vuelve a generar.
La condición de dos intentos se conserva. La versión 3 terminó correctamente:
216,820 s de preparación, 56,644 s de inferencia, 876 tokens en el reintento y
273,968 s de worker. GPU: 49/49 capas. El programa ahora recibe/emite cadenas
JSON y pasa el testigo original, pero falla al intentar subir por encima de la
raíz: `/../../b` produce `/../../b`, cuando el contrato exige `/b`.

Verificación v3: **4/5 casos y tarea NO aceptada**, con 29 recibos auditados.
No se proporcionó este caso final al modelo ni se lanzó un tercer intento.
El resultado combinado sobre las dos tareas es **1/2 completo**, sin ocultar
los fallos intermedios. Registros pasa 5/5 en la primera propuesta; Rutas pasa
4/5 tras la segunda. Rutas utilizó 1.348 tokens de inferencia en total; ambos
problemas, 1.922 tokens. Son ensayos de desarrollo con testigos suministrados,
no una nueva comparación S/I2/F/E ni confirmación independiente.

La omisión del esquema y de errores de ejecución se ha corregido, pero el
ajuste al contraejemplo aún puede introducir una regresión semántica en un caso
nuevo. La brecha de reparación queda **parcialmente mitigada**, no cerrada.
Los oráculos conservaron el rechazo. ECHO-5.1 NO está en verde.

Kaggle confirmó `COMPLETE`; las tres versiones son privadas. Cuota final
observada: 25,74 h GPU restantes (frente a 25,92 h antes de estas ejecuciones;
valores redondeados por la API). Servidor local del 7B y diagnósticos locales
inactivos. No hay campaña de reparación dejada en segundo plano.

## Lo que falta para hablar de ventaja

- Reparación robusta en más familias y entradas nuevas.
- Compatibilizar la política de reparación exclusiva con la cobertura vigente:
  un único contraejemplo reparado no acredita dos categorías de sondeo.
- Comparación nueva S/I2/F/E con modelo, herramientas, costes y aceptación
  comparables; separar mejora de prompts, capacidad del modelo y router.
- Confirmación independiente y ablaciones. Estos casos son desarrollo conocido.

No se cambia S6 ni NEXUS-0. HMAC y replay válidos no prueban invulnerabilidad.
El 14B y otra versión de llama.cpp cambian dos variables; este microensayo no
permite atribuir diferencias únicamente al número de parámetros.

## Reproducción y artefactos

- `artifacts/repair-gap-local-20261013`: r1, fuentes de `87fa143`, auditoría hermana `-audit.json`.
- `artifacts/repair-gap-local-r2-20261013`: r2, fuentes de `3e64b97`, auditoría hermana `-audit.json`.
- `artifacts/repair-spec-first-20261013`: propuestas sin fuente y verificación local negativa.
- `artifacts/repair-reconstruct-20261013`: diagnóstico aislado, fuentes de `66c1adf`, `audit.json`.
- `artifacts/kaggle-repair14b-20261013`: primer envío y lista explícita de archivos/SHA-256.
- `artifacts/kaggle-repair14b-v1-output`: fallo de comprobación de logs, sin propuestas.
- `artifacts/kaggle-repair14b-v2-output` y `-v2-verification`: 1/2, 29 recibos por tarea.
- `artifacts/kaggle-repair14b-v3-20261013-public-evidence`: selección del reintento usando solo ejemplos públicos.
- `artifacts/kaggle-repair14b-v3-output` y `-v3-verification`: Rutas 4/5, rechazo conservado.
- Revisión final del código: `c11e6a5`; las verificaciones importadas registran su manifiesto de fuentes.

Las auditorías se ejecutaron antes de cambiar sus fuentes; para repetirlas se
necesita la revisión indicada. No se elimina la comprobación de identidad para
hacer que una revisión posterior audite como si fuera la misma.
Los artefactos y autoridades privadas permanecen locales; no se incluyen claves
en el notebook. Scripts reproducibles: `run_witnessed_repair.py`,
`prepare_kaggle_repair.py`, `prepare_kaggle_repair_retry.py`,
`kaggle_repair_worker.py` y `verify_kaggle_repair.py`.
