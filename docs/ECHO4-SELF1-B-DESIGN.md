# E4-SELF-1 / SELF-B — hipótesis y ensayos discriminantes v1

2026-09-21. Continuación autorizada del roadmap. Contrato previo a ejecutar
este banco. SELF-A y todos sus archivos sellados permanecen intactos.
**No cierra SELF-1**: recuperación conductual y protección selectiva de T
siguen perteneciendo a SELF-C y al examen final posterior.

## Qué se añade y qué se supone

Un diagnóstico por descarte de hipótesis, no un clasificador entrenado con
las etiquetas del censo. Recibe la referencia nominal sellada de SELF-A,
WSP y recibos de ejecución/restauración. No recibe el cuerpo exacto, fallo,
calor real, familia o fila del evaluador. Mantiene todas las posibilidades
compatibles; solo atribuye si **todas** coinciden en nominal/propia/externa/
mixta. Cero candidatos, varios orígenes o recibos inválidos → desconocido.

**Prior físico explícito, no aprendido:** transición nominal WORLD-1 y
encoder originales conocidos; canales H/temperatura independientes; cada
canal acoplado o siguiendo wait; perturbación externa entre -16,-4,0,+4,+16,
una vez en t=1 de cada ensayo restaurado. Parámetros constantes entre ensayos.
Las hipótesis usan la función pura existente, no el estado del ejecutor.
Esto es diagnóstico basado en modelo dentro de esa familia, no causalidad
general ni aprendizaje autónomo de las leyes físicas. Una fuerza externa
dependiente de la acción podría imitar un actuador averiado y queda fuera.

Todos los estados iniciales vivos compatibles con el WSP se consideran:
no se entrega al consumidor el rango exacto del banco. Las observaciones
nominales descartan estados, sin rellenar H/theta con su valor verdadero.
La calibración se supone nominal y las restauraciones conservan exactamente
el estado inicial oculto entre la referencia y los ensayos posteriores;
lo garantiza el ejecutor y lo comprueba el auditor, no la igualdad de WSP.

## Más referencia y más intervención

Además de los ocho pares por acción de SELF-A se registra **wait durante
ocho ticks antes de introducir la perturbación**, siempre de forma explícita
y supervisada. Así se mide mejor la fase dentro de las bandas. No se inventa
retrospectivamente una observación ni se repite una referencia después del fallo
como si fuera nominal. Ablación: retirar esa referencia adicional.

Catálogo fijo de seis secuencias, acciones 0/1/2 originales:

1. `22222222` — esperar ocho ticks.
2. `12222222` — enfriar una vez y observar.
3. `0222` — cargar una vez y observar, horizonte cuatro.
4. `22122222` — enfriar después de dos esperas.
5. `01010101` — alternar carga/enfriamiento.
6. `22220101` — esperar cuatro y alternar.

Cada secuencia parte de una restauración declarada. No son rescates dentro
de una vida autónoma. Antes de ejecutarla se predicen **todas** sus salidas
por hipótesis. Una secuencia que puede alcanzar terminalidad bajo alguna
hipótesis retenida no es admisible. El gate original sigue pudiendo vetar;
un veto o ejecución no confirmada invalida el ensayo, no prueba fallo corporal.

Selección: minimizar lexicográficamente el peor número de clases causales
compatibles tras la secuencia, el peor número de estados candidatos y su
longitud; desempate por índice fijo. Son enteros, no probabilidades ni
entropía fingida. No repetir una secuencia ni superar seis ensayos/48 acciones.
Cuando solo quede una clase se detiene. Si no hay un ensayo admisible, se
detiene con lo que se sabe, sin inventar una cuarta acción física.

## Presupuesto e integración

H y temperatura se factorizan por la independencia explícita del prior:
máximo 64 candidatos H y 160 candidatos térmicos, producto implícito de
hasta 10.240 estados; no duplicar CAM/T/Q ni materializar ese producto.
Las previsiones pendientes tienen como máximo ocho códigos por candidato.
Se guarda el conjunto de seis ensayos usados y un solo ensayo pendiente;
no se retiene una historia creciente dentro del consumidor.

Integración opt-in nueva encima de SelfAgent. Solo propone ensayos de
diagnóstico en este banco supervisado. No cambia aún la política ordinaria,
el loop histórico ni sus escrituras T. Las etiquetas son hipótesis
condicionadas al modelo, jamás `has_fact=1` en CAM.

## Banco y criterios de este entregable

Se vuelve a usar el censo de desarrollo de SELF-A: H=29..40, temperatura
40..72, cuatro acoplamientos y cinco pulsos, **7.920 condiciones**. Es un
banco público conocido, no B/C reservado. Smoke: H=30/38 y temperatura=48/50/52.
Se conservan todos los desconocidos y causas por separado.

Antes de ejecutarlo se fijan estos criterios diagnósticos:

- Cero atribuciones erróneas en el dominio; correcto ≥75% total y ≥50%
  en cada una de las cuatro causas. Desconocido no cuenta como acierto.
- El testigo SELF-A de H=37/temperatura=65 debe distinguir las cuatro causas
  con la nueva evidencia; si no, conservar el resultado y no afirmar resolución.
- Cero terminalidades en ensayos seleccionados, veto respetado, memoria
  acotada, fuentes nominales/CAM intactas y cero hechos/córtex/destrucción.
- Previsiones registradas antes de ejecutar, consumo solo del plan pendiente;
  IDs, recibos de restauración, gates, tiempos, secuencias y WSP validados.
- Controles ejecutados: solo wait ocho ticks, sin referencia larga y orden
  fijo seguro del catálogo. Publicar precisión y coste de todos. No exigir
  una ventaja inventada sobre el orden fijo; si hay empate, informarlo.
- Pruebas de contradicción, fuera del prior detectable, ambigüedad, falta
  de referencia, presupuesto, saturación/safety y alteración de evidencia.
- Replay en proceso nuevo y revalidación de SELF-A/BOUNDARY/SENSATION.

Si falla algún criterio, mantener este desarrollo abierto sin retocar
umbrales para hacerlo pasar. Aunque pase, `self1_green=false`: faltan
recuperación, conservación selectiva del conocimiento y examen final.

Hardware después del software; METAVERSE-1 permanece último.
