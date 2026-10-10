# ECHO-4.5 · decisiones visibles

**29 sep, diagnóstico de capacidades ARC:** el visor muestra los eventos
existentes `verified_hypothesis`, `refinement_round` y `refinement_result`
del refinador. Conserva el hash del diario y distingue ajuste a demostraciones
de corrección de tests. Doce tareas sintéticas, tres condiciones y 36 replays;
sin tocar la observación de exámenes ni las fuentes congeladas de S6.
[Diagnóstico y alcance](ECHO45-ARC-PREPARATION-RESULTS.md).

**29 sep, S6-B11:** desarrollo ampliado con contrastes entre acciones antes y
después de una propuesta. Los reinicios automáticos se alinean con el contador
existente y se distinguen de decisiones del agente. El mismo visor descubre
`lab/observability/s6b11-20260929`; B y examen carecen de instrumentación.
[Implementación y pruebas](ECHO45-S6-B11-IMPLEMENTATION.md).

2026-09-27. Visor local de desarrollo, separado de los exámenes S5-E/S6 ya cerrados.

Roger pidió ver qué hace ECHO en cada prueba, en una mini terminal que abra el
agente. El núcleo ya tenía `nexus0/thought.py` y `nexus0/talk.py` (TALK-1).
Se reutiliza ese registro; ARC v5.7 recibe un observador externo para guardar
decisiones que antes no se exportaban. El visor también lee los diarios S6.

## Qué muestra

- **Núcleo:** observación, acción ejecutada, Q, gate, recompensa, atención,
  predicción T y cambios de aprendizaje, desde el `thought.jsonl` existente.
- **ARC v5.7:** estado y hash del frame observado; hipótesis actuales sobre
  cuerpo, posición y objetivo; ruta pendiente; acción elegida; rama ejecutada;
  búsquedas realizadas; cambio observado, GAME OVER o nivel completado;
  contadores de predicción e hipótesis registradas por el agente.
- **S6:** peticiones reales, tipo P1–P4, propuestas del modelo y veredictos
  V1–V4/aceptación con medidas A/B cuando existen. El texto se abrevia en la
  ventana; el JSONL conserva lo que estaba registrado.

**HISTÓRICO** significa que el archivo ya contenía esos registros cuando el
visor lo abrió. **NUEVO REGISTRO** significa que el visor acaba de leer una
línea añadida. Ninguna de esas etiquetas, por sí sola, certifica que una
campaña siga activa. El estado del diagnóstico propio proviene de su proceso.
Las pruebas S5-E/S6 anteriores siguen cerradas; ver sus diarios no las ejecuta.

Las frases son etiquetas de datos y ramas realmente ejecutadas, no una voz
interior. Cuando ARC declara una hipótesis «confirmed», el visor conserva esa
etiqueta del agente: no certifica que la inferencia sea correcta. Las etiquetas
de rama cubren asignaciones reconocidas; `--technical` enseña además todos los
retornos de `choose()` con función y línea. No se inventa una razón cuando la
rama no tiene una etiqueta traducida.

## Abrir sin configuración

Desde `echoai/`:

```sh
python3 observe.py --launch --demo
```

Abre una terminal Xfce de 105×28, ejecuta cuatro juegos **de entrenamiento**
ARC3-GYM v3 (semillas 0–3, v5.7, hasta 240 decisiones por juego) y sigue
observando archivos después. La pequeña pausa de 35 ms facilita leerla.
No es un examen ni una puntuación certificada. No usa ningún LLM o red.
Cerrar la terminal termina solamente su propio diagnóstico, si sigue activo.

Sesiones y trazas nuevas se guardan en `lab/observability/`, con un directorio
único, `arc-decisions.jsonl`, resultados por juego y `process.log`. Los registros
ARC tienen índice, hora UTC y cadena SHA-256; el visor comprueba el hash de cada
registro leído. Leer una cola histórica no verifica toda la cadena anterior.
El observador se niega a sobrescribir un diario existente.

Para observar sin ejecutar un diagnóstico:

```sh
python3 observe.py --launch
python3 observe.py --once --plain
python3 observe.py --technical RUTA/arc-decisions.jsonl
```

El visor descubre automáticamente nuevos archivos en `lab/observability/`,
el `lab/thought.jsonl` existente y diarios bajo `lab/seed/`. Al abrir muestra
dos registros de los tres archivos más recientes; después sigue todos los
descubiertos. Se pueden pasar rutas explícitas para observar otro diario.
No lee trazas privadas del simulador ni conecta automáticamente con Kaggle.
Un diario remoto aparece aquí cuando la herramienta de seguimiento lo descarga.

Actualización del 29 de septiembre: el lector admite los lotes S6 agrupados
por brazo/semilla y las respuestas guardadas por separado. Conserva los IDs
reales y muestra las medidas A/B, incluidas las regresiones individuales.
En los registros de desarrollo muestra también controles realmente leídos,
predicciones contradichas y revisiones de transición cuando están registrados.
Una cabecera sin misión se muestra sin inventarle una. Ocho pruebas del lector
original y de estos formatos pasan; el visor sigue siendo de solo lectura y
no modifica las fuentes congeladas ni añade instrumentación a los exámenes.

Tras la desconexión del 29 de septiembre, el visor de desarrollo y el seguimiento
B10 se restauraron como servicios de usuario independientes del chat:
`echoai-observe.service` y `echoai-s6b10.service`. Cerrar el visor no detiene
el experimento. [Recuperación y comprobaciones](ECHO45-S6-B10-RECOVERY.md).
El arranque omite el contenido completo de los diarios históricos que no va a
mostrar, conserva una última línea incompleta y decodifica solo las dos entradas
históricas solicitadas. Esto evita procesar miles de colas antiguas antes de
pintar la ventana. Diez pruebas pasan, incluidas continuación de escrituras
partidas, rotación, hashes y formatos S6. Los archivos originales no se editan.

## Nuevas pruebas de desarrollo

ARC usa su entorno gestionado propio, no el proyecto legacy:

```sh
lab/arc3/ARC-AGI-3-Agents/.venv/bin/python -m echo_arc.observe gym --seeds 0 1 2 3 --budget 600
lab/arc3/ARC-AGI-3-Agents/.venv/bin/python -m echo_arc.observe offline lab/arc3/environment_files --budget 500
```

El primer comando solo permite semillas de entrenamiento 0–39; el segundo
ejecuta los juegos locales de desarrollo. El visor ya abierto detecta sus
diarios. No usar estos comandos para repetir o instrumentar un examen sellado.

Para el núcleo, el lanzador pasa `NAVI_THOUGHT_LOG` a un comando de desarrollo,
abre la ventana y conserva su salida en `process.log`:

```sh
python3 observe.py --launch --run python3 -m echoai.nexus0.bench
```

Esto activa únicamente el registro existente: no enciende el córtex ni cambia
opciones del agente. Una ejecución antigua sin traza no permite recuperar las decisiones
que nunca guardó; una ejecución nueva sin estos mecanismos tampoco las exporta.

## Cómo se conserva el comportamiento

`echo_arc/observe.py` envuelve al actor y reenvía todas sus lecturas/escrituras.
Ejecuta el bytecode del `runner.play` original con una fábrica privada, sin
modificar el registro global de agentes ni los archivos congelados. Lee campos
ya calculados; no llama a `_goal()`, `_plan()` o `report()` para explicar una
decisión. Una traza Python temporal observa los retornos y las asignaciones de
acción dentro de `choose()`; se retira incluso si hay una excepción. Rechaza
coexistir con otro trazador Python para no desplazarlo silenciosamente.

El diario es una exportación pasiva; el agente no recibe ni vuelve a leer el
texto del visor. No hay segundo bus de pensamiento, recompensa nueva,
reputación nueva, acceso a estado oculto ni monólogo generado por un modelo.
La misión escrita en el encabezado declara el objetivo del ensayo para el
lector; no es una instrucción interpretada por ARC ni prueba de que comprenda
una misión en lenguaje natural.

**Límite práctico:** trazar, escribir y pausar añade tiempo. Con un límite de
reloj puede reducir las decisiones que caben; la igualdad medida aquí se refiere
a juegos deterministas con presupuesto de decisiones, sin deadline.
Las fuentes, contratos y resultados congelados S5-E/S6 se conservan.

## Memoria temporal v5.8: H1 y H3

El observador también admite `--agent v5.8` y sus ablaciones mediante una
fábrica privada. Registra las ramas de `temporal_agent.py` y exporta
`temporal_state`: cola de entradas, contadores por instancia, hipótesis de
orden/umbral, apoyo, contradicciones, cobertura y cambios remotos observados.
El visor muestra esos valores ya calculados; no crea explicaciones retrospectivas.

```sh
lab/arc3/ARC-AGI-3-Agents/.venv/bin/python -m echo_arc.observe gym --agent v5.8 --seeds 0 4 --budget 600
```

[Funciones y límites de H1/H3](ECHO45-H1-H3-MODULES.md) ·
[Resultados de desarrollo y auditorías](ECHO45-H1-H3-RESULTS.md).

## Verificación

- Ocho pares de partidas de entrenamiento: versiones gym v2/v3, semillas 0–3,
  v5.7, presupuesto 180. Registro completo idéntico con/sin observador:
  acciones, hashes de todos los frames, reinicios, niveles y modelo final.
- El núcleo con y sin `thought_log`: 32 turnos, mismas acciones, Q y métricas;
  los 32 registros pasan el validador TALK-1 y leerlos conserva sus bytes.
- Comprobaciones de líneas incompletas, truncación, sustitución del archivo,
  JSON inválido, alteración del hash, caracteres de control y reenvío de
  escrituras del runner. No se sobrescribe un diario existente.
- Regresión del registro original y TALK-1, con Python del sistema.

El diagnóstico de la ventana terminó: cuatro juegos, 960 decisiones y 960
resultados registrados; cadena completa comprobada. El lanzador del núcleo
exportó también 352/352 turnos del banco original, con cero llamadas al córtex,
cero hechos falsos y Q final `[-12, 5, 0]`. Pasaron 25 controles stdlib y la
comprobación de los ocho pares ARC. Las fuentes del freeze S6-B2 permanecen
idénticas. [Recibo de verificación](../lab/observability/verification-20260927.json).

```sh
PYTHONPATH=.. python3 -m unittest tests.test_observe tests.test_nexus0.TestThoughtLog tests.test_nexus0.TestTalk1 -q
PYTHONPATH=.. lab/arc3/ARC-AGI-3-Agents/.venv/bin/python -m unittest tests.test_observe_arc -v
```

## Misión, reputación y agentes frontier

La autonomía práctica combina el modelo que propone decisiones con un entorno
que le permite observar, actuar y continuar. El runtime del Agents SDK repite
llamadas al modelo y ejecución de herramientas hasta un punto de parada.
Las verificaciones externas se programan: no debe suponerse un segundo modelo
universal que garantice la verdad de cada pensamiento.
[Bucle de agentes](https://developers.openai.com/api/docs/guides/agents/running-agents),
[verificaciones](https://developers.openai.com/api/docs/guides/agents/guardrails-approvals).

Los modelos de razonamiento, incluido Astra, pueden emplear razonamiento interno;
la API ofrece resúmenes, no los tokens brutos de ese razonamiento.
Eso tampoco convierte un resumen en una auditoría de causalidad interna.
[Documentación de razonamiento](https://developers.openai.com/api/docs/guides/reasoning).

Nuestra decisión de diseño propuesta: declarar «completa la tarea y mejora con
resultados comprobados, respetando el presupuesto y evitando regresiones».
Especificar un objetivo común antes del ensayo es legítimo. Consultar respuestas
reservadas, introducir excepciones específicas del examen o manipular la medida
sería romper la comparación. La reputación tiene sentido cuando hay interlocutores
y confianza social; no es necesaria para aprender a llegar a una meta. Esta tarea
añade observabilidad; no implementa todavía un intérprete general de misiones ni
una nueva fase científica, y no cambia el estado ROJO de S6.
