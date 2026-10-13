# Candidato congelado y evaluación común · protocolo 0.6

Ensayo de desarrollo fijado antes de nueva inferencia. No convierte un empate
anterior ni tres tareas conocidas en una confirmación independiente.

## Cambio solicitado

Separar cobertura del crítico, evidencia de reparación y evaluación final.
`GRADUADO_POR_SUPERVIVENCIA` es únicamente la etiqueta de un candidato reparado
listo para evaluar cuando falta cobertura. Lleva `verified: false`: agotar
intentos o recibir críticas inválidas no prueba ausencia de errores. La
aceptación en S/I2/F/E exige todos los casos finales requeridos soportados y
ningún error/presupuesto agotado que impida completar la evaluación.

La cobertura se conserva como métrica para todos los brazos, incluso cuando
no hubo reparación. No se concede a E una excepción que F o un candidato
correcto sin reparación no tengan. Se conservan los límites originales,
rollback, dos intentos de reparación y todas las refutaciones retenidas.

El bucle comprueba la cuota antes de cada reintento del crítico: no reserva una
séptima llamada. Esto permite continuar la evaluación con los recursos que
queden; no concede recursos adicionales. El prompt de `empty-singleton`
explicita cero o un elemento, usando `value` en Registros, conforme al esquema.
No se inserta un contraejemplo ni una respuesta del oráculo manualmente.

Implementación en `pcworld/pilot.py`, `controller.py` y `adversarial.py`;
`protocol.py` sigue siendo el parser JSON de frontera y no necesita cambiar.
Las pruebas anteriores de cobertura cambian de semántica con el contrato,
conservando el rechazo de código incorrecto y de cobertura inventada.

## Comparación planificada

Se repite el piloto conocido: semilla 47, Registros/Rutas/Paginación, una
variante de cada familia, brazos S/I2/F/E y orden contrabalanceado existente.
12 episodios, Qwen2.5-Coder-14B-Instruct Q4_K_M, llama.cpp b11577, contexto4096,
salida768, temperatura0,2, semilla73+índice. Mismos pesos/revisión/tokenizer,
rootfs, presupuestos y plazo900s del piloto anterior. Kaggle solo inferencia;
Bubblewrap/cgroups y oráculos locales. Notebook privado, máximo50min de worker
externo y60min de Kaggle, sin reintento automático. No publicar ni hacer push.

Se comparan aceptación común, cobertura, reparaciones, tokens observados,
fallos, trabajo y tiempo. Los cuatro brazos pueden ganar, empatar o perder.
Cambian conjuntamente criterio de cobertura y prompt: una eventual diferencia
no aislaría por sí sola el efecto de CAM, del router o de la formulación.

No asumir que el parche actual de Registros pasa porque otro parche anterior
pasó5/5. El piloto0.5 permanece2/3 para todos bajo sus reglas originales; esta
revisión tendrá su propio manifiesto y recibos. Para cerrar científicamente5.1
seguirán haciendo falta tareas independientes y comparaciones/ablaciones
suficientes, aunque aquí E obtuviera3/3.
