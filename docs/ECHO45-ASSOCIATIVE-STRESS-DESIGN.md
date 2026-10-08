# CAP-STRESS-1 — límite del banco asociativo

Contrato del 2 de octubre de 2026, fijado antes de medir. El resultado puede ser
negativo. Se busca un régimen en el que el tamaño evita interferencia y se
acota capacidad de recuperación bajo una distribución declarada. No se
garantiza una victoria de 500k ni un máximo universal.

Se reutilizan `_indices` y `probs` de `SparsePrimitiveGuide`. La entrada se
inyecta como rasgos ya codificados; encoder de rejillas y verificador de
programas quedan fuera del microbanco. La actualización reproduce el incremento
positivo saturado de `observe`. Se mide recuperación del backend, no ARC.

Configuración: 65.536 y 500.000 contadores uint8, ocho hashes por clave,
32 etiquetas equilibradas, ocho rasgos independientes por contexto, dos
observaciones por asociación y cargas acumulativas de 256, 1.024, 4.096,
16.384 y 65.536 contextos. Veinte semillas 46001–46020 determinan contextos,
consultas y etiquetas. No se seleccionan claves a partir de sus colisiones.

Cada carga tiene 512 consultas (256 en la carga menor) a contextos almacenados,
con 0 o 2 de sus ocho rasgos sustituidos por rasgos de otros contextos. La
segunda condición es 25 % de corrupción de rasgos, idéntica en ambos tamaños.
No existe fase temporal ni propagación de spikes en este banco. La etiqueta
correcta es la del contexto original. El control exacto conserva los pares
rasgo–etiqueta sin hashing y utiliza el mismo sumatorio. Los empates se resuelven
por orden lexicográfico fijo. El margen de la guía usa su score normalizado;
el del control exacto usa incrementos, por lo que no se comparan directamente.

Variable primaria: diferencia de exactitud 500k–65k, sin corrupción, a 16.384
contextos. Son 131.072 claves y carga 8D/M = 16 en 65k y 2,097152 en 500k.
La consulta correcta aporta señal directa de 8 × 8 × 2 = 128 incrementos,
antes de interferencias. Esto no garantiza que se cumplan los umbrales.

Verde de esta condición: media 500k ≥ 95 %, media 65k ≤ 90 %, diferencia ≥ 5
puntos porcentuales, límite inferior del bootstrap pareado por semilla al
95 % > 0 y test de signos unilateral p < 0,01. Control exacto ≥ 99 %.
Hay veinte unidades experimentales; las consultas no se tratan como réplicas
independientes. Bootstrap: 10.000 remuestreos, semilla 46099. Las demás cargas
y corrupción se informan como curvas descriptivas, sin cambiar la variable
primaria al ver resultados. Si no hay separación, el contrato queda negativo.

Métricas: top-1, top-5, rango recíproco medio, margen correcto frente al mejor
competidor, ocupación, contadores en 255, máximo de contador, error de score
frente al control exacto, CPU de ajuste/consulta, bytes del vector y RSS.
C95 se acota entre cargas medidas; si 500k no cruza el umbral se informa una
cota inferior. No se extrapola a número de tareas ARC almacenables.

Se ejecutan primero las dos primeras semillas para calibrar duración y después
se completa el mismo plan. Un proceso nuevo repite ambas semillas y compara
los resultados deterministas; CPU/RSS no necesitan coincidir. Los diarios de
desarrollo usan `echo_arc.observe.Journal`. El perfil registra fuentes, plan
y Python. No se modifica ninguna fuente S6 ni del candidato V2.

Extensiones con contrato propio: grafos canónicos, invariancia a renumeración
de nodos, grafos no vistos y control uint16 para separar clipping de
interferencia. Un verde de microbanco no cierra ECHO-4.5.
