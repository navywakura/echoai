# S6: piloto condicionado de evidencia y diversidad

2026-09-28. Ejecutor preparado; ninguna llamada al modelo antes de que cierre
el control manual con una reparación que pase V1–V4. No abre un examen ni
cierra S6 VERDE. El contrato se congela antes de generar respuestas.

Modelo y revisión B4, gramática local intacta, temperatura 0,7 y top-p 0,95.
Tres semillas de muestreo (602001, 602017, 602029), emparejadas FIJO/ECHO;
dos propuestas por brazo y semilla: seis por brazo. Dos calibraciones locales,
**14 llamadas máximas**. Una sola carga del modelo, GPU gratis, límite 900 s.
No activar pago. Si la cuota no alcanza, parar antes de subir el trabajo.

Los prompts se componen del diario B4 de A y sus rechazos, incorporando
activaciones y acciones cambiadas realmente medidas. FIJO mantiene su petición
genérica sobre tres fallos; ECHO elige tipos/episodios con su selector existente.
Se reutiliza su estadística histórica de peticiones fallidas, sin reparaciones
aceptadas. La explicación común del momento de aplicar un parámetro es igual
para ambos. **Ningún candidato humano, ganador o resultado de la búsqueda
manual se incorpora al prompt ni a las fuentes entregadas al modelo.**

Los prompts se fijan antes de inferir; este piloto no prueba adaptación de la
petición entre sus dos propuestas. Cada semilla inicia ambos brazos desde el
mismo ECHO vacío; durante la verificación se componen solo parches aceptados.
Los datos son desarrollo ya utilizado: A 0–19, B 20–39, v2/v3, 2000 decisiones.
Se conservan V1–V4, ganancia mínima +2, ninguna regresión individual A/B y
replay completo exacto A/B. Presupuesto máximo 2720 partidas; una partida
completa por medición visible en el diario ARC existente, observador ya probado.

Promover a un contrato nuevo de campaña solo si ECHO acepta al menos una
reparación y supera a FIJO en la suma de niveles A de las tres repeticiones.
La diversidad se publica aunque no haya promoción; tener propuestas distintas
no equivale a una mejora. El presupuesto final de campaña y su cohorte ciega
deben congelarse después; no se reutiliza como ciega una cohorte abierta.
Este piloto compara dos modos de petición; SEMILLA y SIN FILTRO corresponden
a la campaña posterior de cuatro brazos, no a una certificación en este piloto.

Se conservan fuentes y entradas, semillas, payloads, respuestas parciales,
contabilidad, resultados y replays. Un fallo GPU detiene la verificación sin
aceptar respuestas incompletas. Se usa el prefill por bloques y caché dinámica
explícita ya ensayados por la recuperación B4; no se truncan prompts.

```
lab/arc3/ARC-AGI-3-Agents/.venv/bin/python -m seed.s6_prompt_pilot prepare
lab/arc3/ARC-AGI-3-Agents/.venv/bin/python -m seed.s6_prompt_pilot run
```

`run` exige primero `s6-capacity-20260928/summary.json` positivo e íntegro.
No se lanza este piloto si la búsqueda manual termina sin control positivo.
`follow` espera el cierre del control en segundo plano y ejecuta el piloto solo
si pasa; en otro caso publica SKIPPED y cero llamadas. Las fuentes propias se
congelan antes de activar esa espera; no se adapta el piloto al ganador humano.
