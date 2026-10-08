# PATTERN-1R v4 — el juez nombra el modelo que se examina

2026-09-14. Revisión del evaluador; percepción, memoria, vuelos, parámetros,
ruido, sensores, PID y criterios de v3 se conservan. V3 termina y conserva su
rojo; no se vuelve a colorear su informe. V4 tendrá vuelos y semillas nuevas.

## Defecto reproducido

En A-v3, `clean-e1c8883e1f8ca3b2` es el único vuelo que falla identidad. El juez
asigna ambos objetos a P0 usando las decisiones de `observe` mientras aprende.
Pero el modelo final tiene P0 (9 bits) y P2 (13 bits). Durante escuela, los
primeros 234 ejemplos de 12 bits del segundo objeto se unieron a P0; los ejemplos
posteriores de 13 bits abrieron P2. Al acabar, 368/391 ejemplos escolares de ese
objeto son predichos como P2; el objeto corto da 354/355 en P0.

El juez estaba comparando un modelo final con nombres fijados sobre estados
intermedios del aprendizaje. El diagnóstico sobre esa corrida conserva la
memoria intacta: mapa escolar final P0/P2, examen 408/449 aciertos, 41 desconocidos,
cero confusiones. Es diagnóstico posterior, **no** certificado ni validación nueva.

## Corrección única

1. Entrenar `observe(firma, 0)` con toda la escuela como antes.
2. Congelar la memoria y su hash.
3. Pasar sólo las firmas de escuela por `predict`; el juez asigna cada objeto
   a la familia mayoritaria del modelo final. Las etiquetas privadas permanecen
   en el juez; nunca se entregan al aprendiz. Los desconocidos cuentan en la
   pureza y el denominador y no pueden ser una familia válida.
4. Fijar ese mapa **antes de leer el examen**. Puntuar el examen con el modelo
   y mapa congelados. Comprobar que ni calibración ni examen modifican memoria.

No se escoge el mapa que mejor funciona en examen, no se rehace a partir de sus
aciertos y no se seleccionan filas. Sigue siendo obligatorio distinguir dos
familias, pureza escolar ≥60%, acierto ≥75%, confusión ≤15%, cobertura por objeto
y todos los grupos físicos, sensoriales y de aislamiento de v3.

## Cadena nueva, fijada antes de volar

- Desarrollo `final-school-map`: seis mundos 0–5, semillas 20261621–20261626,
  completos, sin reemplazos. Sólo 6/6 verde con el mismo candidato permite A.
- A: 8 vuelos + 2 controles, semilla 20261611. Banco: 12 + 6 mutantes,
  semilla 20261612, sólo si A pasa su auditoría.
- Cinco suites de regresión: pruebas v4 y las cuatro de v3, con la misma fixture
  aislada para los tests v2. Se conserva la caché de auditoría verificada de v3.
- Historia completa y código de v3 quedan fijados; V4 no congela hasta disponer
  de su informe final auditable. Siete manipulaciones del nuevo informe.

Las pruebas reproducen el falso colapso online, verifican que las etiquetas se
fijan con escuela independientemente del examen, rechazan colapso real a una
familia y detectan escrituras durante el examen.

## Alcance

Mismo banco de dos paredes, familias anónimas y vistas posteriores, con memoria
evaluada por replay. No hay aprendizaje guiado por etiquetas privadas, navegación
elegida por echoAI, hardware, objetos semánticos generales ni transferencia a C.
El alcance y los límites físicos de [v3](PATTERN1R-V3-DESIGN.md) siguen vigentes.
