# COMPOSE-1 v3 — prefijos comparables

Diseño antes del examen. V2 se conserva congelado: 768 misiones B válidas,
64/64 metas alcanzables para completo y horizonte uno, 108 movimientos menos
con el completo. IC 97,5 % del ahorro medio [0,375; 3,03125], pero el test de
signos dio p=0,0297317 frente al límite p<0,025. C funcional y los vuelos de
aceptación v2 no se abrieron. No se cambia ese rojo ni el umbral.

## Cambio e hipótesis

V2 sólo valoraba hojas y sumaba profundidad al coste de revisitas y distancia.
El final de una rama corta podía resultar favorable sin que los cuatro pasos
ofrecieran un medio mejor. V3 considera prefijos y normaliza el regularizador
de profundidad al horizonte de la búsqueda: distancia restante ×10 + visitas
observadas acumuladas ×20 + horizonte. En empate prefiere el prefijo más largo.
Una llegada prevista conserva prioridad y coste por longitud. Ordena la cola
con distancia e historial y evita ciclos dentro del camino, sin confundir un
estado explorado por otra rama con un efecto físicamente imposible.

Esto es una heurística de búsqueda, no una estimación de julios ni una promesa
de optimalidad. La normalización no genera órdenes de espera ni carga energía
imaginaria al cuerpo. El gate mantiene la comprobación explícita de reserva.
El resultado sólo elige el siguiente movimiento; se replantea después de cada
observación. T sigue siendo necesaria para los efectos y no aprende en B/C.

Dos candidatos se declararon y midieron sobre las 32 semillas A originales:
orden por coste acumulado y prefijos de horizonte comparable. Se guardaron
todos los resultados en `lab/compose1-v3/development/algorithms-1/`, junto con
el código. El segundo se seleccionó con A: 8 ventajas, 1 desventaja y 7 empates
frente a horizonte uno, 44 movimientos ahorrados. El p de selección no es
evidencia independiente; el cierre depende de B y C nuevos.

## Contrato conservado

Se conserva [la especificación física y estadística de v2](COMPOSE1-V2-DESIGN.md):
WSP único, modelo T/Q/CAM, mapa inicial vacío, sensores públicos en proceso
aislado, envolvente y margen, PX4 y su imagen fijada, 250 ms de caducidad,
altura 2,5 m, salas extruidas, marcador proporcionado y energía abstracta.
Mismos seis modos funcionales, presupuesto 8/32, máximo horizonte 4 y 64
movimientos. Horizonte uno cambia únicamente profundidad. No se amplían LIF,
no se activa LLM y no hay hardware. Tampoco se consume C de TRANSFER-3.

La escuela física conserva exactamente el modelo y las 56 consecuencias de
`compose1-v2/sitl-development/live-1`; se referencia esa carpeta histórica.
Los archivos de v2 no se editan. V3 tiene su propio inventario y certificado.

## Examen previo al lock

- A: mismas 32 semillas funcionales y los diez vuelos de desarrollo de v2,
  repetidos completos con la nueva búsqueda; cada intento queda conservado.
- B funcional: 202621101–202621228, 128 semillas ×6 modos =768 misiones.
- C funcional: 202622101–202622228, otras 768 misiones.
- Familia de 48 geometrías muestreada con reemplazo, como v2; no se afirma
  que una semilla nueva sea una planta nueva.
- B SITL: 202619301, 202619303, 202619304, 202619305.
- C SITL: 202619403, 202619404, 202619407, 202619408.
- Condiciones físicas: estática, estática, dinámica, reserva insuficiente;
  cuatro modos por sala, 32 vuelos en total. Son las geometrías preregistradas
  de v2, cuyo examen físico quedó sin abrir; no se seleccionan otras fáciles.

Mismos umbrales: cero violaciones en el completo funcional; ventaja frente a
Q; IC 97,5 % con límite inferior positivo y test de signos p<0,025 en éxito
o ahorro entre parejas exitosas, sin pérdida agregada de éxito. Ambas etapas
funcionales deben pasar. Físico: todos los vuelos con evidencia y ejecución
válidas; completo ≥5/6 metas alcanzables y más llegadas que Q; aborto en origen
para la reserva insuficiente. No hay reintentos selectivos ni aumento de N.

Se repiten los controles negativos sobre una misión A válida, la regresión y
el aislamiento antes de congelar. Auditoría posterior en proceso nuevo. V3
sólo cerrará COMPOSE-1 si ambas puertas y su auditoría pasan; CAUSE-1 va después.
