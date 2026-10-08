# S6-B21-A — ejecución y resultados

Actualización: 06-10-2026 21:41 Madrid. Estado: **CLOSED_NO_PROMOTION**.

B21-A implementa cobertura conjunta de duración/guarda, archivo de hipótesis
y reparación por fallos medidos. Actor y juez conservan el contrato B20.
Comparación: B20 una vez, aleatorio y balanceado con tres semillas cada uno.
Máximo 18 propuestas por recorrido; cero llamadas al modelo.

Partidas físicas reservadas: **4212/16000**. Cuatro procesos CPU locales.
Secuencia: micro → replay/auditoría independiente → desarrollo amplio/auditoría
→ conservación nueva/auditoría. Las fases amplias requieren un balanceado elegible.

| Recorrido | Intentos | Duraciones distintas | Mejor ganancia sin pérdidas | Primer pase |
|---|---:|---:|---:|---|
| balanced-821117 | 18 | 10 | 1 | ninguno |
| random-821117 | 2 | 2 | 4 | 2 |
| random-821101 | 18 | 9 | 0 | ninguno |
| balanced-821101 | 18 | 10 | 0 | ninguno |
| B20 | 18 | 3 | 1 | ninguno |
| random-821129 | 18 | 8 | 0 | ninguno |
| balanced-821129 | 18 | 10 | 0 | ninguno |

Auditoría del micro: válida.
Revisión aritmética y bytes exactos: válida.


Cualificación completa: False.

**S6 sigue abierto.** Un pase de B21-A sería evidencia de búsqueda y conservación.
Faltan atribución al neocórtex, descubrimiento desde SEMILLA, piloto, campaña y examen B1–B5.
T/C/R/N/P del informe siguen como intervenciones posteriores separadas.

[Contrato congelado](ECHO45-S6-B21-A-DESIGN.md) · [Implementación](ECHO45-S6-B21-IMPLEMENTATION.md) ·
[Estado](../lab/seed/s6b21-20261006/status.json) · [Pruebas](../lab/kaggle/s6b21-20261006/tests-final.log).

## Revisión posterior al cierre

La regla ganadora es `HOLD=2` si `level<=1`, `pred_error==0` y
`world_events<=8`: 52 → 56 niveles sin pérdidas en el micro. Fue generada
por el control aleatorio y reproducida por replay y auditoría independiente.
No se midió en desarrollo amplio ni en conservación nueva: el contrato
exigía un ganador balanceado para abrir esas fases. Descubrimiento automático
acotado queda demostrado; la ventaja del balanceado, del LLM y el ciclo S6
completo siguen pendientes. La guarda ya pertenecía a la biblioteca B20.

[Diagnóstico y comparación B18–B21](ECHO45-S6-B21-FORENSICS-20261006.md)
con reconstrucción de selección y efectos por caso, sin nuevas partidas.
