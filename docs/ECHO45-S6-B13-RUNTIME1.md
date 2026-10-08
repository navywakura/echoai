# S6-B13-R1 — reinicio declarado por rendimiento del runtime

Adenda privada, 3 de octubre de 2026, fijada antes de iniciar el reinicio.
No autoriza mezclar resultados ni declarar verde S6.

El ejecutable del sistema muestra CPU sin AVX/FMA/AVX2 en su informe de
capacidades, aunque el Ryzen 5500U anuncia esas instrucciones. Su primera
petición real de 1372 tokens tardó 444,33 s; el procesamiento de entrada fue
de 3,19 tokens/s. Un contexto cercano al límite 3072 podría agotar los 900 s
del contrato original. La primera llamada de ECHO agotó esos 900 s a las
23:45:44; queda como fallo del instrumento, no derrota ni rechazo V3.
Durante esa llamada se compiló el runtime nuevo con un solo proceso; esa
carga adicional pudo afectar a su tiempo y queda declarada. La previsión
del riesgo de timeout se hizo antes, a partir del ritmo de FIJO sin compilación.
La razón del cambio es el coste y la fiabilidad del
instrumento, no el resultado favorable o desfavorable de un brazo.

Se compila llama.cpp desde el tag b5904, commit
`79e0b68c178656bb0632cb8602d2940b755077f8`, en un directorio privado de herramientas.
Build Release estático, `GGML_NATIVE=ON`, CUDA/HIP/CURL desactivados. Se sigue
la [documentación oficial de compilación](https://github.com/ggml-org/llama.cpp/blob/79e0b68c178656bb0632cb8602d2940b755077f8/docs/build.md).
El manifiesto conserva commit, opciones, compilador y hashes de los ejecutables.
No se reemplaza `/usr/bin/llama-cli` ni ninguna dependencia del sistema.

El motor numérico cambia: el paquete anterior declara versión 0 desconocida
y bibliotecas b5904; no se presupone equivalencia bit a bit de las inferencias.
Por ello se cierra la ejecución anterior como incompleta, se conservan todos
sus resultados e intentos interrumpidos y se reinician **los dos brazos y el
control aleatorio desde SEMILLA**, con propuestas y cachés nuevas. No se
agregan sus resultados. Las reglas emitidas anteriormente no entran en las
peticiones nuevas. La reserva anterior nunca se abrió y conserva sus semillas.

Se mantienen el GGUF y su hash, los tres pares de semillas, 36 llamadas de
piloto y 60 de campaña, cuatro hilos/procesos, temperatura, límites de tokens,
peticiones, gramática, selector de objetivos, verificador, A/B, máximo de reglas
y criterios V1–V4/B1–B5. Solo cambia el ejecutable/tokenizador a los binarios
estáticos registrados y la guardia temporal de llamada, 900→1800 s. El aumento
de esa guardia no aumenta los 160 tokens de salida ni el presupuesto de juegos.
Las dos calibraciones de transporte, sin datos de tareas, se contabilizan
separadamente; la primera valida el esquema y la segunda mide un prompt sintético
largo. La tokenización de una petición anterior debe reproducirse exactamente.

Las dos calibraciones terminaron bien: 36 tokens en 6,44 s y 1372 tokens en
66,08 s (la segunda usa texto sintético y salida vacía forzada). El procesamiento
de sus 1371 tokens medidos por llama.cpp fue 22,18 tokens/s frente a 3,19
tokens/s en la petición anterior de igual longitud; no se comparan aciertos
ni se confunde esta calibración con una prueba de inteligencia. La tokenización
de la petición real anterior coincide en sus 1372 IDs. Los logs confirman
AVX/AVX2/F16C/FMA/BMI2 activos. Las 22 pruebas de B13/R1 pasan sin jugar.

`seed/s6b13_runtime1.py` reutiliza las funciones originales de B13 mediante
configuración explícita en el padre, los workers y los subprocesos de auditoría.
Las funciones originales de petición/verificación y el examen no se reescriben.
Las fuentes originales y las del runtime nativo se verifican en el nuevo perfil.
Un error de rutas, integridad, contexto o replay vuelve a detener la condición.

La secuencia sigue siendo paridad → piloto → auditoría → campaña → auditoría
→ examen de cuatro brazos. Sigue siendo un experimento cuyo resultado puede
ser negativo. Un runtime más rápido permite medir antes; no demuestra una
mejora de inteligencia ni sustituye las puertas de S6.

Raíz: `lab/seed/s6b13-native-20261003/`. El estado de la versión anterior queda
en `lab/seed/s6b13-20261003/`, sin alterar sus fuentes congeladas.
