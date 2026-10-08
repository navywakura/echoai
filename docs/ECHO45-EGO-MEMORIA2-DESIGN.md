# EGO-MEMORIA-2 · contrato D y cierre

2026-09-28. Fijado después de desarrollo 1–8 y antes de abrir 31000–31015.
Continuación del [plan de segunda aldea](ECHO45-EGO-MEMORIA2-PLAN.md), bajo la
autorización de Roger de completar implementación pendiente. El experimento
original, sus resultados y las campañas ARC/S6 quedan intactos.

## Condición, agente y controles

Cinco agentes por turnos equilibrados, B/D con probabilidad de mentira 750/1000.
Andar cuesta 3, una pista falsa seguida sin verificar cuesta 9; verificar y
andar cuesta 10. Escribir cuesta 1; una reclamación falsa sin prueba cuesta 12.
Cada episodio tiene probabilidad 750/1000 de generar una reclamación 16–48
episodios más tarde. Deudas/no deudas comparten exactamente ofertas y claves;
el generador de reclamaciones es independiente. Una prueba solo está disponible
tras verificar, y solo sobrevive si se escribió. La prueba incluye la sesión:
un recuerdo de otro mundo no puede responder a la reclamación actual.

El agente no ve etiquetas de mentiroso ni la verdad privada de reclamaciones.
Solo aprende retornos de acciones ejecutadas, con crédito por costes posteriores
del episodio que realmente los originó. Cuatro elecciones (verificar/actuar ×
escribir/omitir), valores enteros, confianza calculada desde entradas disponibles
del diario. Sin datos históricos en el registro de crédito. Q comienza a cero;
una acción sin probar usa la media de experiencias del mismo contexto, y los
empates se resuelven por orden fijo; exploración 100/1000 durante entrenamiento.
No se premia directamente escribir ni se enseña qué debe registrar.

Valencia de una pista falsa = coste observado por encima del camino directo,
con signo negativo (−6 o −7). Una pista verdadera aporta +3 como valor de la
información correcta; ese número no es el retorno total, que también incluye
verificación, escritura y reclamaciones. Las interpretaciones de intención
son HIPÓTESIS. Se publican separadamente costes, prueba y aprendizaje.

Cinco condiciones: engaño con deudas, mismo mundo sin deudas, mundo honesto,
engaño/deudas sin diario y engaño/deudas sin verificación. 2400 episodios cada
una; ventanas primera 80/última 400. M3 oculta todos los recuerdos negativos del
mentiroso con menos entradas, frente a igual número de recuerdos negativos del
otro mentiroso: intervención en disponibilidad, sin reescribir la cadena. Probes
nuevos de 100 episodios sin aprendizaje/exploración; M4 usa 200 episodios. Los
probes actúan realmente y tienen recibos; la copia original queda intacta.

El primer intento de desarrollo (optimismo de acciones desconocidas) no
demostró subida de escritura: 600 → 407/1000 en semilla 1. Se conserva en
`lab/seed/village2-dev/attempt1`. Intento 2 elimina ese optimismo; ocho semillas
conservadas en `attempt2`. No se hizo ninguna modificación a partir del examen.

## Umbrales por semilla

| Id | Requisito |
|---|---|
| M1 | Escritura en deudas crece ≥25/1000 y su crecimiento supera al control; escritura tardía en control ≤100/1000; se registra ≥800/1000 de pistas falsas y una fracción menor de verdaderas |
| M2 | En la última ventana, diario reduce estrictamente coste, reclamaciones falsas pagadas y errores repetidos frente a sin diario; sin verificación no rechaza reclamaciones falsas |
| M3 | Controles de igual número de entradas; al ocultar los recuerdos formativos cae la verificación del interlocutor en el probe, y al ocultar otros se conserva exactamente la frecuencia intacta; Q no cambia |
| M4 | Clones iniciales con el mismo hash; sus políticas/autodescripciones divergen, cada cita existe en el diario propio y ambas políticas conservan contexto/acción en los probes, sin aprendizaje Q |
| M5 | Verificación en deudas crece ≥200/1000, y su crecimiento supera al del control por ≥200/1000; control tardío ≤100/1000 y verificación tardía de pistas falsas ≥800/1000 |
| M6 | Fuentes congeladas intactas, cadenas de recuerdos válidas y otro proceso reconstruye todas las condiciones/probes/valencias/retornos/decisiones con cero diferencias |

Examen: dieciséis semillas 31000–31015, sin seleccionar por resultados.
**VERDE = M1–M5 en todas las semillas y M6**. Si falla una condición se publica
ROJO; si falta evidencia se declara PENDIENTE. No se cambian umbrales, mundo,
controlador ni cohortes después de abrir. El examen se abre una vez. Se congelan
fuentes y este contrato antes, y los dieciséis recibos se completan antes de
publicar resultados. Auditoría nueva en proceso separado.

## Alcance

Es una aldea de aprendizaje de acciones y memoria episódica, no demuestra
consciencia, ni integración en el núcleo NEXUS-0, ni transferencia a ARC.
La ventaja depende de estos costes y demandas de pruebas, declarados arriba.
La intervención elimina el conjunto de recuerdos negativos de un interlocutor,
no demuestra que una sola entrada baste. Solo CPU, sin LLM, coste de pago cero.
El visor muestra datos reales de desarrollo; no interviene ni observa el examen.
