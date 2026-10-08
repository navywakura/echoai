# E4-SELF-1 / SELF-A — primer entregable implementado

2026-09-21. **E4-SELF-1 en desarrollo, no cerrado.** SELF-A implementa un
monitor de cambios y una auditoría de identificabilidad. No implementa
todavía atribución positiva propia/externa/mixta ni recuperación conductual.
[Contrato y etapas](ECHO4-SELF1-DESIGN.md).

## Código disponible

- `echo4/self_model.py`: `SelfChangeMonitor`, referencia nominal acotada
  sobre la CAM y `BoundaryMap` originales. Ocho pares concordantes por
  contexto/acción, sellado explícito y comparación posterior sin aprendizaje.
  Separa cambio de deriva del brazo wait y cambio del contraste de acción.
  La etiqueta causal permanece `unknown`; una discrepancia de códigos no
  prueba que una parte concreta del cuerpo haya fallado.
- `echo4/self_agent.py`: `SelfAgent`, conexión opt-in a Agent/SENSATION/BOUNDARY.
  Expone calibración, sellado y comparación. No altera `_propose`, el gate,
  Q/T ni los turnos originales; las pruebas comparan acciones y predicciones
  con el Agent anterior. **Todavía no intercepta aprendizaje T del loop**:
  preservar la referencia nominal no equivale a proteger selectivamente
  todo el modelo del mundo durante una vida.
- `echo4/self_audit.py`: enumeración física, agrupación por evidencia pública,
  testigos de ambigüedad y reproducción de todo el informe y traza.
- `tests/test_echo4_self1.py`: 29 pruebas nuevas.

Sin LLM, nuevas dependencias, hardware, otro bus o cambios en el encoder.
WSP sigue siendo de 16 bytes. La firma nominal tiene ocho enteros por fila;
máximo 128 filas, con el presupuesto original de 4.096 pares de BOUNDARY.
No se conservan listas crecientes de ensayos dentro del monitor.

## Resultado del barrido declarado

396 estados iniciales × cuatro acoplamientos × cinco perturbaciones =
**7.920 condiciones**. Hay 6.336 pares de calibración y 15.840 consultas
posteriores (las dos acciones). Ninguna condición se descarta.

| Evidencia disponible | Una acción por comparación | Ambas acciones por condición |
|---|---:|---:|
| Comparaciones/condiciones | 15.840 | 7.920 |
| Clases de evidencia pública | 1.024 | 704 |
| Clases con causas incompatibles | 252 | 119 |
| Comparaciones/condiciones en clases ambiguas | 8.346 | 3.256 |
| Cota de aciertos si se fuerza una causa | 11.604/15.840 | 6.320/7.920 |

Una acción significa un par acción/wait más su referencia nominal; ambas
significa disponer de los dos pares actuales y sus dos referencias nominales.
Las agrupaciones comparan todos los WSP y recibos relevantes, no las salidas
reducidas del monitor. Solo normalizan los IDs opacos de ensayo: no se admite
usar el número de fila/orden de enumeración como una etiqueta del mecanismo.

La cota suma la clase causal más frecuente dentro de cada firma pública
normalizada. Describe este banco equiponderado sobre condiciones físicas;
no es la precisión de un agente, un porcentaje universal ni un examen ciego.
Las clases físicas tampoco están equilibradas: nominal 396, propio 1.188,
externo 1.584 y mixto 4.752. Ninguna etiqueta privada entrena al monitor.

### Un testigo concreto

Desde H=37 y temperatura=65, estos cuatro mecanismos producen exactamente
la misma evidencia pública en los ensayos actuales de approach y avoid:

| Acoplamiento H | Calor externo | Causa privada del evaluador |
|---|---:|---|
| Intacto | 0 | Nominal |
| Intacto | +4 | Externa |
| Desacoplado | 0 | Propia |
| Desacoplado | +4 | Mixta |

Las trayectorias físicas difieren, pero no cruzan las bandas necesarias
para distinguirlas. El informe conserva este testigo y otros, con huellas
de los paquetes públicos; el auditor los reconstruye desde la física.
**Repetir una etiqueta con mucha confianza no resolvería esta ambigüedad.**
Esto limita este protocolo de dos ticks, no toda intervención futura.

Otro control unitario muestra que calor externo por sí solo puede cambiar
el contraste de acción debido a la cuantización: no basta con llamar
«propio» a cada contraste que cambie. Por eso SELF-A describe discrepancias
sin convertir sus dos máscaras en causas corporales/externas.

## Qué comprueba el monitor

Las **15.840/15.840** comparaciones coinciden con las diferencias observadas
de U/B calculadas por el juez. Es exactitud del detector de cambio, **no de
atribución causal**: el origen permanece desconocido en todas las consultas,
también en las que una futura hipótesis podría resolver.

Comparaciones en que el mecanismo alterado sigue coincidiendo con la
referencia nominal: 495 propias, 408 externas y 255 mixtas. «Coincide con
referencia» no declara que la física esté intacta. Las 792 comparaciones
nominales coinciden y no producen falsa alarma de cambio.

Se conserva exactamente referencia/CAM en **396/396** instancias durante
las consultas. Máximo dos filas por instancia; cero hechos CAM introducidos
y cero destrucción. Recibos inválidos, falta de soporte, conflicto nominal,
tiempo de ejecución diferente, WSP malformado o contexto ausente producen
desconocido sin sobrescribir el pasado.

**29 pruebas nuevas; 208 con regresiones seleccionadas, todas pasan.**
Incluyen integración sin cambiar acciones, conservación Q/T en calibración,
límites y duplicados, entradas inválidas, contraste entero con signo,
contradicciones, testigos reales y rechazo de informe/traza alterados.

La auditoría en un proceso nuevo reproduce toda la evidencia, sin hallazgos:

```text
valid=true
self1_green=false
reproduction_sha256=eeb52994b6b26200f1bcd73b3349530d4a39b5be4e514d7d0568cbf4bf43f6da
```

También se han vuelto a verificar, sin editar sus fuentes, los certificados
SENSATION (`96f2deae…`) y BOUNDARY (`48789bd5…`). No se reinterpretan sus
cierres: influencia causal observable no era atribución general de origen.

## Siguiente trabajo dentro de SELF

1. Diseñar y comprobar secuencias/intervenciones que separen las hipótesis
   de los testigos, manteniendo sensores actuales cuando sea suficiente.
   No ampliar WSP ni filtrar estado oculto para facilitar la clasificación.
2. Implementar atribución propia/externa/mixta/desconocida con evidencia
   suficiente y posibilidad real de refutación; no heredar etiquetas del censo.
3. Conectar ese diagnóstico a conservación selectiva del modelo y conducta
   de recuperación; medir frente a controles sin atribución y simplistas.
4. Fijar el contrato cuantitativo final, abrir B/C nuevos y reproducir el
   cierre. No pasar a CONTINUITY por aprobar este primer monitor.

No se ha demostrado conciencia, propiedad subjetiva del cuerpo, mantenimiento
autónomo ni una contraparte social. Hardware después del software;
METAVERSE-1 permanece al final.

## Evidencia y comandos

Evidencia local (~24,2 MB): [informe](../lab/echo4/self1-a-v1/report.json),
[traza](../lab/echo4/self1-a-v1/traces.jsonl),
[recibo de reproducción](../lab/echo4/self1-a-v1/audit-receipt.json).

Desde `echoai/`:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.. python3 -m unittest echoai.tests.test_echo4_self1 -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.. python3 -m echoai.echo4.self_audit verify lab/echo4/self1-a-v1
```

Para una copia nueva (el directorio debe no existir):

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.. python3 -m echoai.echo4.self_audit census /tmp/echo4-self1-a-reproduction
```

`--quick` solo hace un smoke. Ni el smoke ni el censo pueden marcar SELF
verde. Cambios locales, sin commit/push ni publicación web.
