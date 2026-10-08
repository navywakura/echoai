# ECHO-4.5 · S1 (objetos en rejillas) · cierre (2026-09-25)

Contrato: `ECHO45-SEED-DESIGN.md`. Todo medido en las **201 tareas reservadas** del gimnasio, que
nunca se usan para aprender, con presupuesto de búsqueda de 400 expansiones. Las evaluaciones
siguen selladas.

## Resultados

| Sandbox | Vocabulario | Entrenamiento | Reservadas verificadas | **Reservadas con el test correcto** |
|---|---|---|---|---|
| `echo45-seed` | S0 · 44 primitivas | ninguno | 16 | 15 |
| `echo45-a` | S0 | 3 rondas (68 tareas verificadas, 8 conceptos) | 17 | 16 |
| `echo45-s1-seed` | **S1 · 65 primitivas** | ninguno | 25 | **21** |
| `echo45-s1-a` | S1 | 3 rondas (83 tareas verificadas, 3 conceptos) | 25 | **21** |
| `echo45-s1b-seed` | S1b · 73 (S1 + relaciones) | ninguno | 24 | 20 |

**Custodia:** `verify` rehace los 83 programas y la cadena del diario de `echo45-s1-a`. Resultado:
`valid: true`.

## Lectura

1. **El vocabulario de objetos funciona:** de 15 a **21** tareas correctas (+40 %), sin entrenar.
   Aporta más que tres rondas de aprendizaje con el vocabulario viejo (+1).
2. **Los conceptos que aprende son abstracciones de verdad, y jerárquicas:**
   - `k001` = quitar filas y columnas repetidas («comprimir lo que se repite»), nacido de 4
     tareas distintas;
   - `k002` = reflejar en horizontal y en vertical («mosaico con simetría de 4»);
   - `k003` = girar 180° y aplicar `k002`, un concepto **construido sobre otro concepto**.
3. **Pero el aprendizaje todavía no transfiere:** con S1, las tres rondas no suben las reservadas
   (21 → 21). Los conceptos son secuencias fijas y la búsqueda no tiene intuición sobre qué probar
   primero.
4. **Más primitivas a ciegas diluyen la búsqueda:** S1b añade 8 primitivas de relaciones (deslizar
   objetos, estampar plantillas, reflejar cada objeto, enmarcar), no resuelve ninguna tarea nueva
   y pierde una.

## Decisión

- **S1 queda cerrada con el vocabulario S1 (65 primitivas)** como base de ECHO-4.5. S1b queda
  documentada como intento sin ganancia.
- Para que aprender aporte hacen falta **conceptos con parámetros** e **intuición** (fase S2).
  Según el roadmap acordado, antes van S3, S4 y S5, porque el requisito R3 (20 % en ARC-3) depende
  de ellas. La revisión de ARC Prize 2026 lo refuerza: con la fórmula oficial, la eficiencia en
  acciones pesa muchísimo.
