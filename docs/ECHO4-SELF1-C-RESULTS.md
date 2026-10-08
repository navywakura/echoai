# E4-SELF-1 / SELF-C v1 — protección demostrada, ventaja de recuperación pendiente

2026-09-21. **Implementada, pero roja en el criterio de ventaja conductual.**
El [contrato prospectivo](ECHO4-SELF1-C-DESIGN.md) exigía completar más vidas
que el control sin atribución. Ambos completan 126/240, precisamente las
126 condiciones físicamente viables. No se cambia el umbral después del
resultado: `development_checks_passed=false` y `self1_green=false`.

## Qué está implementado

`SelfRecoveryAgent` integra SELF-B en turnos reales del agente existente:

- Continúa temporalmente las hipótesis; no restaura el cuerpo en cada paso.
- Ajusta la propuesta de acción con una heurística entera de margen corporal
  y la Q existente como desempate. El gate original sigue teniendo autoridad.
- Usa `Agent.self_model.observe_step` para autorizar o retener escrituras
  en la T original, incluido su inverso y su disciplina KCC.
- Da la misma autorización a SENSATION/PATTERN. La historia sensorial sigue
  avanzando aunque una transición no se aprenda; Q recibe la recompensa real.
- Se detiene ante contradicción, veto o ausencia de una acción segura.
  Una parada del experimento no es una cuarta acción ni una vida completada.

El consumidor solo utiliza WSP, hipótesis y ejecución confirmada; no consulta
registros físicos ni parámetros privados. Reutiliza CAM/T/Q, sin LLM ni
segundo bus. La referencia nominal está sellada; el núcleo histórico y los
archivos de SELF-A/B, BOUNDARY y SENSATION no se modifican.

## Comparación completa

240 condiciones de desarrollo × cinco controles = 1.200 vidas evaluadas.
Máximo de 24 pasos por vida. H={29,34,39}, temperatura={44,52,60,68}, cuatro
acoplamientos y cinco pulsos. El juez privado comprueba alcanzabilidad finita:
126 casos permiten completar el horizonte; 114 no. Esa respuesta no se entrega
al agente. Se publican ambos grupos y no se omiten fallos.

| Controlador | Completadas / 240 | Paradas | Muertes | Escrituras con efecto corporal | Escrituras legítimas |
|---|---:|---:|---:|---:|---:|
| Selectivo | 126 | 114 | 0 | 0 | 4.801 |
| Misma decisión, sin protección | 126 | 114 | 0 | 119 | 4.801 |
| Sin atribución dinámica | 126 | 0 | 114 | 1.598 | 3.436 |
| Todo externo | 126 | 0 | 114 | 1.583 | 3.451 |
| Todo propio / congelar todo | 12 | 228 | 0 | 0 | 0 |

«Escritura con efecto corporal» significa que el sucesor observado difiere
del contrafactual con acoplamientos nominales y el mismo pulso externo. No
significa que cada escritura haya desplazado al ganador de T: también puede
incrementar alternativas, conflictos o el inverso. Se cuentan actualizaciones,
no 119 recuerdos únicos destruidos.

Resultados acreditados en este banco:

- **119/119 transiciones retenidas** dejan la fila T, sus contadores/inverso
  y el modelo SENSATION/PATTERN intactos. El control de igual conducta pero
  sin protección las escribe: aísla el efecto del permiso de aprendizaje.
- Pasan **4.801 actualizaciones legítimas**, incluidas **171 externas**.
  No es una congelación global disfrazada de protección selectiva.
- El selectivo completa **126/126 casos viables** y se detiene en los 114
  inviables. Los controles sin atribución/todo externo mueren en esos 114;
  se demuestra una ventaja de parada segura, no más tareas completadas.
- Las acciones cambian frente al control sin atribución en **184/240 casos**.
  Cambiar acciones por sí solo no demuestra mejorar el éxito de la tarea.
- Selectivo y «sin protección» ejecutan exactamente las mismas acciones
  en **240/240 casos**: la política utiliza el prior físico y Q, no T.
  Por tanto, este banco no demuestra utilidad conductual posterior de la
  memoria preservada. Ese es un límite central, no un detalle de presentación.

## Costes e invariantes

Selectivo: 4.920 pasos de vida; sin protección: 4.920; sin atribución y todo
externo: 5.034 cada uno; todo propio: 4.080. La preparación compartida requiere
72 transiciones nominales por estado inicial (12 estados) y el diagnóstico
240/240 correcto consume otros **2.080 pasos en 280 ensayos**. Estos costes
no se ocultan dentro de las vidas evaluadas.

La vida comienza tras una restauración experimental declarada del estado
inicial del diagnóstico. Hay cero resets **durante** cada vida, no cero
restauraciones en todo el protocolo. Se heredan física conocida, familia de
perturbaciones estacionaria y ejecutor confiable de SELF-B. No se demuestra
recuperación autónoma desde una avería espontánea, reparación física ni
supervivencia indefinida. Una perturbación fuera del prior puede invalidarlo.

Máximos observados: cinco candidatos H y cuatro térmicos, frente a capacidades
64 y 160. Un pronóstico pendiente, sin lista de episodios dentro del consumidor.
No son cifras de memoria RSS ni energía de hardware.

En los cinco brazos: referencia preservada 240/240, balance de recursos
240/240, cero hechos falsos, slots destruidos, llamadas corticales o resets
en la vida. El nuevo ejecutor conserva el balance real del canal acoplado.

## Verificación y artefactos

**36 pruebas nuevas y 236 de regresión seleccionada pasan: 272 en total.**
Incluyen integración nativa, pronóstico anterior a la física, autorización
compartida de T/PATTERN, gate, capacidad CAM, contradicción, entradas inválidas,
restauración, límites, contabilidad, rechazo de sobrescritura y manipulación
de informes/trazas. El comportamiento por defecto sin SELF-C no cambia.

[Informe](../lab/echo4/self1-c-v1/report.json) ·
[Trazas](../lab/echo4/self1-c-v1/traces.jsonl) ·
[Recibo de auditoría](../lab/echo4/self1-c-v1/audit-receipt.json).
Identidad de reproducción:

```text
15d8bfba9210027dce9edf4ee3bc5f8a54b6b6bc678f6869e94e01313c3a5b89
```

Auditoría completa en proceso nuevo: **válida, sin hallazgos**. Reproduce
todas las trazas físicas y el informe. Acredita la fidelidad del resultado
rojo; no lo convierte en verde.

Desde `echoai/`:

```bash
PYTHONPATH=.. python3 -m unittest echoai.tests.test_echo4_self1c -v
PYTHONPATH=.. python3 -m echoai.echo4.self_recovery_audit verify lab/echo4/self1-c-v1
```

`census` exige una ruta nueva y retorna código 1 si falla algún criterio
científico. En v1 el código 1 corresponde a `behavioral_gain=false`, no a un
fallo de ejecución. No sobrescribir este resultado para ocultarlo.

SELF-A (`eeb52994…`), SELF-B (`06fae2d4…`), BOUNDARY (`48789bd5…`) y SENSATION
(`96f2deae…`) se han reproducido sin hallazgos con sus fuentes intactas.

## Decisión de roadmap

**SELF-C continúa abierta.** El control sin atribución ya alcanza el máximo
físico de éxitos de este banco. Ajustar la heurística para superar 126 sin
cambiar la tarea sería imposible; redefinir retroactivamente el éxito para
aprobarlo tampoco sería una validación.

El siguiente trabajo es **SELF-C v2**, con contrato nuevo antes de ejecutarlo:
una tarea de reutilización en la que conservar T pueda afectar una decisión
y su resultado posterior. Comparar selectivo, sin protección, sin atribución
y congelación total; conservar v1 y sus límites. Es una propuesta, no una
capacidad ya implementada ni una promesa de resultado favorable.

Después seguirán exámenes nuevos B/C para el cierre conjunto de E4-SELF-1.
No avanzar todavía a CONTINUITY. Hardware después del software y METAVERSE-1
al final. Ningún resultado de este banco acredita conciencia subjetiva.
