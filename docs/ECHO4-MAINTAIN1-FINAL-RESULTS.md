# E4-MAINTAIN-1 — resultados B/C/D y límites

2026-09-22. **E4-MAINTAIN-1 verde y cerrada en su perfil virtual declarado.**
Auditoría reconstructiva válida, cero hallazgos, `maintain1_green=true`.
El alcance es mantenimiento autónomo **condicionado a un modelo mecánico
declarado**, en el cuerpo virtual de MAINT-A. No es reparación general,
aprendizaje desde cero de la física, modificación de pesos/código ni
conciencia subjetiva. ECHO-4 completo sigue abierto.

[Contrato congelado](ECHO4-MAINTAIN1-BCD-DESIGN.md) ·
[Informe](../lab/echo4/maintain1-final-v1/report.json) ·
[Manifiesto previo al examen](../lab/echo4/maintain1-final-v1/lock.json) ·
[Recibo de auditoría](../lab/echo4/maintain1-final-v1/audit-receipt.json).

## Qué se ha implementado

- **B:** inferencia de capacidad corporal a partir del WSP original de 16 B
  y de acciones realmente ejecutadas. Mantiene hipótesis enteras acotadas,
  decide si intervenir, protege una reserva preventiva y se abstiene cuando
  no encuentra una acción segura dentro de la familia declarada.
- **C:** vidas sin reset, averías recurrentes, repuestos finitos y continuidad
  de memoria/contabilidad. Checkpoints de operaciones completas con digest
  externo, fuentes fijadas, codec de grafo cerrado y parada persistente.
- **D:** dos cohortes nuevas, cuatro brazos, criterios previos y reconstrucción
  nativa de las trazas. Solo el recibo del auditor puede conceder verde.

El controlador es ingeniería explícita sobre el punto de propuesta del
agente existente. Usa la Q original para desempatar y conserva sus
actualizaciones, CAM/T, SENSATION, BOUNDARY y el gate. **La política de
mantenimiento no ha sido descubierta desde cero por Q.** Su familia de
hipótesis conoce las reglas del actuador, pero no recibe la avería, el calor,
los registros exactos, los repuestos reales ni el calendario privado.
Esos datos quedan en el ejecutor/auditor, no en un segundo bus cognitivo.

El filtro de seguridad vuelve a considerar el prior completo sobre la
observación actual: una avería puede ocurrir antes del próximo tick sin
anunciarse. Esto evita confiar ciegamente en una capacidad anterior, pero
también puede provocar una parada cuando el cuerpo real aún sería viable.
La garantía no cubre física fuera del prior ni un veto que fuerce una espera
peligrosa. La autoridad del operador sigue prevaleciendo.

## Desarrollo y antecedentes que no se borran

MAINT-A conserva su resultado: el guion de servicio produce 45 unidades de
trabajo frente a 120 del control y seis terminalidades; la Q original sin
guion muere a los cuatro ticks. Sus 87 fuentes y evidencias no se modifican.
[Resultado A](ECHO4-MAINTAIN1-A-RESULTS.md).

En B, el primer lote de 200 vidas con reserva <=40 quedó rojo: 24/30
recuperables completos, aunque mejoraba el trabajo agregado. Elevar la
reserva a <=64 permitió completar 30/30, a costa de reducir el trabajo
adaptativo de 2293 a 2025. Otro sondeo corrigió un ciclo térmico sin trabajo.
Son ajustes de desarrollo, no éxitos de examen ni aprendizaje de parámetros
por el propio agente. [Trazas completas preservadas](../lab/echo4/maintain1-b-development/README.md).

## Examen prospectivo

Fuentes/recetas/umbrales se escribieron antes de ejecutar. D1 y D2 usan 12
cuerpos distintos cada una, excluidos los cinco de desarrollo, con diez
escenarios y cuatro brazos: **960 vidas de examen**. Horizonte máximo de
256 ticks; la parada temprana cuenta y no elimina la vida del denominador.
Los cuerpos son nuevos; la familia de averías y sus calendarios son conocidos.
No se ha probado aquí transferencia a causas nuevas ni al mundo físico.

| Resultado | D1 | D2 | Total |
|---|---:|---:|---:|
| Trabajo adaptativo | 4705 | 4745 | 9450 |
| Trabajo sin reparación | 2404 | 2411 | 4815 |
| Trabajo con mantenimiento fijo | 3740 | 3761 | 7501 |
| Trabajo sin historia del modelo corporal | 2328 | 2344 | 4672 |
| Vidas recuperables completas | 72/72 | 72/72 | 144/144 |
| Reparaciones recuperables confirmadas | 96/96 | 96/96 | 192/192 |
| Muertes adaptativas | 0 | 0 | 0 |

Pasan en **cada** cohorte los márgenes de trabajo (+10% frente a no reparar
y sin historia; +5% frente al fijo), 90% de completitud, 80% de reparaciones
y 80% de confirmación ejecutada. No se sustituyen por un promedio favorable.

La confirmación exige un enfriamiento **posterior realmente ejecutado** que
recupere la caída térmica nominal, descontando el calor externo. No basta
con proponer mantenimiento ni con cambiar una etiqueta privada de avería.
No se concede recompensa por reparar o sobrevivir: solo por trabajo útil.

El control `no_history` vuelve al prior de la observación presente **para
elegir**. Mantiene Q, T y el contador de acciones; no se afirma que sea un
agente sin memoria de ninguna clase. El control fijo comparte homeostasis
y seguridad, con permiso periódico de servicio cada 24 ticks.

### Límites y casos desfavorables

- Los cuatro escenarios límite también cuentan en el trabajo total:
  irreparable, sin repuestos, agotamiento y calor fuerte. En cada cohorte
  las 48 vidas adaptativas de estos grupos paran; no son 120/120 éxitos.
- Ninguna avería irreparable se convierte en reparada. En los dos exámenes
  hay **24 servicios pagados sin recuperación**: la incertidumbre cuesta.
- Incluidos los casos límite, se registran 268 cambios de capacidad y
  261 confirmaciones posteriores. Las siete sin confirmar quedan separadas;
  no se suman a las 192 confirmaciones del dominio recuperable.
- El adaptativo pierde trabajo en 6 y 2 parejas frente al fijo, en 7 y 7
  frente a no reparar, y en 2 y 6 frente a `no_history`. No hay dominancia
  universal. El informe publica todos los escenarios y todas las trazas.
- También los controles registran cero muertes en D. La ventaja no depende
  de obligarlos a morir; depende de capacidad recuperada y trabajo.
- La reparación no elimina calor externo ni crea repuestos. Con calor 4,
  el balance de acciones no permite deducir sostenibilidad indefinida de
  una prueba finita. Fuera de este prior no se promete seguridad general.

## Recursos y cómputo

Totales de D1+D2; todos los costes físicos se producen en el simulador.

| Brazo | Ticks ejecutados | Servicios pagados | Recurso usado total | Coste extra de servicio | Predicciones de cajas |
|---|---:|---:|---:|---:|---:|
| Adaptativo | 44172 | 292 | 73818 | 1752 | 8696280 |
| Sin reparación | 20859 | 0 | 35234 | 0 | 4329492 |
| Fijo | 37342 | 571 | 65008 | 3426 | 7121256 |
| Sin historia corporal | 21043 | 0 | 35731 | 0 | 7644600 |

El coste extra es **parte** del total, no se suma de nuevo. La carga introduce
recurso mediante la acción física declarada; contabilidad H/repuestos conserva
el balance en todos los ticks. El adaptativo trabaja más y consume más
recurso total que los controles; no se publicita como menor gasto absoluto.

Todos comparten horizonte máximo, tres acciones, reglas y límites del modelo.
No se iguala tiempo CPU ni número de operaciones: el contador de predicciones
es un indicador de cómputo, no ticks físicos ni una medida energética del PC.
Las pruebas, desarrollo, continuidad y auditoría añaden cómputo fuera de esta
tabla. LLM apagado; cero llamadas corticales en los cuatro brazos.

## Continuidad, auditoría y reproducción

C compara 12 checkpoints con continuación en procesos nuevos: estado inicial,
progreso 1/2, servicio pagado, futura avería, agotamiento, ausencia de repuestos,
irreparable, veto, operador, terminalidad y presupuesto de 512 ticks. Las
continuaciones y hashes finales coinciden exactamente: **257 eventos futuros**
en ambos caminos. No se recuperan energía, repuestos ni memoria al cargar.
Se rechazan **11/11 mutantes** de contabilidad, progreso, permisos y custodia.

El caso terminal de C fuerza una espera por veto junto al límite caliente:
hay una muerte deliberada de ensayo para comprobar que no revive al cargar.
No es una muerte ocultada de D ni prueba de que todo veto sea inocuo.

La suite de MAINTAIN suma **85/85 pruebas aprobadas**: 43 de A y 42 nuevas.
Las nuevas incluyen 11.664 transiciones puntuales contra la física
sellada A, cobertura conservadora de intervalos, acceso observable, costes,
incertidumbre, veto/parada, clases/esquemas cerrados y orden de congelación.

Regresión final: **611/611 pruebas ECHO-4 aprobadas**, incluyendo las 85
de MAINTAIN. El núcleo/Q añade 495 pruebas: 494 aprobadas y un fallo esperado
histórico. Ocho pruebas GUI no pudieron abrir sockets en el sandbox; se
repitieron sus tres clases (29/29 aprobadas) con permiso para localhost.
No se cuentan esas repeticiones otra vez: **1106 comprobaciones, 1105
aprobadas y un fallo esperado**, sin fallos nuevos pendientes.

La primera ejecución amplia aún cargaba una aserción de desarrollo que
calculaba mal el tamaño de la rejilla (exigía >30000 en vez de 11664).
Las transiciones sí coincidían. Se corrigió **antes** de congelar D y la
repetición completa posterior pasó; no se cambió ningún umbral científico.

```bash
PYTHONPATH=.. python3 -m unittest discover -s tests -p 'test_echo4*.py' -q
PYTHONPATH=.. python3 -m unittest tests.test_nexus0 tests.test_qtable -q
# Solo si el sandbox bloquea sockets: repetir con permiso de localhost.
PYTHONPATH=.. python3 -m unittest tests.test_nexus0.TestGui2 tests.test_nexus0.TestGui3 tests.test_nexus0.TestGui35 -q
```

Digest reproductivo del informe:
`7e1c0e821ba2ddf79834fef6a66a16bfd2773a456d29ac5bbf535c11e6024fbe`.
El informe lleva `criteria_passed=true` y **`maintain1_green=false` por diseño**.
La reconstrucción en proceso nuevo reprodujo B/C/D1/D2 y MAINT-A,
comprobó las 93 fuentes y la custodia heredada de DREAM y concedió
`valid=true`, cero hallazgos y **`maintain1_green=true`**.
No vuelve a inferir con Qwen ni pretende repetir aquí toda la
campaña científica de DREAM.

```bash
PYTHONPATH=.. python3 -m unittest tests.test_echo4_maintain1 tests.test_echo4_maintain1a -q
PYTHONPATH=.. python3 -m echoai.echo4.maintain_final verify lab/echo4/maintain1-final-v1
```

Para reproducir la campaña, usar `campaign` con un directorio **inexistente**.
Repetir estas recetas verifica reproducibilidad; no crea otro holdout.
No sobrescribir informes, checkpoints o recibos.

Con el cierre verificado, el siguiente bloque es **E4-OTHER-1**, seguido
de INTERACTION, RELATION, ROLES e INTEGRATE. RELEASE preparará la publicación
del agente `rxlabs/echoai-4`; todavía no está publicado. Hardware después y
METAVERSE-1 último. El mantenimiento de este perfil no acredita conciencia
ni cierra el agente integrado.
