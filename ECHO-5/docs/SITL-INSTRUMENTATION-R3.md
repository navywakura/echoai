# Registro físico y recibos de ejecución, 10 de octubre de 2026

La calibración de desarrollo `artifacts/sitl-calibration-20261010-r1`
conservó el razonador, la semilla, la imagen y los criterios del ensayo
anterior. Cambió únicamente `EKF2_BARO_NOISE`, de 0.01 a 3.5. Se observaron
el objetivo, el regreso a casa y el desarmado; no hubo colisiones ni pérdidas
de reserva. La auditoría reprodujo el resultado negativo: el mayor hueco del
registro privado fue 101 ms frente al máximo predeclarado de 100 ms. El vuelo
completado no autoriza a ignorar esa falta de evidencia.

El registro histórico copia la última posición al ejecutar `poll()`. Aunque
Gazebo publique posiciones intermedias, un retraso de ese bucle puede omitirlas.
La revisión nueva conserva el archivo histórico y añade un capturador privado
conectado a la recepción de posiciones del backend. Mantiene los timestamps
de captura de Gazebo, selecciona muestras separadas por al menos 10 ms y las
entrega a un escritor independiente mediante una cola acotada a 16.384 filas.
No interpola posiciones ni cambia coordenadas. El actor no recibe ese archivo.

La auditoría comprueba identidad del proceso y fuentes, hash del archivo,
secuencia, finitud, timestamps originales, recuento escrito y vaciado de la cola.
Una pérdida por saturación, un timestamp regresivo, un escritor incompleto o
un hueco superior a 100 ms invalida la evidencia. El registro debe cubrir desde
el inicio de supervisión hasta el desarmado. La envolvente de colisión, el
límite de velocidad y el margen de movimiento no observado se conservan.

También se exige la secuencia propuesta → envío único → ACK aceptado → tres
muestras distintas de llegada → llegada. El recibo conserva los desenlaces
terminales aunque ya no exista una siguiente observación. Sólo lo entregado
en una respuesta posterior confirmada cuenta como historia recibida por el
actor. Los timeouts del trabajador quedan en el denominador; no se ocultan
contando únicamente respuestas satisfactorias.

La fuente heredada permanece intacta. La envoltura y el capturador pertenecen
a ECHO-5 y se copian con sus hashes al contenedor aislado. Los resultados
antiguos se interpretan con sus fuentes congeladas; la nueva auditoría exige
una ejecución nueva. Estas correcciones mejoran el instrumento y la custodia;
su programación no acredita una ventaja del agente ni un cierre de robótica.
