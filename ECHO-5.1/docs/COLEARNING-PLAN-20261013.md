# Co-learning A → B · protocolo de desarrollo 0.9

Estado: implementación; plan fijado antes de inferencia. Sin publicación.

## Pregunta y alcance
¿Un receptor nuevo usa un parche y contraejemplos autenticados de otro episodio
para resolver una variante de Registros sin repetir la reparación? No se cambian
pesos ni se extraen todavía abstracciones parametrizadas. La biblioteca conserva
recetas acotadas: evidencia en A no acredita corrección en B.

## Diseño fijado
- Modelo: mismo Qwen2.5-Coder-14B-Instruct Q4_K_M y runtime del protocolo 0.8.
- Adquisición: una ejecución nueva E, `repair-v2`, Registros00, semilla de tareas
  47, semilla del proveedor 73, catálogo expanded-v2. Sin defecto externo sembrado.
- Publicar solo si A termina aceptado tras una reparación, con auditoría válida,
  refutación no final, reproducción de esa entrada en el parche y ejemplos públicos.
- Si no hay lección elegible, se informa del resultado; no se reintenta A ni se
  importa una victoria histórica para reemplazarlo.
- Receptor B: Registros01, mismo generador/contrato, tres parejas con semillas del
  proveedor 73, 74, 75. Es desarrollo conocido, NO transferencia independiente.
- Pareja 73: aislado → cooperativo; 74: cooperativo → aislado; 75: aislado → cooperativo.
- Solo cambia la biblioteca: vacía frente a la lección congelada de A. Misma política
  E, 25.000 tokens, 50 herramientas, 12 llamadas LLM, 6 críticas, 128 fuel,
  dos reparaciones y plazo de 900 segundos por episodio. No se omiten críticos.
- A se ejecuta una vez como prefijo común y su coste se atribuye a ambos recorridos.
  No se publican lecciones de B durante el ensayo. Reinicialización de CAM episódica
  y restauración de la biblioteca desde disco antes de cada receptor.

## Frontera de evidencia
La memoria compartida usa recibos autenticados separados como almacenamiento,
pero las consultas y decisiones se registran en el `thought.jsonl` existente.
El supervisor atestigua autor, tarea, snapshot y recibos; el nombre del autor no
es una firma criptográfica del LLM. Se valida custodia y semántica del donante,
AST y bytes del parche, compatibilidad de contrato y ámbito. Solo se exportan
contraejemplos observados antes de la evaluación final: nunca casos reservados.
El parche se entrega como dato candidato; no modifica oráculos ni presupuestos.
Retirar o alterar la evidencia invalida el recuerdo. No se afirma consulta total O(1).

## Métricas y auditoría
- Aceptación final y aceptación sin reparación, errores, refutaciones nuevas y
  repetición exacta del contraejemplo de A cuando sea observable.
- Tokens, llamadas LLM/crítico, reparaciones, herramientas, CPU y tiempo por episodio.
- Coste de adquisición común, publicación y consulta explícito; resultados B solos
  y recorrido A → B. Publicación y auditorías se informan como trabajo supervisor.
- Auditoría de cada ejecución, procedencia de memoria e igualdad de fuentes,
  cuotas y configuración entre pares. Conservar fracasos, no elegir semillas después.
- Examen final del receptor permanece intacto. Ausencia de críticas refutatorias
  no implica prueba universal. Tres parejas de una familia no cierran H2/T20.

## Entrega
Biblioteca persistente, integración de propuesta inicial, pruebas de integridad y
no transferencia indebida, supervisor Kaggle con apagado, informe y checklist.
Quedan fuera: semántica de grafos, nuevos prompts CSV, otros routers, S6 y publicación.
