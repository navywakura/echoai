# Recuperación ECHO-4.5 · 29 de septiembre de 2026

Trabajo autorizado por Nav: completar lo posible de EGO-MEMORIA y S6,
conservar los umbrales y registrar también los negativos.

## Memoria: cierre VERDE de la condición 3E

- **3A**, retornos de edad homogénea a 64 episodios: M5 24/24, M1 23/24;
  coste agregado +1333 frente a base. No promovido.
- **3B**, separar costes de navegación, escritura y reclamaciones: M1–M5
  24/24; coste agregado +1370. No promovido por el criterio adicional de coste.
- **3C**, cerrar el retorno al concluir el plazo público de reclamaciones:
  menor coste agregado (−1114), pero M5 23/24. No promovido.
- **3D**, exploración decreciente: coste agregado −9840, pero M1 23/24
  (escritura excesiva de pistas verdaderas). No promovido.
- **3E**, agrupar reclamaciones por existencia real de prueba conservada:
  M1–M5 24/24 en desarrollo y coste −15324. Examen nuevo M1–M5 16/16 y
  M6 exacto 16/16: **VERDE**. [Cierre](ECHO45-EGO-MEMORIA3-RESULTS.md).

Las comparaciones 3A–3E anteriores son desarrollo publicado con todos sus
datos; solo 3E abrió después su examen reservado nuevo de dieciséis semillas.
Las revisiones descartadas NO abrieron la reserva.
Mundo, costes y verificadores M1–M5 originales no se reescribieron.

## S6: B5 cerrado; revisión B6

B5 sigue cerrado sin promoción. B6 añade explicación exacta del consumo de
parámetros y recuperación de puntos reales de decisión desde los 40 diarios
de SEMILLA en A. No usa soluciones humanas ni datos de B en los prompts.
Doce propuestas y dos calibraciones Qwen en Kaggle privado; inferencia terminada.
B6 termina sin promoción: ECHO 534 frente a FIJO 537; cero aceptaciones ECHO.
La propuesta +8 A falla conservación B. Auditoría independiente completa: 12 veredictos reconstruidos y fuentes intactas.
B de desarrollo: 24320–24339. No abre examen.

[B7](ECHO45-S6-B7-DESIGN.md) añade una propuesta por pareja desde sus propios
veredictos reales, ocho llamadas nuevas contando calibración. Cerrado y auditado:
una aceptación ECHO, suma A 537 frente a FIJO 537; sin promoción. Seis veredictos
nuevos reproducidos, fuentes separadas y sin resultados B en los prompts.
Promoción exige aceptación ECHO y suma A estrictamente superior a FIJO.

La GPU sigue gratuita y el pago desactivado. No se programa una campaña completa
sin promoción. Que un piloto sea positivo tampoco cumple B1–B5 finales.

## Cierre total ECHO-4.5

Memoria está verde en su condición 3E. S6 debe superar SEMILLA/FIJO/SIN FILTRO,
conservar habilidades y pasar auditoría. ARC-2 y ARC-3 conservan sus fallos del
examen final anterior; no se presentan como resueltos por mejorar esta aldea.
No se han abierto ni instrumentado exámenes antiguos ni modificado NEXUS-0.

Fuentes y recibos:
- [Memoria 3E](ECHO45-EGO-MEMORIA3E-DESIGN.md).
- [Piloto B6](ECHO45-S6-B6-DESIGN.md).
- [Datos 3E](../lab/seed/village3-receipts-20260929/).
- [Datos B6](../lab/seed/s6b6-20260928/).

## Hipótesis siguiente para S6, aún sin medir

El cuello de botella actual es seleccionar una reparación útil que generalice:
ocho propuestas B6 conservaron el HOLD nativo y no cambiaron acciones; una
mejora mayor en A perdió conservación B. B7 recuperó una mejora válida, pero
la suma de ECHO empata con FIJO. Más propuestas por sí solas no demuestran
que ECHO sepa pedir mejor.

Propuesta: un selector de peticiones que use **aplicabilidad y efecto observado
en A**. Antes de pedir una corrección, identifica dónde se consume el parámetro,
si la guarda se activa y qué acciones cambian; después presenta al modelo el
fallo concreto y el resultado de su intento previo. Esos diagnósticos deben
proceder del ejecutor, sin guiarse por puntuaciones ni estados protegidos B.
Una variante sin selector y otra sin feedback permiten separar ambos aportes.

No es todavía un contrato ni una mejora acreditada. El próximo contrato debe
fijar de antemano cohortes, presupuesto total (incluidos diagnósticos y reintentos),
paridad de información permitida, promoción y auditoría. Si el lenguaje de
reparaciones se amplía, ambos brazos reciben el mismo lenguaje. Se conservan
B1–B5 y un examen final nuevo solo se abre tras superar el piloto.

## Cierre de S6 de esta sesión

S6-B6/B7 cerrados y auditados; B7 ECHO 537 frente a FIJO 537, aceptaciones ECHO 1; sin promoción; examen final sin abrir. [B6](ECHO45-S6-B6-RESULTS.md) · [B7](ECHO45-S6-B7-RESULTS.md).

## Validación y alcance del cierre

28 pruebas unitarias distintas pasan entre los módulos de memoria y S6.
Memoria 3E reproduce las dieciséis semillas reservadas y todas sus sondas en
un proceso independiente. S6 reconstruye los doce veredictos B6 y seis B7,
con comprobaciones adicionales de procedencia de inferencia y composición
de políticas. Los perfiles de las condiciones previas se conservan.

No queda medición ni auditoría de esta iteración pendiente. Los visores de
observación pueden permanecer abiertos; no son campañas experimentales.
El resultado agregado se guarda en
[recovery-20260929-closure.json](../lab/seed/recovery-20260929-closure.json).
