# PCWORLD-1: remediación de reparación

Plan previo al microensayo. Se conserva `repair-v2` como resultado histórico.
No se publica ni se relaja el oráculo ni la cobertura de dos categorías.

1. Feedback CEGIS explícito y vinculado a recibos: input, salida observada,
   esperada y ejemplos públicos, exclusivamente de ejecuciones no finales.
2. Probar primero los casos públicos y los casos anteriormente aprobados.
   Un parche regresivo queda archivado, pero no sustituye al candidato vigente;
   el segundo intento recibe el fallo y el código rechazado. Dos intentos máximo.
3. En E, la primera refutación activa reparación exclusiva, sin más crítico.
   Reejecutar los sondeos anteriores sobre el nuevo candidato. Si solo se
   obtuvo una categoría, informar cobertura pendiente, incluso si se reparó.
4. Watchdog explícito para CPU: 300 s por llamada, 900 s por episodio;
   mismos límites para todos los brazos, sin cambiar tokens/herramientas.
5. Tests de datos de reparación, rollback, persistencia del fallo, ausencia de
   consultas adicionales al crítico y conservación de cobertura. Suite PCWorld.
6. Dos episodios locales E, Registros y Rutas, semilla 43. Son desarrollo;
   elegirlos se declara antes de ejecutar. No se extrapola una victoria.
7. Si una reparación pasa los casos reservados, microensayo GPU 14B privado.
   Kaggle aloja únicamente inferencia; la ejecución candidata conserva
   Bubblewrap/cgroup local. Medir carga, tokens, tiempo y uso GPU. No iniciar
   la matriz completa sin comprobar el transporte y la frontera de ejecución.

Correcciones de la autopsia: el feedback anterior ya incluía expected/observed
en evidencia genérica. Registros y CSV repitieron código, no se demostró que
todas las reparaciones fallaran por regresión. Intervalos perdió en E por plazo
del proveedor. F registró 34.346 tokens observados + 112.642 reservados por
fallos; E, 33.810 + 43.904. La diferencia entre totales no acredita por sí sola
ahorro de inferencia. HMAC y replay válidos no prueban aislamiento inexpugnable.

## Microensayo local r1 y revisión r2

r1 terminó 2/2, sin errores del proveedor, con 0 reparaciones y 0 pases finales.
Auditoría válida: 140 recibos. Registros repitió la sustitución de duplicados;
Rutas eliminó componentes sin resolver correctamente la relación con el padre.
Los dos intentos fallidos se conservaron sin sustituir el candidato retenido.

r2 cambia exclusivamente la presentación del prompt de reparación: secciones
explícitas de contrato, programa retenido, entrada, salida observada, esperada
y ejemplos públicos. Mismos dos casos/semilla, modelo, límites y verificadores.
Es desarrollo sobre casos conocidos, no confirmación independiente. No se
añade la solución ni se divulgan entradas de evaluación reservadas al modelo.
