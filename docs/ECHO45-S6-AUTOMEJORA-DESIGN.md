# ECHO-4.5 · S6 (automejora: ECHO pregunta, el modelo propone, ECHO verifica) · contrato · APROBADO

Estado: **aprobado por Roger el 2026-09-26** («cuando acabes empieza S6»). Paso 0 en Kaggle con GPU
gratis (elección de Roger), subiendo `echoai/seed` y las tareas de entrenamiento públicas como dataset
privado.

Roger, 2026-09-26: «¿el LLM hace más listo a ECHO? que ECHO intente modificarse usando una API…
y ver si se automejora para ir más a lo general… poder poner una solicitud al LLM personalizada».

Esto adelanta y concreta la S6 de `ECHO45-DECISIONES.md` §5 («córtex opcional: el modelo propone y
ECHO verifica»).
- **Qué cambia:** el modelo ya no resuelve tareas. **Propone cambios a ECHO**, y ECHO decide qué se
  queda.
- **Precedentes del patrón «modelo propone, evaluador estricto decide»:** FunSearch, AlphaEvolve,
  Voyager y Darwin Gödel Machine. Es PLAN: no afirmamos que funcione aquí hasta medirlo.

## Pregunta que responde

> Con el mismo número de llamadas al modelo, ¿resuelve ECHO más tareas **que nunca ha visto** si él
> mismo decide qué pedir y verifica lo que recibe?

## Alcance

- **Fase A (este contrato): rejillas.**
  - El modelo propone **operaciones nuevas** para el vocabulario de la semilla: funciones puras de
    rejilla a rejilla, con o sin parámetro de color.
  - La base es el sandbox oficial `echo45-s2v` (24 tareas reservadas).
- **Fase B (contrato aparte, después de S5): juegos.** El modelo propone estrategias para `echo-arc`,
  y se verifican en ARC3-GYM y en los 8 juegos de desarrollo. **No** entra aquí.

## Qué puede cambiar ECHO y qué no

| Puede proponer | Nunca puede tocar |
|---|---|
| operaciones nuevas del vocabulario (`seed/proposals/`, un archivo por operación aceptada con su hash en el diario) | `gym._guard`, las evaluaciones selladas y la lista de tareas reservadas |
| — | el verificador (`learn.solve` en modo verificación), `sandbox.verify` y la cadena del diario |
| — | este contrato, los criterios y el código de medida |
| — | el cortafuegos, `code_gate` y el stop |

**Control de integridad:**
- antes y después de cada ronda se calcula el sha256 de los archivos protegidos;
- una sola diferencia anula la campaña.

## El bucle (una ronda)

1. **ECHO mira sus fallos.** Solo usa las tareas de la partición **A** (ver abajo):
   - lista las que no resuelve;
   - de cada una guarda su **casi-acierto**: el programa que más celdas acertó, con el diff.
2. **ECHO construye la petición.** Elige un **tipo de petición** y lo rellena con sus propios datos:

   | Tipo | Qué pide |
   |---|---|
   | P1 · casi-acierto | «Con mi programa X acierto el 90 % de esta tarea; falla aquí (diff). Proponme una operación que lo arregle» |
   | P2 · grupo de fallos | «Estas 5 tareas fallan y se parecen en esto (colores, tamaños, nº de objetos). Proponme una operación común» |
   | P3 · generalizar | «Este concepto mío (`@kNNN`) resuelve estas tareas. Proponme una versión más general» |
   | P4 · libre | ECHO compone la petición con los campos que elija de su diario (tareas, casi-aciertos, conceptos, operaciones que nunca usa) |

   La plantilla de cada tipo es fija. **Los datos y la elección del tipo son de ECHO.**
3. **El modelo propone** el código de una función. Solo recibe tareas de la partición A: nunca
   reservadas, nunca evaluación.
4. **ECHO verifica** la propuesta. Se acepta solo si pasa **todo**:
   - V1: supera el control de código: AST sin `import`, sin `__`, sin `open`/`exec`/`eval`,
     reutilizando `echo4/arc2_bench.check_code`;
   - V2: se ejecuta en un proceso aislado (CPU 5 s, memoria 512 MB, 16 descriptores) y es
     determinista (dos ejecuciones iguales);
   - V3: con ella, ECHO resuelve **≥ 2 tareas de A** que antes no resolvía, verificadas con todos
     los ejemplos;
   - V4: en la partición **B**, **no** baja el número de tareas resueltas. Así una operación
     acertada no se acepta si sobrecarga la búsqueda: es la lección de S2.
5. **Aprender a preguntar.**
   - Cada tipo de petición lleva dos contadores enteros: intentos y aceptadas.
   - La elección es entera:
     `puntos = aceptadas*1000 // (intentos+1) + 300 // (intentos+1)`
     (se elige el máximo; el empate lo decide la semilla).
6. **Sueño.** Tras cada ronda, el sueño normal de S2 comprime las operaciones nuevas en conceptos.

Todo queda en el diario encadenado:
- la petición exacta;
- la respuesta cruda;
- el veredicto V1–V4 con su motivo.

## Particiones

- Las **808 tareas de entrenamiento** se parten, con una semilla fija escrita antes de medir, en:
  - **A** (606): proponer y aceptar;
  - **B** (202): no empeorar.
- Las **201 reservadas** no se tocan hasta el final de cada brazo.

## Brazos (el mismo modelo y el mismo número de llamadas, N = 300)

| Brazo | Qué es |
|---|---|
| **SEMILLA** | `echo45-s2v` sin cambios (24 reservadas; control) |
| **FIJO** | una sola petición fija («aquí tienes 5 tareas que fallo; propón una operación»), con las mismas V1–V4 |
| **ECHO** | peticiones P1–P4 construidas por ECHO, más el aprendizaje de qué pedir, con las mismas V1–V4 |
| **SIN FILTRO** | las **mismas** propuestas del brazo ECHO, aceptadas sin V3 ni V4 (solo V1 y V2 por seguridad). Mide cuánto vale verificar. No cuesta llamadas extra |

Rondas: 10 de 30 llamadas.

## Criterio (fijado antes de medir)

| Id | Condición |
|---|---|
| A1 | reservadas del brazo ECHO **≥ 27** (+3 sobre la semilla, lo mismo que dio S2) |
| A2 | reservadas del brazo ECHO **>** brazo FIJO. Que ECHO elija qué pedir tiene que aportar algo |
| A3 | tasa de aceptación del brazo ECHO en las rondas 6–10 **>** rondas 1–5 (aprende a preguntar) |
| A4 | reservadas de SIN FILTRO **<** brazo ECHO (verificar aporta) |
| A5 | integridad: hashes protegidos idénticos, 0 escapes del aislamiento, `verify` del diario válido, y reconstruir la biblioteca desde el diario da el mismo resultado byte a byte |

**S6-A verde = A1 ∧ A2 ∧ A3 ∧ A4 ∧ A5.** Si sale rojo se publica igual, con qué condición falló.

Se informa además:
- el coste por operación aceptada (llamadas, tokens y dólares);
- las operaciones aceptadas, legibles, con qué tareas resolvieron;
- las rechazadas por cada motivo.

## Modelos y coste

- **Paso 0 · gratis (se hace primero):**
  - un modelo abierto de código en las 2×T4 de Kaggle, que Roger elige;
  - el bucle entero corre en el notebook: verificar es CPU;
  - antes hay que subir `echoai/seed` como dataset de Kaggle, **con confirmación de Roger**;
  - estimación: 600 llamadas en 3–5 h de GPU, dentro de la cuota semanal.
- **Paso 1 · de pago, solo con orden de Roger:**
  - repetir los brazos FIJO y ECHO con un modelo frontier (OpenRouter, Claude Code o Codex), con un
    tope en dólares que fija Roger;
  - hoy quedan unos 0,58 $ en OpenRouter;
  - `claude -p` dio límite de gasto mensual: confirmar la facturación antes.
- Así se responde a una segunda pregunta: **¿un modelo mejor hace más listo a ECHO?**

## Límites declarados

- **Contaminación.**
  - Las tareas de ARC-AGI-1 son públicas y el modelo puede haberlas visto al entrenarse.
  - Mitigaciones:
    - el modelo nunca recibe tareas reservadas ni de evaluación;
    - lo que se acepta son operaciones generales, no respuestas;
    - cada operación aceptada se publica para que se pueda juzgar si es general o una trampa hecha
      a medida.
- **Autoría.**
  - Las operaciones del brazo ECHO las **escribe un modelo**. En el examen de ECHO-4.5 (R1, R2) se
    darán **dos cifras**: con y sin las operaciones de S6.
  - La afirmación de ECHO-4.5 «aprende sin preentrenar» solo vale para la cifra sin S6.
- **ARC Prize.**
  - En Kaggle no hay internet durante la evaluación: la automejora ocurre **antes**, y lo aceptado
    viaja dentro de `echo-arc` como código.
  - Si ganamos, ese código también se publica en CC-BY 4.0.
- **Qué no afirma.** «Más listo» aquí significa «más tareas nuevas resueltas con conceptos
  verificados». No significa inteligencia general.

## Calendario

- Puede correr **en paralelo** con la iteración 3 de S4: esa usa CPU y juegos, y esta, GPU de Kaggle
  y rejillas.
- Tiene que cerrarse antes del examen de ECHO-4.5 (17 de octubre) para entrar en él.
- Estimación:
  - construir el bucle: 1 día;
  - paso 0: 1 sesión de Kaggle;
  - auditoría: medio día.

## Ajustes antes de medir (2026-09-26, fijados antes de la primera llamada real)

Se decidieron al construir el bucle (`seed/selfimprove.py`) y probarlo sin modelo. **No se ha
hecho ninguna llamada real todavía.**

1. **Modelo del paso 0:** `Qwen/Qwen2.5-Coder-7B-Instruct` en las 2×T4 de Kaggle (elección de Roger:
   Kaggle GPU gratis). Temperatura 0,7 y 700 tokens como máximo.
2. **Rondas:** cada ronda son 30 peticiones generadas en bloque. El aprendizaje de qué pedir se
   actualiza al final de cada ronda. Dentro de una ronda, las peticiones ya encargadas cuentan como
   intentos, para repartir los tipos.
3. **V3 por coste** (una prueba completa en 606 tareas son unos 50 min):
   - **criba:** la propuesta tiene que resolver al menos una de las tareas sobre las que se
     preguntó, con 150 expansiones;
   - **prueba:** después se cuentan las tareas nuevas en esas tareas más una muestra de 40 tareas
     no resueltas de A, con 400 expansiones. Hacen falta ≥ 2.
4. **V4:** se mide en una muestra fija de 50 tareas de B (por brazo, con semilla fija), no en las
   202.
5. **Métrica de reservadas:** «tareas reservadas» = `holdout_test_correct` con 400 expansiones, la
   misma cifra que dio 24 en S2. A1 exige ≥ 27.
6. **Punto de partida** (sandbox `echo45-s2v`): A 70/606 y B 14/202 resueltas
   (`lab/seed/s6/baseline.json`).
7. **Seguridad de las propuestas:**
   - código sin `import`, sin nombres con guion bajo y sin `open`, `exec`, `eval`…;
   - funciones básicas de Python restringidas;
   - 50 ms por llamada;
   - 1 GB de memoria por proceso.
8. **Reparto del trabajo:** los brazos FIJO y ECHO corren en dos notebooks de Kaggle separados. Las
   pruebas de reservadas de los cuatro brazos (SEMILLA, FIJO, ECHO y SIN FILTRO) se hacen aquí,
   con las operaciones descargadas.
9. **Cambios respecto al texto original:**
   - V2 no usa un subproceso por llamada, que haría la búsqueda inviable. Se usa ejecución
     restringida en proceso, con los límites del punto 7.
   - En este paso 0 no se aplica el sueño de S2 a las operaciones nuevas: entran como primitivas.
10. **Ajustes de interfaz tras la prueba corta en Kaggle** (10 propuestas, descartadas, no cuentan):
    - si el modelo no llama `op` a la función, se usa la última función de primer nivel;
    - se permite el nombre `_` (`for _ in range`), pero siguen prohibidos los nombres y atributos
      que empiezan por `__`;
    - se añaden `str`, `round`, `divmod`, `isinstance`, `frozenset`, `next` e `iter` a las
      funciones permitidas;
    - la generación va de 2 en 2 y reintenta de una en una si la GPU se queda sin memoria.

    Ninguno de estos cambios mira qué propuestas son buenas: solo arreglan el formato.
11. **Reanudación de FIJO (2026-09-26, tarde).**
    - El brazo FIJO se cayó en la llamada 183 de 300: una propuesta lanzó un `UnboundLocalError`
      que el aislamiento no capturaba.
    - Arreglo: cualquier excepción de una propuesta es un rechazo. No cambia qué se acepta; solo
      evita la caída.
    - FIJO se reanuda desde su diario (183 llamadas, 1 aceptada). ECHO se lanza ya con el arreglo.

## Recuperación técnica para el cierre (2026-09-27, antes de la campaña nueva)

Las primeras ejecuciones no completaron una comparación auditable: FIJO terminó con 263 veredictos
por una respuesta ausente que usó una variable sin inicializar; ECHO quedó marcado RUNNING con 78
veredictos visibles y sin avance entre consultas. Se conservan sus diarios/registros como antecedentes,
pero **no se mezclan con la comparación final**. FIJO ya había sufrido una reanudación que reiniciaba
el generador aleatorio y desplazaba las rondas; esa trayectoria no equivale a las diez rondas originales.

La campaña de cierre repite **300 propuestas por brazo, diez rondas de 30**, desde la misma base,
con el mismo modelo, temperatura, semillas, presupuestos de búsqueda y umbrales A1–A5. Los arreglos
se fijan antes de medir las reservadas y se aplican idénticamente a los dos brazos:

- Una respuesta ausente se registra como intento sin respuesta; también cuenta en el aprendizaje
  del tipo de petición. No se sustituye por una propuesta seleccionada.
- Se limita también la inicialización del código y la validación de la salida. Solo se permiten
  funciones en el nivel superior (más cadenas de documentación), sin decoradores ni valores por
  defecto calculados. No se permite capturar todas las excepciones con `except:`. La operación debe
  producir una rejilla rectangular de 1–30 filas y columnas, con colores 0–9, como pide la interfaz.
- Una operación que no puede ejecutarse en ninguna rejilla de la criba falla V2. No se interpreta
  la ausencia de ejecuciones válidas como prueba de determinismo.
- Los procesos verificadores se crean con `spawn`: no heredan el modelo ni su espacio de memoria
  antes de imponer el límite de 1 GB. La búsqueda sigue limitada por expansiones, sin cortar tareas
  por tiempo de reloj.
- Se guardan las respuestas del bloque, el estado de ECHO, el generador aleatorio y las propuestas
  pendientes antes de evaluar. La reanudación conserva las rondas y no regenera respuestas.
- El orden de las operaciones se reconstruye del diario, en orden de aceptación. Las huellas
  iniciales y finales quedan en los artefactos de cada brazo; no se modifica el código durante ellos.
- Se registran tokens de entrada y salida y coste de API de 0 USD. El wrapper devuelve el código
  de salida del experimento para que el estado de Kaggle no oculte otra caída.

Estas correcciones fortalecen V1/V2 y la custodia. Son una revisión declarada del ejecutor respecto
de las ejecuciones interrumpidas, no resultados de automejora. V3/V4 y A1–A5 se mantienen.

### Corrección de la línea base y del crédito V3 antes de la campaña final

La auditoría encontró que `bb43febb` y `d282b262`, acreditadas por la ejecución antigua a una
propuesta, ya eran resueltas por la biblioteca S2v sin esa propuesta, a 400 expansiones. El inventario
histórico de 70 tareas de A y 14 de B procedía del diario y no medía toda la biblioteca ampliada.
Se sustituye por una medición real de A606/B202, con la misma biblioteca y presupuesto.

V3 comprueba ahora también las tareas candidatas sin la nueva operación, con las mismas
400 expansiones; resta las que ya se resolvían y exige ≥2 tareas realmente nuevas. No cambia
el umbral. Los dos brazos finales usan el mismo paquete congelado y empiezan de cero: quedan
excluidas tanto las ejecuciones originales como el FIJO de recuperación anterior a este arreglo.

Se corrige P3 para cribar la tarea pendiente que aparece en su petición. Si todavía no hay
operaciones aceptadas para generalizar, P3 conserva el fallback P4 preexistente; el informe
declarará cuántas peticiones P3 utilizaron ese fallback.

V2 prueba determinismo en un proceso nuevo, limitado a 1 GB y 5 segundos de CPU, con una espera
máxima de 15 segundos para rechazar procesos que no devuelvan el resultado. La búsqueda aplica
las operaciones en sus trabajadores restringidos, con 50 ms por aplicación. Las anotaciones de
funciones solo admiten constantes o nombres simples para evitar ejecución arbitraria al definirlas.
Los manejadores de excepciones solo admiten los nombres `Exception`, `ValueError` e `IndexError`
(o tuplas de esos nombres); no pueden calcular un ancestro como `BaseException` para capturar
el plazo. Se prohíbe asignar atributos para que una función no guarde estado entre aplicaciones.
V4 y A1–A5 permanecen iguales. Esta revisión sustituye las descripciones anteriores del aislamiento
de V2 y del inventario inicial; se fija antes de generar los resultados de los brazos finales.

Custodia y decisiones: `ECHO45-S6-RECOVERY-NOTES.md`. Fuente y resultados finales:
`lab/kaggle/s6-final-20260927/` y `lab/seed/s6-final-20260927/`.
