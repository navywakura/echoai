# Prompt de implementación B20

Texto para entregar al siguiente agente. Estado del encargo: investigación
hecha el 6 de octubre; B20 diseñado, sin implementación ni ejecución.

---

Trabaja en `/home/roger/REALRXOS/RXos/echoai`. Implementa y valida S6-B20 a
partir de la investigación local. Puedes usar Kaggle privado y su GPU gratuita.
Mantén la investigación privada. No cambies criterios para forzar un verde.

Lee primero `AGENTS.md`, `CLAUDE.md` y `docs/05-NEXUS-0-SPEC.md`; después:

- `docs/ECHO45-S6-B19-FORENSICS.md`.
- `docs/ECHO45-S6-B20-PLAN.md`.
- `lab/seed/s6b19-analysis-20261006/analysis.json` y su `analyze.py`.
- `docs/ECHO45-S6-B19-DESIGN.md` y `docs/ECHO45-S6-B19-RESULTS.md`.
- `docs/ECHO45-S6-B18-COST-FORENSICS.md`.
- El corte actual de módulos en `docs/ECHO45-ECHO5-ROADMAP.md` y `docs/NOW.md`.

B19 está CLOSED_NO_PROMOTION: 36 propuestas, 1.188 juegos físicos sobre doce
casos dirigidos, una generación inicial LLM. Ningún brazo pasa +2 niveles sin
regresiones individuales. Los 160 casos de cualificación y los 80 protegidos
nuevos no se abrieron. B19 está terminado; no hay que reanudarlo.

Hallazgos que debes abordar y comprobar:

1. Híbrido: diez refinamientos del candidato 2, +4 con una pérdida. Sintetizador:
   nueve del candidato 3, +1 sin pérdidas. El selector B19 perdió el límite de
   descendientes y no conserva varios objetivos reparables.
2. El generador solo tiene 1.205 guardas ancladas. No incluye todas las
   conjunciones legales de hasta tres features. No inyectes las guardas del
   informe como respuestas: amplía de manera general y declarada la biblioteca.
3. La cobertura confunde cualquier consumo basal coincidente con conservar la
   ganancia de la partida completa. La carga negativa mezcla valores y linajes.
   Una carga cero no prueba seguridad. Vincula intervenciones y consecuencias
   con incertidumbre explícita; conserva el juez separado.
4. `path_pending=1` con HOLD 0,1,2,4 repite conducta en cuatro intentos de
   síntesis. Es una mejora de score sin niveles, no una regla inerte. Usa
   equivalencia observada para detectar estancamiento; poda solo con certificado.
5. En v3/28027, HOLD1/events<=8 conserva cinco niveles pero aumenta acciones
   registradas de 784 a 1.264 y reinicios automáticos de 19 a 32. HOLD inhibe
   reinicios; `pending_effect=0` no indica que una copia remota haya dejado de
   ser útil. No entregues al agente el estado privado del simulador.
6. El esquema se filtra con tres casos aunque existen doce. Conserva evidencia
   propia de desarrollo completa para el sintetizador y resumen trazable para
   el modelo. No introduzcas datos protegidos ni IDs de tareas como features.

Orden de trabajo:

A. Verifica hashes B18/B19 y procesos. Ejecuta el análisis de solo lectura.
   Crea módulos B20 separados y pruebas de regresión que detecten los fallos
   anteriores. No edites ninguna dependencia congelada. No uses echo-discord,
   ni actives un LLM dentro de NEXUS-0, ni crees un segundo bus de pensamientos.

B. Formaliza el contrato ejecutable antes de medir. Calibra coste de generación
   y evaluación con datos de desarrollo declarados; fija topes por etapa,
   reglas de selección, semillas, particiones, presupuesto físico y parada.
   La autorización permite ejecutar sin otra confirmación dentro de esos límites
   gratuitos; no autoriza gastos ni publicación. Si cambias una condición después
   de ver resultados, cierra la anterior y registra una nueva.

C. Separa el control de capacidad del ensayo de descubrimiento. Contrasta
   biblioteca antigua/ampliada en desarrollo. Los controles humanos conocidos
   no entran en prompts, respuestas, ranking ni memoria inicial del investigador.
   Si no hay solución en el espacio medido, informa ese límite sin declararlo
   imposibilidad universal. Investiga features temporales observables bajo una
   subcondición nueva si la representación no permite distinguir los casos.

D. Implementa archivo de hipótesis con varias ramas, límite de estancamiento,
   crédito por intervención/valor/linaje y contrastes controlados de guarda y
   duración. Regenera certificados cuando cambien lenguaje o umbrales. No
   infieras resultados de una política nueva únicamente reproduciendo acciones
   de una política antigua: necesita simulación real de sus nuevas decisiones.

E. Ejecuta el micro factorial propuesto: inicializador determinista/LLM ×
   buscador B19/B20, con biblioteca y presupuestos comparables, sin compartir
   feedback entre brazos. Usa el mismo arranque LLM dentro de cada par y las
   semillas predeclaradas. No cuentes réplicas deterministas como nuevos datos.
   Primero comprueba el bucle entero desde la base real, no desde una regla
   ganadora entregada por el investigador. Una generación inicial no acredita
   refinamiento LLM continuo; si lo añades, debe ser otra ablación explícita.

F. Solo si corresponde por el contrato, congela el primer candidato elegible,
   ejecuta desarrollo amplio, replay y auditoría independiente. Abre conservación
   nueva después, sin realimentarla. Comprueba la historia de exposición antes
   de reutilizar la reserva B19. Los fallos del instrumento bloquean; no cuentan
   como resultados negativos del agente. Los fallos científicos cierran esa
   condición sin abrir fases dependientes.

G. La cualificación B20 no cierra S6. Prepara y encadena piloto emparejado →
   auditoría → campaña → auditoría → examen de cuatro brazos únicamente si
   pasan sus requisitos y contratos. Conserva B1–B5 y V1–V4. Respeta el arranque
   formal desde SEMILLA para demostrar el descubrimiento completo. No proclames
   ventaja del híbrido si empata con síntesis ni ventaja ARC por resultados gym.

Infraestructura de referencia: Python
`lab/arc3/ARC-AGI-3-Agents/.venv/bin/python`, runtime 3.12.13, numpy 2.3.2,
arcengine 0.9.3; modelo y hashes en
`lab/kaggle/s6b19-20261005/input/manifest.json`. Kaggle utilizó T4 y cuatro
workers CPU. Crea un notebook/paquete B20 privado nuevo; no sobrescribas B19.
Las credenciales se consumen por el mecanismo existente, nunca se imprimen
ni se empaquetan. La GPU acelera el modelo; mide por separado el cuello CPU.
Mantén recibos atómicos, reanudación idempotente, auditoría con otra caché y
revisión aritmética independiente. Respeta los límites de disco y cuota.

Entregables: contrato congelado, implementación aislada, pruebas y resultados
con hashes, análisis de ablación/ganancia/coste/regresiones, auditoría, estado
de promoción y actualización de NOW/roadmap/RXLABS_STATUS. Describe al final
qué procesos siguen activos, etapa, avance y ETA basada en medición. Si no hay
procesos, dilo. S6 solo verde con B1–B5; cierre final de 4.5 todavía requiere
transferencia ARC y retención global. No hay una garantía previa de éxito.
