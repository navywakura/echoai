# Contenido de los sondeos · desarrollo 0.8

Plan fijado antes de la inferencia. Objetivo: corregir el ejemplo de entrada
CSV y probar sondeos de orden topológico contrarios al orden alfabético.
No se presupone que E gane a F, ni se convierte este desarrollo en confirmación.

## Cambios y controles

- CSV: `format.input` deja de ser la descripción del dominio y pasa a ser
  `alpha,beta`, ejemplo de sintaxis neutral de un solo registro. El esquema
  JSON se presenta por separado. Se explicita cómo codificar comillas CSV
  dentro de JSON y que un salto de línea solo puede ir dentro de un campo
  entrecomillado. La instrucción pide generar un caso nuevo de la categoría,
  no copiar el ejemplo. Cambio idéntico para crítico y autorrevisión de S.
  No se da la solución, la salida esperada ni un caso final al modelo.
- `expanded-v2`: cinco categorías en las primeras cinco familias; seis en
  Dependencias. Tanto F como E pueden usar `reverse-alphabetical-edges`.
  El validador requiere dominio `nodes`/`edges`, grafo acíclico y al menos
  una arista cuyo origen sea lexicográficamente posterior al destino.
  Aristas repetidas se permiten según el contrato. Un ciclo no cumple esta
  categoría aunque tenga una arista inversa.
- E prioriza esa categoría si el AST contiene una llamada a `sorted()` o
  `.sort()`. Es una señal heurística escrita por humanos, no una prueba de
  que ordenar sea incorrecto. No se inspecciona el oráculo para seleccionar.
- F conserva el orden por SHA-256 de `[20261013, task_id, category]`;
  E conserva el mismo orden de respaldo. La categoría nueva puede cambiar
  el orden de F en Dependencias; no se busca una semilla que lo perjudique.
- Se conservan las categorías y rutas de `legacy-v1` y `expanded-v1`.
  La mejora del prompt CSV es compartida por todos los catálogos; reproducir
  prompts históricos exige conservar su revisión congelada de código. La auditoría verifica selección,
  reintentos, elegibilidad y evidencia también para `expanded-v2`.

## Ejecución congelada

Una sola campaña `repair-v2`, doce variantes con semilla47, cuatro brazos
S/I2/F/E contrabalanceados:48 episodios. Todas las familias incluidas:
Intervalos, Registros, Rutas, CSV, Paginación y Dependencias. No se eliminan
fallos, casos negativos ni episodios con errores después de medir.

Mismo Qwen2.5-Coder-14B-Instruct Q4_K_M y revisión/hash; llama.cpp b11577,
contexto4096, salida máxima768, temperatura0,2 y semillas del proveedor
anteriores. Mismo rootfs hermético local. Kaggle T4 privado solo para inferir;
los candidatos y verificadores se ejecutan en Bubblewrap/cgroups local.
Por episodio:25.000 tokens,50 herramientas,12 llamadas LLM,6 críticas,
128 fuel,300s CPU y900s de plazo. Dos reparaciones máximo, guardas de
regresión, evaluación final común y cobertura informativa sin cambios.
El worker tiene80min activos tras carga y techo total90min. No son previsiones.

Antes de lanzar: suite completa, revisión y congelación de código, contrato,
plan y scripts con hashes; notebook privado confirmado. Después: auditoría
repetida, verificación de hashes, descarga de evidencia y apagado de servicios.
No se hace push ni se publican claves o artefactos privados.

## Medición e interpretación

Aceptación por familia, E−S/E−F emparejados, casos finales comunes,
contraejemplos, reparaciones, categorías, entradas copiadas del enunciado,
errores, duplicados, tokens, herramientas y tiempo. Costes de fallos también
se conservan. Auditoría válida certifica consistencia bajo estos checkers;
no prueba seguridad absoluta ni ausencia universal de errores.

Dos cambios simultáneos y tareas conocidas: cualquier diferencia respecto a
0.7 es descriptiva. La comparación E/F comparte el nuevo prompt y catálogo,
pero aún no aísla CAM frente a selección. No se promete 9/12,10/12 ni cierre
científico. Dos variantes de una familia no son dos familias independientes.
El informe final contendrá resultados, limitaciones y la checklist completa
hecho/pendiente de ECHO-5.1, con S6 aplazado hasta después de5.5.
