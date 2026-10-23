# ECHO-4.5 · S6-A · resultados y cierre: ROJO

Estado: **S6-A terminado y auditado; ROJO**. La condición de éxito era A1 ∧ A2 ∧ A3 ∧ A4 ∧ A5;
no se cambian los umbrales para cerrar. Fecha de generación: 2026-09-27T10:53:19.676547+00:00.

## Comparación en las mismas 201 tareas reservadas

| Brazo | Operaciones nuevas en el vocabulario | Tareas con test correcto |
|---|---:|---:|
| SEMILLA | 0 | 24/201 |
| FIJO | 0 | 24/201 |
| ECHO | 0 | 24/201 |
| SIN FILTRO | 244 | 25/201 |

FIJO y ECHO completaron **300 intentos cada uno, diez rondas de 30**, con
`Qwen/Qwen2.5-Coder-7B-Instruct`, temperatura 0,7, máximo 700 tokens, semilla `s6`, presupuesto
de búsqueda de 400 expansiones y la base `echo45-s2v`. SIN FILTRO reutiliza las respuestas de ECHO
que superaron V1/V2; no tiene llamadas adicionales. SEMILLA se midió otra vez y reprodujo 24/201.

El bucle verificado **no mejoró la semilla**, pedir de forma personalizada no superó a FIJO,
y verificar utilidad no superó al brazo SIN FILTRO. Tampoco mejoró la tasa de aceptación entre
las dos mitades. La integridad y la reconstrucción sí pasaron. Este resultado rojo corresponde
a este ejecutor, modelo y presupuesto; no responde por todos los modelos o filtros posibles.

## De dónde viene la tarea adicional de SIN FILTRO

Conservó las 24 soluciones de SEMILLA y añadió `4347f46a`. El programa usa una sola operación,
`s6_echo_f5e737ea`, escrita en la petición **182, P2**. La función `highlight_edges` conserva los
bordes y los píxeles vecinos de otro color; convierte en cero los interiores uniformes.
Resolvió los ejemplos y el test reservado en **una expansión**.

V3 la había rechazado con «solves none of the tasks it was asked about»: no resolvió las tareas
`a79310a0`, `bcb3040b` y `6ad5bdfd` en la criba de 150 expansiones. No llegó a la comprobación
de dos mejoras en A ni a V4. El filtro descartó así una operación que sí transfirió a una reservada.
La explicación se obtuvo después de congelar las 600 propuestas y medir los cuatro brazos;
no se usó para modificar las peticiones, los veredictos ni los umbrales.

Proveniencia verificable: `lab/kaggle/s6-final-20260927/unfiltered-gain-provenance.json`.

## Criterios fijados antes de medir

| Criterio | Resultado |
|---|---|
| A1 | NO PASA |
| A2 | NO PASA |
| A3 | NO PASA |
| A4 | NO PASA |
| A5 | PASA |

A1 exige ECHO ≥27; A2, ECHO > FIJO; A3, mayor tasa de aceptación en rondas 6–10 que en 1–5;
A4, SIN FILTRO < ECHO; A5, integridad y reconstrucción.
ECHO aceptó 0/150 propuestas en la primera mitad y 0/150 en la segunda.

## Operaciones aceptadas

| Brazo | Intento | Petición | Operación | Tareas nuevas de A |
|---|---:|---|---|---|
| — | — | — | Ninguna | — |

No hubo operaciones aceptadas ni archivos de operaciones nuevas para FIJO o ECHO. Los diarios
`lab/seed/s6-final-20260927/{fijo,echo}/journal.jsonl` conservan la petición exacta, respuesta,
código y motivo de rechazo de cada intento.

| Brazo | Rechazadas en V1 | Rechazadas en V2 | Rechazadas en la criba V3 |
|---|---:|---:|---:|
| FIJO | 33 | 59 | 208 |
| ECHO | 6 | 36 | 258 |

Todas las propuestas que superaron V1/V2 fallaron la criba de las tareas de su petición. V4
no llegó a ejecutarse para ninguna candidata: esta campaña no aporta una prueba empírica de
su capacidad para detectar regresiones. ECHO hizo 75 peticiones etiquetadas de cada tipo;
las 75 P3 utilizaron P4 porque todavía no había una operación aceptada que generalizar.

## Recuperación y límites declarados

Las ejecuciones originales de Claude se conservaron como antecedentes: FIJO terminó en 263/300,
con una operación aceptada, y ECHO mostró 78 veredictos antes de dejar de avanzar. Se excluyeron
de la comparación final. Esta campaña repitió los dos brazos desde la misma base con el ejecutor
corregido y congelado. La revisión técnica se fijó en
`ECHO45-S6-AUTOMEJORA-DESIGN.md`, sección «Recuperación técnica para el cierre».

Se corrigieron las respuestas ausentes, el límite de ejecución en la inicialización y validación
de las operaciones, la creación de verificadores sin heredar el modelo GPU y la reanudación exacta.
Se reforzó V1/V2 y la custodia. La auditoría comprobó que la única propuesta aceptada del FIJO
antiguo recibió crédito por dos tareas que la base ya resolvía sin ella. Se midió de nuevo la línea
base en A606/B202 y V3 exige dos soluciones que no se obtengan sin la candidata a las mismas
400 expansiones. También se descartó el FIJO de recuperación anterior a ese arreglo. Los primeros
intentos de arranque fallaron al extraer el paquete, antes de llamar al modelo. V4 y A1–A5 conservaron
sus umbrales. Ambos brazos finales utilizaron literalmente el mismo ejecutor y línea base congelados.

P3 verifica la tarea pendiente mostrada en su petición. Cuando no hay operaciones aceptadas que
generalizar, utiliza el fallback P4 preexistente: 75 peticiones etiquetadas P3 lo usaron.
SIN FILTRO incorpora una sola vez cada código distinto que supera V1/V2; las propuestas repetidas
tienen el mismo nombre y constituyen una sola operación en el vocabulario.
La medición inicial completa, con la biblioteca base intacta, dio 73/606 en A y 16/202 en B.

Durante la primera medición de SIN FILTRO una señal de plazo se escapó de la limpieza del
temporizador y mató un trabajador; el pool quedó esperando su resultado. Antes de obtener
la cifra de ese brazo se añadió `probe_driver.py`, que convierte también esa señal en rechazo
de la aplicación y restaura temporizador/manejador. Conserva las operaciones, su orden y las
400 expansiones. Los diarios y archivos protegidos de las campañas quedan intactos. La medición
válida de SIN FILTRO y los cuatro replays usan este mismo envoltorio, congelado por SHA256 en
`measurement-profile.json`. No se presenta el primer intento atascado como una medida completa.

Este resultado corresponde a este modelo y presupuesto. ARC tiene tareas públicas que el modelo
puede haber visto al entrenarse. El proponente recibió solo ejemplos de tareas de A; no se le
entregaron las reservadas ni las evaluaciones selladas. Las operaciones son código escrito por
el modelo, no aprendizaje del núcleo sin preentrenamiento. La comparación no demuestra
inteligencia general ni conciencia.

## Auditoría, coste y artefactos

- 300 entradas por brazo, rondas correctas, cadenas de hashes válidas y propuestas referidas solo a A.
- Huellas protegidas iniciales y finales idénticas en cada campaña, comparadas con la fuente congelada.
- Directorios de operaciones coherentes con cero aceptaciones; SIN FILTRO reconstruido del código
  de las propuestas que superaron V1/V2, sin llamadas adicionales.
- No hubo operaciones aceptadas sobre las que repetir V3/V4; el contrafactual que invalidó el
  crédito antiguo quedó registrado antes de generar los brazos finales.
- Biblioteca reconstruida desde los diarios, mediciones repetidas en procesos nuevos y **cuatro
  informes idénticos byte a byte**. No se observó un escape de las restricciones de las propuestas.
- **Coste de API: 0 USD**, GPU gratuita de Kaggle. El informe incluye intentos por operación aceptada
  y tokens. Las entradas cuentan tokens antes del truncamiento a 6000; las salidas se retokenizan
  desde el texto decodificado, por lo que no se presentan como contabilidad exacta del generador.

Con cero aceptaciones, los costes e intentos **por operación aceptada no están definidos**
(`null` en el informe); no se les atribuye una eficiencia de cero. Las doce pruebas del ejecutor
y del manejo del temporizador pasaron con Python del sistema.

Informe verificable: `lab/seed/s6-final-20260927/audit.json`.
Diarios, huellas y recibos: `lab/seed/s6-final-20260927/{fijo,echo}/`.
Mediciones: `probe-*.json` y `replay-probe-*.json` en ese directorio.
Fuente congelada, notebooks privados y herramientas de reproducción:
`lab/kaggle/s6-final-20260927/`. Huella del paquete: `c295e291fb1cc15bac76acbadf1b27ed07621a0c817244cbbd4f61f8d41a6313`.

Notebooks: `navywakura/echo45-s6-fijo-final` y `navywakura/echo45-s6-echo-final`.

**S6-A queda cerrado con este resultado.** La fase B de juegos y el paso de pago con un modelo
frontier son experimentos posteriores; no forman parte de esta campaña.
