# EGO-MEMORIA-3E → ARC · protocolo pendiente

29 de septiembre de 2026. Preparación autorizada junto con el comparador ARC.
**Diseño documentado; adaptador y ensayo de transferencia todavía pendientes.**
No añade nuevos requisitos retroactivos al examen de aldea, ya cerrado VERDE.

La aldea demuestra que ECHO aprende cuándo verificar y conservar pruebas útiles,
y que sus recuerdos afectan a decisiones posteriores. No demuestra que pueda
usar ese diario para resolver una rejilla. Analogía: aprender a llevar una
libreta de recibos no enseña por sí solo a utilizarla para montar una máquina.

## Trabajo necesario antes de medir

1. Definir un adaptador entre observaciones ARC y entradas del diario existente:
   identidad del episodio, hipótesis de programa, evidencia reproducible de las
   demostraciones, acción ejecutada y coste observado. Sin otro bus de pensamiento.
2. Asegurar que el controlador realmente consulta esos recuerdos para decidir
   qué propuesta verificar o reutilizar. Guardar un log que nadie consulta no
   cuenta como memoria útil. El actor actual de aldea elige verificar/escribir;
   no tiene directamente la interfaz de acciones de ARC.
3. Fijar qué estado se conserva entre episodios, el límite de almacenamiento,
   el coste de leer/escribir/verificar y cómo se representa una contradicción.
   No se copian hechos privados de la aldea como si fueran hechos ARC.
4. Medir primero secuencias sintéticas de desarrollo con relaciones repetidas,
   distractores, cambio de colores/posiciones y reglas que a veces cambian.
   La única prueba disponible al agente procede de demostraciones u observaciones
   autorizadas; nunca del output de test reservado.

## Comparación propuesta

El contrato de ejecución deberá congelarse **antes** de medir, incluyendo
adaptador, semillas, presupuestos y criterios numéricos concretos. Esta propuesta
no abre ni asigna todavía una reserva.

| Brazo | Diferencia experimental |
|---|---|
| Memoria transferida | Conserva el aprendizaje autorizado entre episodios |
| Memoria reiniciada | Misma arquitectura, presupuesto e historial de entrenamiento; estado episódico vacío al evaluar |
| Recuerdos formativos retirados | Ablación de evidencia cuya consulta quedó registrada |
| Control de retirada | Retira igual cantidad de recuerdos no formativos, con regla fijada previamente |

La selección de recuerdos formativos se fija por trazas de entrenamiento,
no por las respuestas reservadas. Se emparejan tareas, orden y semillas; se
registran lecturas y costes reales. El proceso de memoria vacía conserva una
oportunidad equivalente de cómputo: no se le compara con un agente deliberadamente
sin presupuesto. No se premia escribir; se mide su utilidad posterior.

Solo se afirmará **transferencia a estas familias** si mejora el acierto o
reduce el coste preservando aciertos, la ablación de recuerdos relevantes
elimina esa ventaja más que la retirada control, y la auditoría reproduce
decisiones, procedencia y presupuesto. Un primer resultado de desarrollo no
certifica ARC-1/2/3. La atribución de mejora en ARC exige la comparación posterior
del candidato integrado y una confirmación independiente sin reutilizar la
reserva para ajustar el adaptador.

## Estado verificable

- ✅ EGO-MEMORIA-3E: M1–M5 16/16; M6 reconstruye los dieciséis ensayos.
- ✅ Comparador de diferencias, referencias ARC y diagnóstico por capacidades preparados.
- ❌ Adaptador de memoria al solver/controlador ARC e integración del aprendizaje.
- ❌ Desarrollo emparejado y ablaciones de memoria.
- ❌ Contrato de ejecución numérico, congelación, confirmación y auditoría.

[Examen de memoria ya cerrado](ECHO45-EGO-MEMORIA3-RESULTS.md) ·
[Comparación ARC](ECHO45-ARC-COMPARISON-DESIGN.md).
