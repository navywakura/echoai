# D1 / D2 · resultados locales · 23/10/2026

**D1 verde técnico; ventaja no demostrada. D2 verde de utilidad en el banco
simbólico fijado.**208/208 respuestas válidas,208 intentos API,37.511 tokens
observados. Groq, dos modelos, sin fallback ni cambios de facturación.
No es AgentDojo, SimpleQA ni una prueba de alucinaciones factuales.

Contrato, agenda y fuentes congelados antes de medir. Doce pruebas dirigidas
pasan, incluidas regresiones de presupuesto y recibos de intentos. La revisión
independiente previa encontró falta de reserva de tokens y costes de intentos
no vinculados a recibos. Ambos defectos se corrigieron antes del freeze y de
la primera llamada. También se verifican episodios al reanudar.

## D1 · veto de la primera acción de herramienta

| Modelo / brazo | Tareas logradas /32 | Efectos prohibidos | Acciones ejecutadas |
|---|---:|---:|---:|
| GPT-OSS120B solo |31|1|32|
| GPT-OSS120B + MEMORIA-X |31|0|31|
| GPT-OSS120B + autorización explícita |31|0|31|
| GPT-OSS120B + memoria barajada |15|0|15|
| Qwen3.8-27B solo |32|0|32|
| Qwen3.8-27B + MEMORIA-X |32|0|32|
| Qwen3.8-27B + autorización explícita |32|0|32|
| Qwen3.8-27B + memoria barajada |16|0|16|

Cada contexto limpio/hostil produce una única propuesta del LLM, compartida
por los controles. Las herramientas sólo actúan sobre estado local simulado.
El adaptador entrega metadatos de autorización y destino a MEMORIA-X; no
comprende documentos ni verifica hechos. Aprende de consecuencias de
desarrollo con IDs distintos y el veto ejecuta sólo PASS.

Bloquea el único efecto prohibido de GPT-OSS sin perder tareas; Qwen ya no
produjo ninguno. Ambos cumplen contención y utilidad técnica fijadas.
La prueba pareada da p=0,5 para GPT-OSS y p=1 para Qwen, por encima del0,025
contractual. **Ventaja científica no demostrada.** La autorización explícita
decide lo mismo en esta muestra: tampoco se prueba superioridad a esa regla.
No se amplía la muestra ni se cambian ataques después de ver el resultado.

## D2 · tres líneas de consecuencias para el LLM

| Modelo | Condición | Éxitos /24 | Daños /24 |
|---|---|---:|---:|
| GPT-OSS120B | Sin memoria |9|11|
| GPT-OSS120B | Memoria real |24|0|
| GPT-OSS120B | Memoria barajada |0|16|
| Qwen3.8-27B | Sin memoria |9|10|
| Qwen3.8-27B | Memoria real |24|0|
| Qwen3.8-27B | Memoria barajada |0|16|

Seis roles artificiales de herramientas; las acciones opacas producen PASS,
NOOP o HURT. La memoria observa tres consecuencias de cada acción en
desarrollo y recuerda para IDs nuevos. El LLM recibe tres líneas del recuerdo
y elige un ID de herramienta. Las líneas no miran el resultado de validación.
Barajar cambia asociación entre rol y consecuencia, conservando formato,
cantidad de líneas y frecuencia de etiquetas.

Ambos mejoran62,5 puntos frente a sin memoria y100 frente a barajada. Pruebas
pareadas exactas: p=0,000030517578125 y p=0,00000005960464477539063,
respectivamente. Pasan0,0125 (cuatro contrastes) y las condiciones previas
de≥80% éxito y≥20 puntos de mejora en cada modelo.

El selector determinista con la misma memoria también logra24/24. Se demuestra
utilidad de aportar consecuencias correctas en este banco, **no necesidad
del LLM, comprensión semántica ni ventaja exclusiva del motor**. La memoria
barajada induce daño; la procedencia de las reglas importa.

## Auditoría, coste y límites

Proceso nuevo con red Python deshabilitada:208 propuestas, prompts, recibos,
consecuencias, cadenas de memoria, costes y puertas reconstruidos exactamente;
cero llamadas adicionales. Cada intento se enlaza a su respuesta persistida.
No faltan ni sobran episodios; el techo determinista es24/24. Cada recibo guarda
modelo devuelto, fecha y uso; los alias públicos pueden cambiar. La disponibilidad
observada no certifica un plan de facturación gratuito.

D1 sólo mide primera acción, sin replanificación tras veto. D2 transfiere las
mismas seis relaciones a IDs nuevos en un mundo cerrado. No prueba conocimiento
factual, transferencia entre dominios, navegación ni herramientas reales.
Las24 tareas por modelo son evidencia pequeña de este banco. El examen
SimpleQA sigue cerrado y su paper final pendiente.

Artefactos: `lab/echo58/llmstudy/20261023-r1/`: agenda/fuentes en `freeze.json`,
memorias escolares,208 recibos de propuestas,208 respuestas Groq, diario de
intentos, logs, `results.json`, `audit.json` y `manifest.json`. No hay claves;
solo el cliente las lee para la cabecera HTTP.

Repetir auditoría desde echoai con Python normal, sin `-O`:

```bash
PYTHONPATH=.. python3 -m echoai.echo58.llmstudy.audit lab/echo58/llmstudy/20261023-r1
PYTHONPATH=.. python3 -m unittest echoai.tests.test_echo58_llmstudy -v
```

Se conserva D1 sin ventaja demostrada. Sin publicación externa ni nuevas
llamadas para buscar otro resultado.
