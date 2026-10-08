# S6-B8-CPUQ8 · continuación numérica separada

29 septiembre 2026. Registrado antes de respuestas Q8. Se heredan únicamente
las doce propuestas GPU auditadas de B8, conservando sus veredictos. La reserva
24500–24559 no se ha abierto. No utiliza resultados ni propuestas del control
humano nuevo sobre transiciones; sus seis peticiones p2 siguen siendo las
originales de B8, con sus semillas, mismos V1–V4 y B1–B5.

Motivo: la continuación CPU float16 tardó 1315 segundos en completar la primera
petición tras cargar pesos. Seis peticiones no cabrían en el límite de 3600 s
si mantuvieran ese ritmo. Su primer resultado no se ha evaluado ni usado para
escoger esta condición. Se conservará esa ejecución hasta su límite y sus
respuestas parciales, sin mezclarlas con Q8 ni llamar completo a ese piloto.

**Nuevo backend explícito, no equivalencia numérica:** la misma revisión
`Qwen/Qwen2.5-Coder-7B-Instruct@c03e6d358207e414f1eca0bb1891e29f1db0e242`
se carga desde los cuatro shards con hashes verificados y transforma todos
los Linear ordinarios a cuantización dinámica int8 de PyTorch, motor fbgemm.
El resto de parámetros opera en float32. Se convierte una capa por vez para
evitar una copia inicial float32 completa. Dispositivos, capas transformadas,
versiones y revisión quedan registrados; sin GPU ni pago. Cuatro hilos.
Antes de cargar el modelo grande, un Qwen2 minúsculo con pesos aleatorios
debe generar dos tokens tras la misma conversión. Es una comprobación de
infraestructura sin tareas ni pesos entrenados; no es una propuesta S6.

Ambos brazos usan exactamente este backend en la tercera ronda y en cualquier
campaña posterior. Las dos rondas heredadas usaron GPU float16; se declara esa
historia. Los resultados no representan repetir íntegramente B8 GPU, ni B8 CPU
float16. La cuantización podría cambiar la calidad de las propuestas; se mide,
no se presupone equivalencia. Esta condición se eligió por viabilidad antes de
ver su rendimiento; no se elegirá retrospectivamente la mejor variante numérica.

Presupuesto lógico: 18 propuestas piloto más dos calibraciones heredadas;
si promueve y pasa auditoría, campaña desde parche vacío de 60 propuestas más
dos calibraciones. 82 llamadas lógicas con la historia, hasta siete trabajos
CPU nuevos de 3600 s cada uno, sin reintentos automáticos fallidos. Los intentos
fallidos y parciales de otras condiciones se contabilizan aparte y se conservan.

Promoción exige aceptación ECHO y suma A estrictamente mayor que FIJO. Solo
piloto y campaña auditados autorizan cuatro brazos y conservación oficial.
Se comprueba que ninguna condición anterior abrió esa reserva antes de hacerlo.
Un empate, regresión o fallo de auditoría no se etiqueta VERDE.

[B8](ECHO45-S6-B8-RESULTS.md) · [CPU float16](ECHO45-S6-B8-CPU-DESIGN.md).
