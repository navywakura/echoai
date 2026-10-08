# E4-MAINTAIN-1 — MAINT-A implementada y auditada

2026-09-22. **Infraestructura A verificada; MAINTAIN-1 sigue abierta.**
[Contrato previo y etapas B/C/D](ECHO4-MAINTAIN1-A-DESIGN.md).

## Qué se ha implementado

- [Entorno](../echo4/maintain_world.py): obstrucción reparable, avería no
  reparable, calor externo persistente, repuestos finitos y trabajo medible.
  Reutiliza la transición WORLD-1; servicio mediante tres enfriamientos reales,
  con tres ticks, nueve unidades del enfriamiento y seis adicionales, más
  un repuesto. No nuevo comando ni recurso gratuito.
- [Adaptador](../echo4/maintain_agent.py): `MaintenanceAgent(SelfAgent)` con
  CAM/T/Q/SENSATION/BOUNDARY y gate originales. Política original sin reemplazo,
  córtex apagado, WSP 16 B. Parada enclavada antes de mutar memoria; sin respawn.
- [Banco](../echo4/maintain_bench.py): guiones privados de factibilidad,
  baseline Q sin guion, bloqueo de fuentes, recibos completos y reconstrucción.
  Los guiones no están en la política del adaptador ni prueban autonomía.
- [43 tests nuevos](../tests/test_echo4_maintain1a.py), incluidos costes,
  irreparables, terminalidad, veto, parada, WSP sin etiquetas privadas,
  rechazo de checkpoints nominales que perderían estado de mantenimiento,
  entradas inválidas y seis manipulaciones con digest recalculado.

## Resultado completo, incluidos los límites

108 contextos públicos de desarrollo, dos guiones: **216 episodios**.
Todos conservan los invariantes. No son un examen de generalización ni
una selección de casos favorables.

| Guion de laboratorio | Pasos reales | Reparaciones | Servicios pagados | Recurso total gastado | Trabajo | Terminalidades |
|---|---:|---:|---:|---:|---:|---:|
| Cuatro enfriamientos y una espera | 534 | 18 | 54 | 1.722 | 45 | 6 |
| Ciclo interrumpido, sin servicio | 540 | 0 | 0 | 1.188 | 120 | 0 |

**Reparar indiscriminadamente es peor en esta mezcla:** consume más, produce
menos trabajo y causa seis terminalidades por exceso de enfriamiento. Estos
resultados se conservan; no se presentan las 18 reparaciones como una ventaja
conductual. La futura política debe evitar gasto inútil y sostener trabajo.

Testigo concreto, sin restauración: cuerpo inicial H=64, temperatura=96,
obstruido y un repuesto. Tras tres enfriamientos: H=49, temperatura=84;
se han gastado 15 unidades y el repuesto. El siguiente enfriamiento vuelve
a descender 16 en vez de 4. Después de una espera termina H=45, temperatura=72,
con **una unidad de trabajo**, cinco ticks y 19 unidades gastadas en total.
Recupera una capacidad por una operación física virtual costeada, no por
reemplazar el cuerpo. La selección de esas acciones sigue siendo guionizada.

Controles adicionales:

- Veto nativo a la tercera propuesta: se ejecuta WAIT y no hay servicio.
- Parada antes de esa propuesta: dos ticks, sin más acciones ni reparación.
- **Baseline Q nativa sin guion:** cuatro ticks, cero trabajo/reparaciones,
  terminalidad por calor. Esta entrega no ha solucionado el mantenimiento
  autónomo de ese agente.

En total el informe registra **220 episodios y 1.090 ticks** (216 de la malla
y cuatro testigos). Cero resets, hechos falsos, destrucción CAM o llamadas
corticales. Balance de H y repuestos y registros corporales correctos en cada
tick. Las siete comprobaciones del mecanismo pasan. El auditor vuelve a
ejecutar esos episodios: sus costes y los de tests son repeticiones de
verificación, no nuevos resultados independientes ni energía medida.

## Evidencia y reproducción

- [Informe](../lab/echo4/maintain1-a-v1/report.json).
- [Bloqueo previo](../lab/echo4/maintain1-a-v1/lock.json): **87 fuentes**, las
  82 anteriores intactas más tres módulos, el test y el contrato de MAINT-A.
- [Recibo reconstructivo](../lab/echo4/maintain1-a-v1/audit-receipt.json):
  `valid=true`, sin hallazgos; **`maintain1_green=false`**.
- SHA-256 reproductivo:
  `ec4a6d1eee3c2f1f985209727d95a8a675ed8f4ceaceb7dd48bfa89e1ef8d91c`.

Desde `echoai/`:

```bash
PYTHONPATH=.. python3 -m echoai.echo4.maintain_bench verify lab/echo4/maintain1-a-v1
PYTHONPATH=.. python3 -m unittest echoai.tests.test_echo4_maintain1a -q
```

Para generar otra copia de desarrollo, elegir un directorio que no exista:

```bash
PYTHONPATH=.. python3 -m echoai.echo4.maintain_bench preflight /tmp/echo4-maintain-a-reproduction
PYTHONPATH=.. python3 -m echoai.echo4.maintain_bench verify /tmp/echo4-maintain-a-reproduction
```

No repetir `--write-receipt` sobre un recibo existente ni sobrescribir el
directorio original. El auditor comprueba custodia de fuentes/artefactos y
vínculos DREAM v3/v2/v1, **no ejecuta otra campaña DREAM ni vuelve a llamar
a Qwen**. El informe A tampoco acredita compatibilidad de checkpoints:
CONT-A rechaza correctamente este perfil nuevo; MAINT-C deberá implementarlo.

Regresión ejecutada: **235 tests aprobados**, 43 nuevos y 192 de WORLD-1,
SENSATION, BOUNDARY, integración SELF, DREAM v3, Q-table y gate/banco NEXUS-0.
Los 43 nuevos se repitieron tras la limpieza final de un import sin uso;
no se suman dos veces. Reconstrucción adicional en proceso nuevo válida.
`git diff --check` sin errores; Ruff no está disponible y no se ha ejecutado.

## Siguiente: MAINT-B

Desarrollar estimación observable de capacidad y elección de intervención,
con memoria/historia y comparación contra no reparar, política fija y
ablación del modelo propio. No leer el fallo privado, no usar H/temperatura
exactos para decidir, no presumir que el diagnóstico SELF anterior cubra este
dominio, ni conceder un «reparado» por haber emitido tres propuestas.
Definir umbrales antes de abrir el examen conductual. Después: MAINT-C/D,
OTHER, INTERACTION, RELATION, ROLES, INTEGRATE y RELEASE.

Destino previsto de producto: **`rxlabs/echoai-4`**, sujeto a permisos,
licencias, instalación limpia y demo verificable. No publicado en esta entrega.
[Plan de empaquetado y límites](../echo4/README.md).
Sin cambios en Discord, hardware, web, núcleo histórico ni modelos; sin
commit/push. Se preservan los cambios previos del workspace.
