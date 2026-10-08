# S6-B22 — registro de implementación

Implementación privada del 6 de octubre de 2026 a partir del PDF B22 recibido.
Se ejecuta la etapa V/S de 15.336 partidas descrita por el informe. N, E y la
confirmación estadística S requieren reservas y contratos posteriores. El
estado de esas fases se conserva como NOT_RUN; no se presentan como código
de examen ya terminado ni se abren reservas del examen S6.

| Componente | Implementación |
|---|---|
| Muestreo emparejado R22/M22 | `echo_arc/s6b22_search.py` |
| Bloques de dos hijos con duración fija | Mismo investigador; vecindario de una edición y archivo de resultados propios |
| Medición, auditoría, libro físico y validación neutral | `seed/s6b22.py` |
| Recuperación B21, exposición y congelación | `seed/s6b22_build.py` |
| Revisión aritmética independiente y comparación emparejada | `seed/s6b22_review.py` |
| Informe privado de progreso | `seed/s6b22_report.py` |
| Casos de aceptación e integración | `tests/test_s6b22.py` |

Pasan 102 comprobaciones: 33 B22 y 69 de regresión B21/B20/B18 con Python
3.12.13. La suite nueva comprueba una rama +4 con pérdida y dos reparaciones
HOLD fijo; presupuesto de diez exploraciones globales; hijos sin ganancia;
falta de vecinos; independencia del muestreo R respecto a resultados;
normalización por caso; superficies de entrada; ganador R sin ganador M;
veto por pérdida individual; discrepancias de replay/auditoría; cachés
separadas y reanudación; coste reservado sin devolución; interrupción sin
reintento gratuito; permisos protegidos; y análisis emparejado.

Las pruebas de integración simulan el ejecutor para comprobar contabilidad
y separación de cachés. La ejecución científica posterior es la que debe
confirmar paridad del actor real y medir los resultados; tests verdes no
equivalen a B22 ni S6 verdes.

La recuperación comprobó las 70 fuentes B21 y la identidad del ganador,
incluida su política compuesta y las mediciones completas base/candidato,
replay y auditoría. La revisión de exposición consultó 197 metadatos
históricos sin coincidencias para 65000–65039 y 66000–66039. El manifiesto
conservará el inventario exacto. No se consultaron respuestas nuevas.

El runtime enumera su cierre de dependencias y excluye contratos, informes,
PDF, tests y controles humanos. El supervisor recupera el ganador exacto
para V; el investigador S recibe solo base, historial propio, tipo, índice
y semilla. Las llamadas quedan grabadas como bytes canónicos comprimidos,
reconstruidos antes de cada auditoría de candidato.

La agenda sustituye la alternancia B21 por bloques protegidos de condiciones.
Las señales locales se llaman solapamientos observados; la ganancia prevista
y efecto medido del hijo empiezan en null, y el riesgo en unknown. No hay
reparación local de duración. Las diez duraciones siguen accesibles mediante
muestreo global común, sin favorecer la ganadora B21.

La apertura de transferencia exige una cualificación auditada de cada
candidato. Se congelan juntos los finalistas S por el orden de semillas,
independientemente de sus scores futuros. V tiene su propia plaza y no
depende de un ganador M22. Las políticas, propuestas y contratos anteriores
no se modifican. El cambio tampoco afecta al núcleo NEXUS-0.

El diario de desarrollo existente conserva propuestas y veredictos reales.
Las cohortes nuevas y desarrollo amplio usan el ejecutor sin observador:
la activación exacta de la regla no se conoce allí, y se reportan cambios
de acciones sin identificarlos con activaciones. Esta limitación se declara
en el contrato para preservar el actor y el instrumento congelados.

Comandos con el entorno gestionado:

```sh
lab/arc3/ARC-AGI-3-Agents/.venv/bin/python -m seed.s6b22_build prepare
lab/arc3/ARC-AGI-3-Agents/.venv/bin/python -m seed.s6b22_build launch
python3 -m seed.s6b22_report
python3 observe.py --launch
```

`prepare` requiere pruebas válidas y deja el manifiesto congelado. `launch`
verifica código, pruebas, entradas, contrato y runtime antes de comenzar.
El lanzamiento supervisado se registra en el servicio de usuario
`echoai-s6b22-run`. Los artefactos viven en `lab/seed/s6b22-20261006/`.
El código no factura ni llama a Kaggle/API: estos módulos se miden en CPU.

[Contrato](ECHO45-S6-B22-DESIGN.md) · [Resultado vivo](ECHO45-S6-B22-RESULTS.md) ·
[Pruebas](../lab/seed/s6b22-20261006/tests-final.log).

Arranque confirmado: 6 de octubre a las 22:45:36 Madrid. Servicios
`echoai-s6b22-run` y `echoai-s6b22-report` activos. La primera medición
basal reproduce exactamente los 52 niveles y todas las filas B21; replay
y auditoría continúan. [Recibo de arranque](../lab/seed/s6b22-20261006/launch.json).
