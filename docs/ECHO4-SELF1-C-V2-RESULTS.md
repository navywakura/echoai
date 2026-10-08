# SELF-C v2 — utilidad conductual de la memoria protegida

2026-09-22. **SELF-C v2 verde en reutilización controlada de memoria.**
Desarrollo, confirmación y replay completo pasan: `self_c_v2_green=true`.
**E4-SELF-1 no está cerrada:** `self1_green=false`. El resultado rojo
de [SELF-C v1](ECHO4-SELF1-C-RESULTS.md) y sus fuentes permanecen intactos.

## Qué se ha implementado y qué pregunta responde

El [contrato prospectivo](ECHO4-SELF1-C-V2-DESIGN.md) sustituye la pregunta
saturada de supervivencia por una tarea nueva: después de una alteración
corporal temporal, ¿conservar el conocimiento nominal ayuda a elegir una
acción útil, sin dejar de aprender cambios externos que siguen presentes?

`SelfReuseAgent` extiende el agente existente, con su misma CAM/T/Q y gate:

- Aprende T mediante transiciones nominales realmente ejecutadas. No recibe
  una tabla de sucesores verdaderos del simulador.
- Durante la exposición utiliza el permiso de aprendizaje de SELF-C v1,
  compartido por T y SENSATION/PATTERN. Las acciones de exposición son
  supervisadas e idénticas entre controles; no son exploración autónoma.
- El ejecutor restaura el cuerpo nominal, conserva el pulso externo y entrega
  un recibo de restauración. **El agente no descubre ni ejecuta su reparación.**
- Recibe una solicitud WSP16 y compara las tres predicciones de T con ella.
  Entre coincidencias usa Q; sin coincidencia conserva la propuesta original.
  El selector no recibe física privada, diagnóstico, causa ni acción correcta.
- Ejecuta una acción real. Se puntúa el WSP alcanzado, no una declaración de
  confianza. El gate original puede vetar la propuesta.

La solicitud es un objetivo, no un hecho verificado ni una inserción en CAM.
No hay segundo bus, segundo núcleo, nuevo actuador, LLM o hardware.

## Resultados de los cuatro brazos

Cada fase incluye cuatro estados iniciales × cuatro acoplamientos × tres
pulsos externos: **48 condiciones y 144 objetivos por brazo**. Se conservan
las solicitudes coincidentes, sin descartar casos. Los criterios exigían
al menos 60% de éxito selectivo, al menos 1/3 en cada causa y una ventaja de
cinco puntos porcentuales frente a **cada** control, en **cada** fase.

| Brazo | Desarrollo / 144 | Confirmación / 144 |
|---|---:|---:|
| Selectivo, consulta T | **114 (79,17%)** | **108 (75,00%)** |
| Sin protección, consulta T | 99 (68,75%) | 90 (62,50%) |
| Congelar todo, consulta T | 76 (52,78%) | 56 (38,89%) |
| Mismo aprendizaje selectivo, sin T en la decisión | 60 (41,67%) | 48 (33,33%) |

Ventaja sobre el control más fuerte, sin protección: **+10,42 y +12,50
puntos porcentuales**. Los trece criterios del contrato pasan en ambas fases.
El brazo sin protección también representa aquí la ausencia de atribución
para aprender; no se cuenta como dos controles independientes.

Comparación emparejada: victorias / pérdidas / empates del selectivo.

| Frente a | Desarrollo | Confirmación |
|---|---:|---:|
| Sin protección | 15 / 0 / 129 | 18 / 0 / 126 |
| Congelar todo | 38 / 0 / 106 | 52 / 0 / 92 |
| Sin T en la decisión | 54 / 0 / 90 | 60 / 0 / 84 |

La ablación `no_t` no lee T en el selector; la predicción sensorial ordinaria
sigue existiendo, sin decidir por esa vía. Q permanece idéntica durante
preparación, exposición y tarea. Retirar T cambia el éxito pese a mantener
el mismo aprendizaje previo: evidencia de una contribución conductual de T.

## Desglose causal y fallos conservados

| Causa | Selectivo desarrollo | Sin protección desarrollo | Selectivo confirmación | Sin protección confirmación |
|---|---:|---:|---:|---:|
| Nominal | 12/12 | 12/12 | 12/12 | 12/12 |
| Propia | 36/36 | 21/36 | 36/36 | 18/36 |
| Externa | 24/24 | 24/24 | 24/24 | 24/24 |
| Mixta | **42/72** | 42/72 | **36/72** | 36/72 |

La protección aporta la ventaja frente a aprenderlo todo en las causas
propias. Permitir aprendizaje externo aporta la ventaja frente a congelar
todo: en causas externas este último solo alcanza 7/24 y 2/24, respectivamente.

**No se demuestra ventaja frente a aprenderlo todo en las causas mixtas.**
El selectivo falla 30 objetivos de desarrollo y 36 de confirmación, todos
mixtos. Retener una transición con efecto corporal puede impedir aprender
también su componente externo. No se inventan sucesores contrafactuales para
enseñar a T lo que no observó. Este límite queda abierto y las trazas contienen
todos esos fallos.

## Protección, costes y condiciones del experimento

| Medida del selectivo | Desarrollo | Confirmación |
|---|---:|---:|
| Actualizaciones retenidas, T/PATTERN sin cambios | 540/540 | 648/648 |
| Actualizaciones con efecto corporal admitidas | 0 | 0 |
| Actualizaciones legítimas admitidas | 1.188 | 1.080 |
| De ellas, externas | 792 | 720 |
| Diagnósticos correctos | 48/48 | 48/48 |

El control sin protección admite 540 y 648 actualizaciones con efecto
corporal. Son eventos de aprendizaje, no ese número de recuerdos únicos
destruidos. Todos los brazos reciben exactamente la misma exposición en
48/48 condiciones por fase; `no_t` y selectivo tienen formación idéntica.

Preparación por estado inicial: 64 pasos de referencia corta, ocho de
referencia larga y 24 de aprendizaje nominal de T; **96 pasos y 57
restauraciones experimentales**. Son 384 pasos por fase, compartidos mediante
copias equivalentes del agente ya preparado. Cada fase añade 408 pasos de
diagnóstico en 54 ensayos restaurados. Cada condición/brazo añade 36 pasos
de exposición y tres de tarea, cada paso desde restauración explícita.
En total por fase: 7.488 pasos de exposición/tarea, más 792 de preparación
y diagnóstico. No son vidas continuas ni restauraciones hechas por la política.

Las ocho observaciones nominales por acción y las doce exposiciones por
acción se fijaron antes del banco: permiten que evidencia alterada desplace
al ganador de T mediante el KCC original si no se protege. La ventaja medida
no implica robustez a cualquier proporción de experiencias.

Se congelan T y SENSATION/PATTERN durante las tareas; se verifica igualdad
completa de Q. Las 144 tareas de cada brazo/fase mantienen esos modelos y
el balance de recursos. Cero terminalidades, hechos falsos, slots destruidos
o llamadas corticales; referencia nominal preservada en todos los casos.
Los resets del objeto físico son cero dentro de cada ensayo, **no** las
restauraciones del protocolo completo.

## Alcance de la confirmación

Desarrollo usa H={30,37}, temperatura={48,65}; confirmación usa H={31,38},
temperatura={49,66} y orden inverso de objetivos. No se cambian fuentes ni
criterios entre fases. **Cada estado inicial tiene su propia calibración y
su propio aprendizaje nominal:** no es transferencia sin entrenamiento.

Son estados distintos dentro del mismo simulador, con mecanismos conocidos,
sensores cuantizados y restauración confiable. No constituyen los B/C finales
de E4-SELF-1, evidencia fuera del prior o una muestra de ensayos estadísticamente
independientes. El diagnóstico sigue condicionado a la física y familia de
perturbaciones declaradas en SELF-B. No se demuestra autorreparación,
mantenimiento indefinido, identificación causal general ni conciencia.

## Verificación y reproducción

**30 pruebas nuevas y 272 regresiones seleccionadas pasan: 302 en total.**
Cubren integración nativa, modelo compartido, ausencia de lectura privada,
cambio de decisión al intervenir T, ablación sin lectura de T, predicción
anterior al paso físico, veto, capacidad, recibos inválidos, congelación,
ausencia de sobrescritura y rechazo de informes/trazas manipulados.

Auditoría completa de v2 en proceso nuevo: **válida, sin hallazgos**.
Reproduce todos los pasos y el informe, incluido el resultado verde acotado
y `self1_green=false`.

[Informe](../lab/echo4/self1-c-v2/report.json) ·
[Trazas completas](../lab/echo4/self1-c-v2/traces.jsonl) ·
[Recibo de auditoría](../lab/echo4/self1-c-v2/audit-receipt.json).
Identidad de reproducción de la campaña:

```text
74bbdfddfac8199ba8763abee5dbe5fe364fdcea04d0ee3981ed58cdeb2590a0
```

Desde `echoai/`:

```bash
PYTHONPATH=.. python3 -m unittest echoai.tests.test_echo4_self1c_v2 -v
PYTHONPATH=.. python3 -m echoai.echo4.self_reuse_audit verify lab/echo4/self1-c-v2
```

`campaign` requiere un directorio nuevo y nunca sobrescribe evidencia.
`--quick` ejecuta solo smoke y nunca puede cerrar v2. El verificador compara
fuentes, todas las trazas y el informe con una ejecución física nueva; un
hash coincidente sin replay no basta.

SELF-C v1 (`15d8bfba…`, roja), SELF-B (`06fae2d4…`), SELF-A (`eeb52994…`),
BOUNDARY (`48789bd5…`) y SENSATION (`96f2deae…`) se han revalidado sin hallazgos,
sin modificar sus fuentes selladas.

## Siguiente paso

Preparar el **contrato de cierre conjunto de E4-SELF-1 y nuevos exámenes B/C**:
atribución, utilidad conductual y protección, incluyendo desconocidos,
contradicciones, vetos y mecanismos fuera del desarrollo. El fallo mixto de
v2 debe formar parte explícita de ese diseño, no desaparecer del informe.
No pasar todavía a CONTINUITY. Hardware después del software; METAVERSE-1
al final. La conclusión admisible es utilidad funcional de la memoria
protegida en este protocolo, no la creación de experiencia subjetiva.
