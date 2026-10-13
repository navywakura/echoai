# Piloto de dos puertas · 13 de octubre de 2026

Estado: preparación de desarrollo; ECHO-5.1 no está cerrado. Protocolo
`repair-two-gate-v1`, contrato `0.5.0-development`. No sustituye los resultados
anteriores ni presupone que E gane.

## Cambios y límites

El contrato de Rutas ya decía «without traversing above root». Ahora explicita
que `..` en la raíz no tiene efecto ni permanece en la salida. Es una aclaración
para todos los brazos, no una corrección del oráculo. El caso final expuesto en
el diagnóstico anterior ya pertenece al desarrollo, no a una confirmación ciega.

E detiene las críticas durante la reparación. Tras un parche comprobado contra
los ejemplos públicos, los casos antes soportados y las refutaciones retenidas,
reproduce los sondeos anteriores sobre ese parche y vuelve a solicitar una
categoría distinta si aún falta cobertura. Si esa categoría refuta el parche,
puede usar el intento de reparación restante. Se mantienen dos intentos totales,
seis llamadas al crítico y los límites originales. Un parche rechazado restaura
el candidato anterior mediante compare-and-swap. Una crítica inválida o repetida
no acredita cobertura. F conserva el mismo requisito de dos categorías.

## Plan fijado antes de inferencia

- Tres familias solicitadas: Registros, Rutas y Paginación.
- Una variante por familia: `repair-v2`, generador de seis tareas, semilla 47,
  filtrado por esas tres familias antes del lanzamiento. Son nuevas variantes de
  familias conocidas, **no tareas independientes**.
- Doce episodios: S, I2, F y E en cada tarea, orden contrabalanceado existente.
- Qwen2.5-Coder-14B-Instruct Q4_K_M, mismos pesos, revisión y tokenizer del
  diagnóstico previo; llama.cpp b11577, contexto 4096, salida máxima 768,
  temperatura 0,2 y semilla 73 + índice de llamada para todos los brazos.
- Reparación desde contrato más testigos (`contract_only`) en todos los brazos;
  no se suministran resultados finales al proponente ni al crítico.
- 25.000 tokens, 50 herramientas, 12 llamadas LLM, 6 críticas y 128 fuel por
  episodio. Plazo 900 segundos por episodio, límite externo de una hora GPU
  para este piloto pequeño. No garantiza terminar dentro de ese plazo.
- Sin caché de propiedades; código candidato ejecutado únicamente en el rootfs
  local fijado, con Bubblewrap y cgroup. Kaggle solo calcula inferencia.
- Transporte temporal autenticado con permisos separados para solicitante y
  worker; no ofrece shell, archivos ni ejecución de candidatos. Las claves
  efímeras no forman parte de documentación ni commits.

## Qué se publicará en el informe local

Se retienen todos los episodios, incluidos errores y timeouts. Se desglosan:
aceptación del protocolo, resultados en los mismos casos finales de cada tarea,
cobertura de categorías, refutaciones, reparaciones, tokens realmente usados,
reservas cobradas por fallos, herramientas y tiempo. La métrica común de casos
finales permite distinguir calidad del código de cobertura adicional en E/F.
S conserva su autorrevisión e I2 sus dos propuestas independientes: ninguno se
empobrece para producir una victoria de E.

Los doce episodios solo dimensionan y diagnostican. Cualquier ventaja observada
necesitará nuevas familias independientes, un contrato congelado y una muestra
adecuada. Si hay empate o E pierde, ese será el resultado registrado.
