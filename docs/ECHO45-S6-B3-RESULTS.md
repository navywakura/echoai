# S6-B3 · resultado auditado

2026-09-27. **ROJO** según el contrato previo.

Base v5.8; políticas temporales acotadas elegidas por Qwen2.5-Coder 7B.
Los algoritmos H1/H3 son los módulos programados previamente; esta campaña
mide selección y composición de controles, no generación arbitraria de código.

| Brazo | Niveles /1800 | Puntuación media |
|---|---:|---:|
| echo | 1668 | 49.435224 |
| fijo | 1668 | 49.435224 |
| semilla | 1668 | 49.435224 |
| sinfiltro | 1586 | 40.863818 |

| Criterio | Pasa |
|---|---|
| B1 | ❌ |
| B2 | ❌ |
| B3 | ✅ |
| B4 | ✅ |
| B5 | ✅ |

Desarrollo oficial, suma de las 24 partidas por brazo:

| Brazo | Niveles | Puntuación total |
|---|---:|---:|
| semilla | 24 | 23.999037 |
| echo | 24 | 23.999037 |

Las fuentes y políticas se congelaron antes de abrir 18000–18059.
No se reevalúan los rojos anteriores, no se selecciona otro agente tras
ver el examen y no se declara resolución de ARC oficial reservado.

La puntuación conserva el contador histórico que excluye los reinicios
automáticos; estos siguen guardados y contados en los registros.

[Contrato](ECHO45-S6-B3-DESIGN.md) ·
[Auditoría](../lab/seed/s6b3-20260927/exam/audit.json).
