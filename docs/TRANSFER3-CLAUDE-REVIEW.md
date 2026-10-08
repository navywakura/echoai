# Petición a Claude — revisión independiente de TRANSFER-3

Roger dispone de Claude Code y ha ofrecido colaboración. Este archivo es la
tarea propuesta; **no afirma que Claude haya revisado o aprobado nada**.

## Instrucciones para copiar a Claude

Trabaja en `/home/roger/REALRXOS/RXos/echoai`. Lee AGENTS.md, CLAUDE.md y
docs/05-NEXUS-0-SPEC.md primero. Revisión **sólo lectura**: no edites archivos,
no lances entrenamiento/campañas, no generes ni abras B/C reservados. Puedes
ejecutar diagnósticos read-only sobre informes públicos y tests existentes.
No LLM dentro del agente NEXUS, no segundo bus, no Akida, no kernel.

Lee:

- docs/TRANSFER3-REHEARSAL-V3.md y docs/TRANSFER3-V4-DESIGN.md.
- docs/TRANSFER3-REHEARSAL-V4.md (resultado del cribado con presupuesto igual).
- docs/TRANSFER3-FINAL-PROTOCOL-DRAFT.md.
- nexus0/transfer3/{policy.py,school_v3.py,budget_school.py,rehearsal_v2.py,
  rehearsal_v3.py,rehearsal_v4.py,custody.py}.
- nexus0/compose1/model.py, compose1_v3/controller.py y el gate heredado en
  compose1/controller.py; tests/test_transfer3*.py.
- lab/transfer3/rehearsal-v4.json si necesitas verificar datos.

Responde con hallazgos priorizados, archivo/línea y evidencia. Separa:

1. Bugs de implementación o de auditoría frente a hipótesis científicas.
2. Si la representación relativa Q mezcla estados que requieren elecciones
   opuestas y si el desempate actual puede realmente aprender el desvío.
3. Si reward/optimismo de acciones no probadas/cobertura explican los fallos;
   evita sugerir dar más peso a Q sin justificar representación y evidencia.
4. Justeza de scratch y presupuestos, captura única, congelación y costes.
5. Independencia geométrica, capacidad del generador y tamaño muestral.
6. Huecos del enlace de custodia. Los tests de apertura no prueban custodia
   externa ni integran todavía la campaña al examinador.

Propón **un siguiente experimento causal acotado**, con qué cambiar, qué
mantener fijo y qué resultado lo refutaría. No busques hacer verde el examen
mediante selección de salas o rebajando criterios después de ver v4.

Entrega texto de revisión, no parches. Roger lo pegará a Codex. Codex no
considerará la revisión hecha hasta recibir ese texto y comprobar hallazgos.
