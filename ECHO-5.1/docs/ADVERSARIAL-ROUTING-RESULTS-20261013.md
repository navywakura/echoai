# PCWORLD-1 · resultados del sondeo adversarial

Fecha de ejecución local: 13 de octubre de 2026. Estado: ejecución completa y
auditoría válida; **la ventaja de ECHO no quedó demostrada**.

## Resultado principal

Se ejecutaron los 48 episodios preregistrados: 12 variantes de reparación por
seis familias conocidas, cada una en los brazos S, I2, F y E. La aceptación
exigía que el candidato pasara todas las pruebas públicas, los contraejemplos
retenidos y las pruebas de desarrollo reservadas del episodio.

| Brazo | Aceptaciones | Pruebas adversariales válidas | Episodios con contraejemplo | Tokens | Llamadas LLM | Pared acumulada |
|---|---:|---:|---:|---:|---:|---:|
| S | 4/12 | No aplica | 2/12 | 17.490 | 28 | 1.312 s |
| I2 | 4/12 | No aplica | 0/12 | 8.252 | 24 | 684 s |
| F | 2/12 | 8 apoyadas, 2 refutadas | 4/12 | 146.988 | 51 | 2.706 s |
| E | 2/12 | 6 apoyadas, 6 refutadas | 8/12 | 77.714 | 46 | 2.543 s |
| **Total** | **12/48** | **14 apoyadas, 8 refutadas** | — | **250.444** | **149** | **7.247 s** |

La categoría «refutada» significa que el verificador independiente confirmó que
el candidato falló ese input; es un contraejemplo útil, no una reparación
correcta. E halló seis contraejemplos confirmados frente a dos de F, pero no
obtuvo más tareas aceptadas: ambos acabaron en 2/12. Así que el crítico
adaptativo mejoró la detección en esta muestra, pero el ciclo no convirtió esa
señal adicional en una mejora del resultado final.

Los rechazos del validador muestran que el reintento no eliminó los problemas
de formato de forma uniforme: en F quedaron registrados 11 sondeos que no
correspondían a la categoría pedida y 6 sondeos duplicados; en E, 1 y 3,
respectivamente. No se registraron inputs fuera del dominio en esta tanda. Las
respuestas rechazadas no se contaron como cobertura y su coste quedó en los
recibos.

E no superó a F en ninguna de las 12 comparaciones emparejadas: 12 empates.
Frente a S, E empató en 10 tareas y perdió en dos; frente a I2, el mismo
resultado. S e I2 aceptaron cuatro tareas cada uno y compartieron los mismos
dos éxitos de intervalos y dos de paginación. F y E aceptaron solo las dos
variantes de paginación. Los otros cuatro dominios (registros, rutas, CSV y
dependencias) quedaron en 0/2 para todos los brazos.

## Coste y fallos

Todos los brazos usaron el mismo Qwen2.5-Coder-7B-Instruct Q4_K_M local, el
mismo runtime hermético, tareas, verificadores y límites. Se consumieron
250.444 tokens de los presupuestos por episodio. F fue el brazo más caro
(146.988 tokens); E consumió menos que F, pero 4,4 veces lo de S y 9,4 veces
lo de I2 en esta ejecución. El tiempo acumulado de inferencia del proceso
llama.cpp fue 28.351 segundos de CPU y el pico de memoria del servicio fue
6,47 GB. La campaña duró 7.247 segundos de pared; energía eléctrica no medida.
No hubo coste de API pagada.

Siete episodios acabaron con `ProviderFailure: provider total deadline
exhausted` (F=5, E=2); los demás episodios completaron el protocolo, incluidos
los rechazos y abstenciones. El comando del piloto terminó con código 1 por
esos errores de proveedor. Esto no invalida la ejecución completa de la
matriz: se generaron 48 resultados y el auditor independiente devolvió código
0. Sí limita la comparación porque los plazos del modelo afectaron más a F y
E, y deben tratarse como fallos, no como éxitos ni como datos ausentes.

Los límites configurados fueron 25.000 tokens, 50 herramientas, 300 s de CPU
del candidato, 300 s de pared y hasta 12 llamadas LLM por episodio, con máximo
de seis llamadas de crítico. El modelo tardó cerca de dos horas de CPU de
pared del servicio; por ello, este resultado también refleja el perfil de
latencia de Qwen 7B Q4 en la CPU disponible.

## Integridad y alcance

- Auditoría: `valid: true`, 2.049 recibos, 48 episodios, cero errores.
- Fuentes congeladas: `sources_unchanged: true`.
- `destroyed == 0` en todos los episodios; cero aceptaciones falsas.
- Sin llamadas a fixtures de diagnóstico y sin llamadas al NEXUS-0 nativo.
- No hubo acceso del modelo a las pruebas reservadas ni a sus resultados.
- Todas las variantes pertenecen a seis familias ya conocidas. No es una
  prueba de transferencia a dominios independientes ni un benchmark externo.
- Con dos variantes por familia, los conteos son descriptivos y muy inciertos;
  no permiten inferencia estadística ni una afirmación general de superioridad.

El piloto fue completo, pero no confirmatorio. La conclusión preregistrada se
mantiene: **ECHO no demostró ventaja en tasa de resolución**. Hay una señal
diagnóstica que merece investigación —más contraejemplos válidos en E que en F—
y un cuello de botella claro entre detectar el fallo y repararlo. La siguiente
prueba tendría que congelar un mecanismo para convertir contraejemplos en
reparaciones, limitar fallos de proveedor de forma igual para los cuatro
brazos y usar semillas o familias nuevas. No se debe reutilizar esta tanda
como confirmación.

## Evidencia local

Los archivos detallados permanecen en el directorio ignorado de artefactos y
no contienen credenciales de API:

- `ECHO-5.1/artifacts/adversarial-routing-20261013/result.json`
- `ECHO-5.1/artifacts/adversarial-routing-20261013-audit.json`
- `ECHO-5.1/artifacts/adversarial-routing-20261013-resources.json`
- `ECHO-5.1/artifacts/adversarial-routing-20261013.log`

La primera ejecución parcial, detenida manualmente por un diagnóstico erróneo
del operador, está separada en `adversarial-routing-20261013-aborted-operator-stop`
y queda excluida. La matriz aquí informada es el relanzamiento completo con el
mismo código y contrato congelados.
