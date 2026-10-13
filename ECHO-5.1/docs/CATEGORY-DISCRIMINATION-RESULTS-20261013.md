# Catálogo de cinco categorías y seis familias · resultados

**E=8/12, F=8/12, S=6/12, I2=6/12.** E y F reparan Registros en las dos
variantes; ninguno resuelve por completo CSV ni Dependencias. La ampliación
no desempata E frente a F en aciertos. ECHO-5.1 sigue abierto para confirmación
y atribución de mecanismos, aunque la ejecución y su auditoría están completas.

Implementación local `e1a8030`, contrato `0.7.0-development`,
[plan previo](CATEGORY-DISCRIMINATION-PLAN-20261013.md). Se conservaron los
27 archivos congelados sin cambios durante la medición. No se hizo push ni
se publicó el notebook. Las puntuaciones de pilotos anteriores no cambian.

## Diseño ejecutado

48 episodios, dos variantes de cada una de seis familias conocidas, semilla 47;
S/I2/F/E en el orden contrabalanceado existente. `expanded-v1` añade dos
categorías válidas por familia. F usa una permutación fijada por SHA-256 con
semilla 20261013 y la identidad de tarea; no se pusieron deliberadamente
categorías irrelevantes primero. E puede priorizar señales del AST y recupera
observaciones/rechazos de CAM; sin señal usa el mismo orden de respaldo.

No son familias nuevas ni un benchmark externo. Estas variantes cambian valores
de tareas ya expuestas. Comparten techo de 25.000 tokens,50 herramientas, 12
llamadas LLM,seis críticas, 128 fuel, 300 s CPU y 900 s de plazo por episodio. El
consumo real no está igualado: S/I2 gastan bastante menos. Se mantienen modelo,
oráculos, rootfs y política de aceptación común. Cobertura no equivale a éxito.

## Aciertos y coste

| Brazo | Aceptadas | Tokens observados | Llamadas LLM | Herramientas | Tiempo de episodios |
|---|---:|---:|---:|---:|---:|
| S | 6/12 | 20.612 | 32 | 252 | 420,051 s |
| I2 | 6/12 | 9.428 | 24 | 238 | 270,613 s |
| F | 8/12 | 66.993 | 59 | 376 | 668,669 s |
| E | 8/12 | 54.310 | 55 | 390 | 630,291 s |

| Familia | S | I2 | F | E |
|---|---:|---:|---:|---:|
| Intervalos | 2/2 | 2/2 | 2/2 | 2/2 |
| Registros | 0/2 | 0/2 | 2/2 | 2/2 |
| Rutas | 2/2 | 2/2 | 2/2 | 2/2 |
| CSV | 0/2 | 0/2 | 0/2 | 0/2 |
| Paginación | 2/2 | 2/2 | 2/2 | 2/2 |
| Dependencias | 0/2 | 0/2 | 0/2 | 0/2 |

Emparejamiento E−S y E−I2: dos victorias, diez empates y ninguna pérdida.
Ambas victorias proceden de Registros; no son dos familias independientes.
E−F: doce empates en aceptación. La ganancia descriptiva E−S es 16,67 puntos
porcentuales en esta muestra, no una estimación confirmada de transferencia.

E consume 18,93 % menos tokens que F: 12.683 tokens de diferencia. Sin embargo,
10.485 de esa diferencia (82,67%) proceden de un solo episodio fallido de CSV,
donde F intenta y comprueba más reparación que E. No se atribuye ese ahorro
causalmente al router ni se omite el episodio como un valor atípico. E utiliza
más herramientas (390 frente a376) y más trabajo de recuperación de memoria
(1.091 frente a617 unidades de búsqueda registradas). No hay una mejora
uniforme de todos los costes. I2 sigue siendo el más barato, con menos aciertos.

Total: 151.343 tokens, 170 llamadas LLM. Todas tienen uso observado; no hay cargos
por respuestas de uso desconocido. Los techos originales permanecen intactos.

## Diagnóstico por mecanismo

**Registros:** en ambas variantes, E y F descubren una refutación por claves
duplicadas, reparan en un intento y pasan todos sus casos finales, incluido el
testigo retenido (5/5). S/I2 fallan dos de los cuatro casos comunes. Es evidencia
del flujo completo en estos ejemplos. No demuestra que todo agente único sea
incapaz de repararlos ni identifica por separado el efecto de CAM.

**Rutas:** todos pasan. Las reparaciones de E/F parten del fallo del ejemplo
público, no de un descubrimiento del crítico. F en la segunda variante termina
con una sola categoría soportada y etiqueta `GRADUADO_POR_SUPERVIVENCIA`; después
pasa los 4/4 casos finales. Aquí sí se ejercita en GPU la evaluación de un
candidato con cobertura incompleta, a diferencia del piloto 0.6. La etiqueta
sigue llevando `verified: false`; la aceptación viene del examen finito posterior.

**CSV, variante 00:** los críticos de E/F copian el enunciado en `input` seis
veces. Es una cadena CSV admisible, pero no pertenece a las categorías pedidas.
Los seis sondeos de cada brazo son rechazados; no se retiene refutación y ambos
fallan 4/5 casos finales. La corrección de memoria evita repetir seis veces la
misma categoría: pasan a otra tras tres rechazos, sin resolver el problema del
contenido generado.

**CSV, variante 01:** ambos críticos vuelven a copiar el enunciado, pero esta
vez cumple `whitespace-newline` y refuta realmente el tratamiento de espacios.
No se le concede mérito de deliberación por ello; sí hay un testigo válido.
E intenta dos reparaciones y ambas se rechazan por romper el caso base; conserva
el candidato anterior y pasa 1/6 casos finales completos. F rechaza el primer
parche y el segundo corrige el testigo y el caso base, pero no el algoritmo CSV
completo. Antes de agotar herramientas, la evaluación final ya refuta dos casos
de comillas. Obtiene 3/5 de los casos ejecutados y queda el sexto sin ejecutar.
Por tanto, **F no fue rechazado solo por presupuesto**: ya había errores finales
observados. Su etiqueta de graduación nunca se convirtió en un pase falso.

El prompt actual de `provider.py` inserta la descripción textual del dominio
como valor ilustrativo de `format.input`. Es una hipótesis concreta para explicar
el copiado; requiere un ensayo separado, no se cambió durante esta campaña.
S también intenta reparar CSV mediante autorrevisión en ambas variantes y falla;
no es correcto describirlo como un brazo sin capacidad de reparación.

**Dependencias:** hay categorías válidas pero sondeos poco discriminantes.
En la primera variante, por ejemplo, E comprueba un ciclo y una cadena cuya
dirección coincide con el orden alfabético. El candidato pasa esos ejemplos y
falla los casos reservados que requieren otro orden o manejan aristas repetidas.
F también pasa sus sondeos sin descubrir el defecto. Ambos fallan la tarea en
las dos variantes. Elegir una etiqueta pertinente no garantiza generar un
contraejemplo útil dentro de ella. No equivale a demostrar ausencia de bugs.

**Intervalos y Paginación:** todos pasan ambas variantes. Más coordinación no
añade aciertos en estas tareas de desarrollo.

## Sondeos y correcciones previas al lanzamiento

| Métrica | F | E |
|---|---:|---:|
| Llamadas al crítico | 41 | 37 |
| Refutaciones observadas, sin contar replays | 3 | 3 |
| Sondeos duplicados rechazados | 10 | 5 |
| Categoría incorrecta | 11 | 10 |
| Entrada fuera de dominio | 0 | 1 |
| Intentos de reparación guardada | 6 | 6 |
| Episodios con error de presupuesto | 1 | 0 |

Se corrigió, antes del ensayo, un fallo descubierto en revisión: E consultaba
solo observaciones y olvidaba las críticas rechazadas registradas como fallos.
La prueba real de episodio reprodujo seis intentos de la misma categoría en E,
frente a tres más tres en F. Ahora E recupera ambos tipos en una sola consulta
CAM cobrada y respeta los reintentos por categoría. No se reescriben resultados
anteriores para atribuirles esa corrección.

La auditoría ampliada comprueba categorías, orden de elección, secuencia de
reintentos, propiedades observadas, propuesta crítica originaria o replay
autenticado y novedad del input. Las firmas por sí solas no bastan para declarar
correcta una respuesta. El catálogo anterior permanece disponible por defecto;
el nuevo se seleccionó explícitamente y figura en `tasks.json`.

## Verificación y recursos

- 214 pruebas PCWorld pasan en 83,441 s antes de congelar el código.
- 48/48 episodios conservados; auditoría válida de 2.362 recibos, repetida
  después de terminar, sin discrepancias. `destroyed == 0` en todos.
- Un error de episodio: `BudgetExceeded: tools reservation exceeds remaining
  budget`, en CSV01 de F. Se conserva como no aceptado. Sin timeouts ni errores
  de proveedor. No confundir evidencia válida con tarea resuelta.
- Notebook privado `rogeernavarro/echo51-categories14b-20261013`, versión 1,
  `COMPLETE`. Solo inferencia remota; los candidatos se ejecutan localmente
  en Bubblewrap/cgroups con rootfs fijado. Los oráculos no se suben a Kaggle.
- Qwen2.5-Coder-14B-Instruct Q4_K_M y llama.cpp b11577 fijados como antes;
  49/49 capas en GPU, 9.161 MiB en CUDA0 y 105 MiB en la segunda T4 al cargar.
- Preparación: 236,311 s; worker: 2233,221 s (37 min 13 s). No fueron 25 min.
- 510 solicitudes de transporte, todas HTTP 200, para 170 llamadas LLM.
- Cuota observada: 25,33 → 24,71 h GPU: aproximadamente 0,62 h por la resolución
  del contador. Worker detenido normalmente; supervisor, broker y túnel inactivos.

## Evidencia local y estado

- `ECHO-5.1/artifacts/categories14b-pilot-20261013/`: resultados, recibos,
  snapshots, manifiestos, `audit.json` y `summary-by-arm.json`.
- `ECHO-5.1/artifacts/category-control-20261013/`: fuentes congeladas,
  parámetros de lanzamiento, GPU lista y transporte; contiene claves privadas.
- `ECHO-5.1/artifacts/kaggle-categories14b-output/`: informe y logs del worker;
  incluye input con credencial efímera del transporte apagado. No publicar.
- SHA-256 de `result.json`:
  `ef92fa86bc0904ea984dbd5d294ca1752ecc137909ff5991b3196519b18c898a`.
- SHA-256 de `audit.json`:
  `6b349ded16487862d0e2fddcd37d22442078581700537a9ac95001e1fd3998e3`.

```sh
python3 -I -B ECHO-5.1/scripts/run.py audit ECHO-5.1/artifacts/categories14b-pilot-20261013
```

H1 tiene apoyo descriptivo frente a estos controles bajo un techo común; no
confirmación general, ni comparación con consumo real igualado. H4 no se
desempata en aciertos. El ahorro observado necesita repetición y ablaciones:
E/F difieren también en recuperación de memoria y coordinación. Las variantes
correlacionadas y el cambio conjunto de catálogo, AST y memoria limitan la
atribución causal. No se etiqueta la ampliación como «verde definitivo».

El siguiente diagnóstico acotado sería separar esquema de ejemplo de salida
en el prompt del crítico y comprobar generación de CSV válidos, además de
casos de grafos que varíen el orden de nombres dentro de cada categoría. Para
eficiencia, estudiar la reserva de herramientas para verificación antes de
seguir sondeando. Son propuestas futuras, no cambios medidos en esta tanda.
Después: ablaciones y familias independientes con contrato nuevo. S6 aplazado;
sin nueva campaña automática, publicación ni push.
