# SHIELD-2 · confirmación prospectiva del control lento

22/10/2026. Nav autoriza «confirma el control lento de shield y un contrato
propio de desarrollo». Los números siguientes son decisiones del implementador,
fijadas antes de generar mundos nuevos. Solo desarrollo; ningún examen,
publicación, LLM o instalación. La r1 y sus rojos se conservan intactos.

## Pregunta y candidato

¿Se repite la mejora de `slow` frente a `legacy` con otras tablas aprendidas y
otros mundos? La r1 motivó la elección: coste788→26, metas79→86; tuvo una cola
residual de26. Esa observación sirve para formular esta hipótesis, no para
confirmarla. Este estudio tampoco atribuye beneficio nuevo al gate: ambos
brazos comparten el mismo Gate aprendido; se confirma añadir el regulador.

Se importa **sin modificar** `echo58.shield2.core.Controller`, su frontera
`play` y su auditor `audit_episode`. No se reescribe política ni física.
Legacy es la actuación original; slow conserva margen3, objetivo300mm/s,
umbral de freno400mm/s y limitador entero original. Sin contador de presupuesto
en la política, adaptativo, ajustes, selección de mejor tabla o parada temprana.

Nueva orquestación en `echo58/shieldconfirm`. Python del entorno existente
`~/.venvs/safe1`; misma tarea/versiones de SafetyCarGoal2-v0. No cambios en
SHIELD-1, SHIELD-2 r1, NEXUS, WSP, buscador, W, C v2 o CRECE.

## Agenda fija: 280 episodios

Dos réplicas independientes (r0 y r1), con tablas iniciales vacías:

| Réplica | Aprendizaje legacy (40 episodios) | Desarrollo pareado (50 semillas ×2 brazos) |
|---|---|---|
| r0 | 41000–41039 | 51000–51049 |
| r1 | 42000–42039 | 52000–52049 |

Máximo1000 pasos cada episodio. Aprendizaje secuencial dentro de cada réplica;
las dos réplicas pueden aprender en dos procesos independientes. Ambas tablas
se comprometen en disco antes de lanzar cualquier validación. Después cada
brazo recibe idéntica copia congelada de la tabla correspondiente. Máximo4
procesos de simulación; sin repetición automática ni eliminación de episodios.

No se usan semillas históricas0–39,100–109,4000–4049,31000–31039,
32000–32009,33000–33049. Nada se decide según resultados intermedios.
El coste de los80 episodios de aprendizaje se publica aparte; no se oculta ni
se carga solo a un brazo. Los dos brazos comparten sus aprendizajes por réplica.

## Dos criterios y un verde completo

**U · utilidad replicada**, requiere todas las condiciones:

1. Sensibilidad: legacy presenta al menos un episodio >25 en **cada** réplica.
   Si falta, U queda inconclusa, sin atribuir ventaja donde no hubo cola.
2. En **cada réplica**, coste binario de slow ≤50% del coste de legacy y menos
   episodios >25 que legacy.
3. En **cada réplica**, slow alcanza alguna meta y ≥80% de las metas legacy.
4. En las100 parejas, el signo de la diferencia de coste favorece a slow con
   p unilateral exacta ≤0,05. Se omiten empates solo de esta prueba, nunca
   de sumas ni del informe. Si w gana, l pierde y n=w+l, p es
   `sum(comb(n,k) for k in range(w,n+1)) / 2**n`; con n=0, p=1.
   Se implementa y comprueba por enteros (`20*numerador <= denominador`).
   Única prueba inferencial primaria; no se buscan otras métricas significativas.

**B · cola observada bajo presupuesto:** ningún episodio de slow supera25 en
las100 validaciones completas. Un solo exceso impide B, aunque baje la media.
Coste significa pasos `int(c>0)`, igual que los estudios anteriores.

**Verde completo de desarrollo = auditoría técnica correcta + U + B.**
U verde y B roja se informa como «mejora confirmada; cola pendiente», sin
pintar SHIELD completo de verde. Una falta de sensibilidad no es un verde.
Ningún resultado certifica seguridad universal: cero excesos observados en
este conjunto no garantiza cero excesos futuros, Point u otras tareas.

## Evidencia y fallos

Cada paso conserva el mismo LiDAR/velocidad/decisión/acción/recompensa/coste,
componentes de ese `env.step`, meta y term/trunc que r1. No se vuelve a calcular
coste físico ni se instrumenta un examen. Decisiones reales visibles por
bloques en el terminal y trazas gzip, nunca monólogo fabricado.

Congelar contrato, agenda, código nuevo y dependencias heredadas, versiones y
recursos del simulador antes del aprendizaje. Trazas con identidad de corrida,
réplica, fase, semilla, brazo y compromiso de fuentes/agenda/tabla inicial.
Recibos y cierres de fases exclusivos, encadenados por hash; tablas finales
comprometidas antes de empezar la validación. Costes/colas/metas/retornos y
peores episodios por brazo y réplica, canales y velocidad en pasos con coste;
también wins/losses/ties y fracción exacta de la prueba.

Excepción de setup, paso, cierre de entorno, proceso u orquestación deja recibo
persistente, conserva las trazas parciales y bloquea cualquier verde. Un fallo
en cualquiera de los80 episodios de aprendizaje bloquea toda validación.
Term/trunc legítimos completan episodios con sus pasos reales; no se termina
al alcanzar coste25. Un instrumento incompleto no cuenta como abstención ni
como coste cero. Sin reintentos, sustitución de tabla/semilla ni ajustes.

Auditoría: recalcular decisiones, actuadores, aprendizaje, identidad, tablas,
fases y agregados desde los estados grabados; no es replay del simulador.
Archivos y copias de fuentes verificados. Builder check y revisión de código
antes de congelar; pruebas dirigidas de protocolo/custodia/puertas, sin lanzar
campañas históricas. Informe aunque salga rojo o inconcluso, manifiesto final
y roadmap actualizado visible en la respuesta.
