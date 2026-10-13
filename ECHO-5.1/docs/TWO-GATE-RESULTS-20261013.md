# Dos puertas con 14B · resultados de desarrollo

**Veredicto: el flujo de reparación y validación funciona, pero no se demuestra
superioridad de E.** S, I2, F y E empatan en 2/3 tareas aceptadas. ECHO-5.1
continúa abierto. Rama local `research/echo-5.1-pcworld1`; sin publicación ni push.

Implementación medida: commit `2b71b1a`, contrato `0.5.0-development` y plan
[TWO-GATE-PILOT-20261013.md](TWO-GATE-PILOT-20261013.md). Se congelaron las fuentes
antes del lanzamiento y se verificaron sus hashes después. No hubo cambios de
política, presupuestos, oráculos ni código durante el piloto.

## Matriz completa

Tres variantes de familias conocidas, semilla 47, doce episodios en orden
contrabalanceado. No son tres familias nuevas ni un examen independiente.

| Brazo | Registros | Rutas | Paginación | Aceptadas | Tokens observados | Tiempo de episodios |
|---|---|---|---|---:|---:|---:|
| S | No | Sí | Sí | 2/3 | 5.212 | 121,680 s |
| I2 | No | Sí | Sí | 2/3 | 2.352 | 54,874 s |
| F | No: cobertura incompleta | Sí | Sí | 2/3 | 22.378 | 163,124 s |
| E | No: cobertura incompleta | Sí | Sí | 2/3 | 20.372 | 147,145 s |

Se consumieron 50.314 tokens en 48 llamadas al modelo. Todos tienen uso observado;
no hay reservas cobradas por respuestas de uso desconocido. E utilizó un 8,96 %
menos de tokens que F, pero ambos gastaron mucho más que S/I2 con idéntica
aceptación. Es una diferencia descriptiva de este piloto, no evidencia general
de eficiencia o superioridad causal. I2 fue el más barato en esta muestra.

## Qué ocurrió en cada mecanismo

**Rutas:** E y F produjeron inicialmente `//l/c` para el ejemplo público `/l/c`.
Ese fallo público activó una reparación, comprobada antes de reanudar críticas.
E pasó `dotdot-cancellation` y `root-boundary`; F pasó ambas categorías después
de tres sondeos duplicados en `repeated-separators`. Ambos pasan los cuatro casos
finales de esta variante. E gastó 4.349 tokens y F 9.050. S e I2 también pasan.

Por tanto, aquí hay reparación real seguida de dos categorías verificadas,
pero **el crítico no descubrió el defecto que originó la reparación**. No se
atribuye ese descubrimiento al crítico ni a CAM. El contrato anterior ya
prohibía atravesar la raíz; la nueva formulación lo hace más explícito para
todos los brazos. El caso expuesto en el diagnóstico anterior ya es desarrollo.

**Registros:** el crítico de E sí descubrió un contraejemplo de claves repetidas.
E produjo una reparación comprobada en un intento y reprodujo ese sondeo sobre
el parche. Después, las cinco respuestas restantes volvieron a proponer listas
largas pese a pedir entrada vacía o de un elemento: dos duplicados y tres errores
de categoría. No consiguió la segunda categoría. F también retuvo y reparó un
contraejemplo, en dos intentos, pero obtuvo solo una categoría soportada; tuvo
tres errores de categoría y dos duplicados.

Ambos alcanzaron seis llamadas al crítico. El bucle interno intentó reservar
otra llamada y la contabilidad la rechazó con `BudgetExceeded: critic_calls
reservation exceeds remaining budget`. Esa séptima llamada **no se ejecutó**.
El episodio terminó sin evaluación final. No se cuenta como timeout de GPU,
fallo del proveedor ni demostración de que el parche sea incorrecto en esos
casos finales: faltó completar el protocolo y esa evidencia no se obtuvo.

**Paginación:** los cuatro brazos pasan los cinco casos finales, sin reparación
guardada. Más agentes no aportaron aciertos adicionales en esta tarea.

## Comparación sobre casos comunes

| Familia | S | I2 | F | E |
|---|---:|---:|---:|---:|
| Registros | 2/4 | 2/4 | No evaluados al finalizar | No evaluados al finalizar |
| Rutas | 4/4 | 4/4 | 4/4 | 4/4 |
| Paginación | 5/5 | 5/5 | 5/5 | 5/5 |

Esta tabla solo usa los mismos casos públicos y finales de cada tarea. No
convierte la falta de evaluación de Registros en «0/4 del código», ni vuelve a
ejecutar fuera del presupuesto esos parches para elevar retrospectivamente su
nota. La aceptación del protocolo se conserva separada de calidad observada.

## Infraestructura y auditoría

- 12/12 episodios conservados; auditoría válida de 580 recibos, sin discrepancias.
- `destroyed == 0`. Ningún aceptado falló los casos finitos ejecutados; esto no
  implica cero alucinaciones universales ni aislamiento inexpugnable.
- 198 pruebas PCWorld pasan (71,960 s), incluidas diez pruebas del transporte:
  capacidades separadas, rutas exactas, caducidad, replay, límites y worker.
- Notebook privado `rogeernavarro/echo51-two-gate14b-20261013`, versión 1,
  confirmado `COMPLETE`; solo inferencia, ningún programa candidato ejecutado allí.
- Qwen2.5-Coder-14B-Instruct Q4_K_M y llama.cpp b11577 fijados como en el diagnóstico
  anterior. 49/49 capas en GPU, 9.161 MiB en CUDA0 (105 MiB en la segunda T4).
- Preparación: 195,131 s. Worker total: 685,926 s, unos 11 min 26 s.
- 144 solicitudes de transporte, todas HTTP 200: plantilla, tokenización e
  inferencia para las 48 llamadas. Sin timeout de proveedor en este piloto.
- Cuota observada: 25,74 → 25,54 horas restantes; diferencia aproximada de 0,20 h
  por la resolución del contador. No confundirla con una medición eléctrica.
- Worker cerrado normalmente; supervisor, broker y túnel detenidos. Las claves
  efímeras no se incorporan al repositorio. Todo el código candidato se ejecutó
  aquí en el runtime hermético y bajo Bubblewrap/cgroups.

El túnel temporal se utilizó conforme al mecanismo de
[Quick Tunnels de Cloudflare](https://developers.cloudflare.com/tunnel/get-started/):
solo el broker autenticado, sin shell ni acceso a archivos. No es un servicio
persistente ni una nueva frontera de ejecución para ECHO.

## Evidencia local

- `ECHO-5.1/artifacts/two-gate14b-pilot-20261013/`: resultados, recibos, snapshots,
  manifiestos, runtime, diarios, `audit.json` y `summary-by-arm.json`.
- `ECHO-5.1/artifacts/two-gate-control-20261013/`: hashes congelados, prueba de GPU
  lista y registro de transporte. Contiene claves privadas; no publicar la carpeta.
- `ECHO-5.1/artifacts/kaggle-two-gate14b-output/`: informe del worker y logs GPU.
  El input del transporte contiene una credencial efímera; tampoco publicarlo.
- SHA-256 de `result.json`:
  `4b54d1f29b5fb8d4d01a76c7ced634d05b694bc48591c29b5dccc68203bec47c`.
- SHA-256 de `audit.json`:
  `198a885a95c9e34d9568244387276c2dfd36b74852b5e253223dcde0c392a766`.

## Pendiente después del piloto

1. Mejorar la obediencia del crítico a la categoría pedida, conservando la
   validación externa y controles iguales. La repetición de listas de varios
   elementos cuando se solicita vacío/singleton está documentada, no es una
   hipótesis sobre falta de parámetros.
2. Terminar las críticas de forma explícita cuando se agota su cuota, antes de
   intentar otra reserva. Si queda presupuesto de verificación, separar esa
   evaluación del rechazo por cobertura; nunca inventar una segunda categoría.
3. Medir sobre tareas/familias independientes y dimensionar la confirmación.
   Ni el empate ni un eventual resultado favorable con tres tareas cierran 5.1.

No se lanzó otra campaña para buscar un resultado favorable. El resultado
negativo sobre superioridad se conserva junto al progreso de implementación.
