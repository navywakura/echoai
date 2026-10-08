# E4-SELF-1 — inicio: cambio observable antes de atribución

2026-09-21. Autorización: empezar E4-SELF-1 tras BOUNDARY. **En desarrollo,
no cerrado.** No modifica WORLD/SENSATION/BOUNDARY ni SELF-1 histórico.

## Pregunta y etapas

Cuando una consecuencia deja de coincidir con su experiencia, ¿ECHO puede
distinguir una alteración del actuador de un cambio externo, conservar el
conocimiento no refutado y recuperar una conducta útil?

1. **SELF-A, este entregable:** monitor de cambios respecto a experiencia
   nominal, sin reescribirla; auditoría de identificabilidad con los sensores
   actuales. No atribución positiva de cuerpo/entorno ni recuperación todavía.
2. **SELF-B, pendiente:** hipótesis contrastables de causa propia, externa,
   mixta o desconocida; selección de intervenciones que separen hipótesis.
   Ningún empate se convierte automáticamente en «externo».
3. **SELF-C, pendiente:** diagnóstico que cambia conducta, gate intacto,
   recuperación y preservación selectiva del modelo frente a controles.
4. **Examen y cierre, pendiente:** contrato final de dominio/umbrales,
   B/C nuevos, ablaciones, regresiones y auditoría completa en proceso nuevo.

El cero de un contraste no prueba que nada físico haya cambiado. Incluso
con recibos de restauración válidos, la cuantización puede ocultar causas
distintas. La auditoría debe encontrar y publicar esas equivalencias, no
exigir al agente que acierte una etiqueta que sus entradas no determinan.

## SELF-A: API y memoria

Se reutiliza la misma instancia `BoundaryMap` y su CAM. Cada fila nominal
`(slot CAM, acción)` conserva una firma de ocho enteros: cuatro cambios
del brazo wait (U/B, t=1/2) y cuatro contrastes acción-versus-wait. Conserva
también tick de aplicación, número de muestras y conflicto. Máximo 128
filas y 4.096 pares de calibración; no segunda CAM/T ni lista de episodios.

La firma sale exclusivamente de los WSP de 16 bytes y recibos públicos
de BOUNDARY. Sin H/theta exactos, reglas, acoplamientos, semilla o etiquetas.
No usa coordenadas del SELF-1 del cubo, no añade átomos WSP ni hechos CAM.

Ocho repeticiones concordantes y BOUNDARY suficiente autorizan comparar,
no declarar una causa. Una contradicción nominal invalida la fila; no se
promedia hasta esconderla. `seal()` congela esta referencia y BOUNDARY.
No afirma congelar T/Q del Agent vivo: este slice no interviene en su loop.

La consulta valida antes de actuar y no escribe en CAM/T/Q/mapa nominal.
Devuelve máscaras de **deriva de referencia cambiada** y **contraste de
acción cambiado**, bytes conocidos/desconocidos y motivo. La atribución
de origen sigue siendo `unknown`, incluso si ambas máscaras son no nulas:
cambios en códigos sensoriales no equivalen a causas físicas separadas.
Un par actual aislado solo demuestra una discrepancia observada, no su
replicación futura. Tick de aplicación diferente, recibo inválido, contexto
desconocido, cambios semánticos no soportados o calibración conflictiva
obligan a abstenerse. No se presupone identidad del estado oculto a partir
de un WSP idéntico entre calibración y consulta.

## Auditoría prospectiva de identificabilidad, no examen de cierre

Enumeración determinista declarada **antes de ejecutar**:

- H inicial 29..40, temperatura 40..72: 396 estados físicos.
- Acoplamiento H/temperatura: ambos, solo H, solo temperatura, ninguno.
- Calor externo común: -16, -4, 0, +4, +16, en t=1.
- Acciones 0 y 1, cada una frente a wait; horizonte original de dos ticks.
- Referencia nominal con ambos canales acoplados y calor externo cero.
- Ocho pares nominales por acción/estado; después, monitor congelado.

Son 7.920 condiciones físicas (396 × 4 × 5), 15.840 consultas posteriores.
La verdad privada clasifica nominal / propio / externo / mixto por los
parámetros de la intervención; esas palabras nunca llegan al monitor.
Se usa el ejecutor original de BOUNDARY y el mismo encoder, sin ampliar
sensores, cambiar su física ni autorizar acciones tras terminalidad.

Agrupar por **todos los paquetes públicos**, no solo las máscaras:
referencia nominal y resultado actual de ambos brazos, intención,
ejecución, gate, timestamps y recibos de restauración. Se normalizan solo
IDs de ensayo opacos que no transportan causa. Comparar la información
de una sola acción con la de ambas acciones desde restauraciones explícitas.
Una clase con varias causas físicas es un contraejemplo de identificabilidad
en este protocolo finito, no una prueba de imposibilidad con todo sensor
o toda secuencia de acciones futura.

Informe: distribución de causas, clases públicas, clases con etiquetas
incompatibles, condiciones afectadas, cota de aciertos del mejor clasificador
determinista sin abstención en este banco equiponderado, testigos completos,
salidas del monitor y conservación exacta de su referencia/CAM.
La cota es descriptiva del banco, no probabilidad universal ni resultado
del agente. El auditor puede guardar trazas; el monitor no.

## Criterios de este primer entregable

- Todas las condiciones y ambos brazos contabilizados; cero ejemplos omitidos.
- Al menos un testigo público idéntico con causas privadas incompatibles;
  reproducción de testigos contra el ejecutor, no igualdad por etiqueta.
- Monitor detecta los cambios de códigos que se comprueben directamente
  en la traza, sin llamar a eso «yo», «externo» o «mixto».
- Fuente nominal/CAM byte-idéntica tras consultas; límites, orden de fases,
  duplicados y entradas inválidas probados; cero hechos falsos/destrucción.
- Integración opt-in con Agent/SENSATION/BOUNDARY existentes, sin alterar Q
  ni sus acciones. Los certificados anteriores siguen verificando.
- Pruebas y replay reproducible del informe. `self1_green=false` siempre
  en SELF-A; una auditoría técnicamente válida no cierra la fase completa.

## Qué deberá exigir el cierre completo

Acertar etiquetas no bastará: harán falta recuperación conductual medida,
preservación del conocimiento no refutado y ventaja frente a controles
«todo es propio», «todo es externo» y sin atribución. Deben incluirse causas
mixtas, mecanismos fuera de desarrollo, datos insuficientes, contradicción,
vetos y perturbaciones que inicialmente se parezcan. Las clases que sigan
siendo indistinguibles requieren desconocido, no aciertos por oráculo.

Los umbrales cuantitativos de atribución/recuperación se fijarán antes de
abrir ese nuevo examen, después de decidir intervenciones identificables.
No se reutilizará este barrido como B/C reservado ni se promocionará SELF-A
por haber escrito un campo llamado «self». Sin hardware ni METAVERSE-1;
hardware tras software y METAVERSE-1 último. Nada de esto acredita conciencia.
