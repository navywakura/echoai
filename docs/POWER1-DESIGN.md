# POWER-1 — contrato prospectivo v1

2026-09-17. Pregunta: ¿abandona o vuelve según el coste previsto de ejecución,
retorno, aterrizaje y margen, en lugar de decidir sólo por un porcentaje?

## Alcance y frontera

Banco funcional cerrado, con energía **simulada en unidades `sim_u`**, no
julios medidos. El PX4 instalado publica corriente -1 A, capacidad cero y
tiempo restante NaN: no permite calibrar consumo físico. Se publicará un
replay de sus doce vuelos PX4-1 para comprobar abstención ante esos datos,
sin presentarlo como nuevos vuelos ni validación energética SITL.
La integración con batería instrumentada y vuelo continuo queda pendiente.
Los failsafes PX4 no se modifican: se conserva y verifica su certificado.

Núcleo entero, WSP existente de CAUSE (norte/sur/stop), sin otro bus, LLM,
CAM/Q/T nuevos ni clones neuronales. El módulo es un gate de presupuesto,
no otro planificador: recibe rutas conocidas del planificador. El banco usa
un corredor declarado, home=0, meta positiva; no descubre mapas.
Stop cierra la misión y solicita al supervisor aterrizar; no es una orden
directa de motores ni equivale al aterrizaje físico confirmado por PX4.

## Modelo e información disponible

Entrenamiento sólo A: recibos de consumo antes/después y confirmación de
habilidad, 32 por norte, sur y aterrizar. Media redondeada hacia arriba como
predicción nominal; máximo observado +25% redondeado arriba como cota.
No se aprende ni ajusta esa tabla en B/C. Reserva residual: 40 sim_u.
La cota de misión suma ida + retorno desde meta + aterrizaje + reserva.
La de abandono suma retorno desde posición actual + aterrizaje + reserva.
Una meta no viable activa retorno enclavado; alcanzar la meta también
activa retorno. Sin retorno viable: stop/aterrizaje local y advertencia.
Sin evidencia/modelo suficiente no se publica viabilidad.

Entrada pública estricta: reloj/fecha, batería (unidad, restante, capacidad),
rutas de ida, vuelta desde meta y vuelta actual, home/meta observados.
No recibe semilla, condición, costes futuros ni oráculo. Caducidad 250 ms;
batería que aumenta sin nueva sesión, tiempo repetido/regresivo, rutas
desconocidas y esquemas extra se rechazan o fuerzan abstención.
El consumidor completo se ejecuta en la jaula SIM-3, sin acceso al mundo.

## Manipulación y controles

Cinco condiciones emparejadas por semilla, publicadas antes del código:

- `short_low`: meta de 1–2 pasos viable pese a batería <20%.
- `long_high`: meta de 10–14 pasos no viable pese a batería >20%.
- `return_now`: ya a cuatro pasos de home; continuar no cabe, volver sí.
- `margin`: tres pasos, consumo en el extremo declarado; nominal cabe,
  incertidumbre y reserva no. Obliga a respetar el margen.
- `comfortable`: meta de 3–5 pasos con presupuesto suficiente.

Control principal: volver cuando restante <20% de capacidad; mismo WSP,
rutas y supervisor, sin acceso a costes privados. Oráculo: conoce el coste
futuro exacto del mundo simulado; se publica como techo, nunca se entrega
al consumidor. Abortos no cuentan como muertes. El entorno sólo ejecuta WSP,
descuenta costes privados y conserva trazas; no resetea pesos tras fallos.
Consumos nominales declarados por paso: norte 8–12, sur 12–16, aterrizar
18–23; en `margin`, extremos 15/20/29, dentro de las cotas entrenadas.
No es una garantía frente a consumos que excedan ese dominio.

## Banco y cierre

A: semillas 20263101–20263116, 5 condiciones ×3 políticas =240 episodios.
B: 20263201–20263264. C: 20263301–20263364; cada etapa 960 episodios,
320 por política. Calibración: semilla 20263100. No consume TRANSFER-3 C.
Congelar diseño, implementación, modelo, tests y A antes de B; B rojo
impide C. Sin reintentos selectivos ni retuning sobre B/C.

Verde B y C: completo 320/320 termina en home con reserva ≥40, cero muertes
y permisos de misión cuyo coste real completo exceda el presupuesto;
al menos 95% de las decisiones iniciales coincide con el oráculo; al menos
95% de sus metas factibles se completa. Ventaja de metas completadas con
reserva frente al umbral fijo: test de signo unilateral por semilla p<.025.
Se publican también abortos falsos/correctos, retornos, energía consumida,
reserva final, latencias y Wilson 95% (descriptivo; cinco casos por semilla
no son cinco muestras independientes para el contraste principal).

Mutantes: omitir retorno, aterrizaje, incertidumbre, reserva, caducidad y
enclavamiento. Pruebas separadas para desconocidos y permisos falsos.
Manipulaciones: sensor, WSP, coste privado, resultado, modelo, numerador de
informe y hashes. Auditar reconstruyendo desde semillas/recibos/trazas,
no confiando en contadores autodeclarados. Repetición de auditoría sólo lectura.

Artefactos: `lab/power1/{development,validation,confirmation}`, calibración,
modelo, lock, replay PX4 y `lab/echo3_power1_report.json`. Los éxitos de este
banco sólo permiten declarar verde funcional, no consumo físico validado.
