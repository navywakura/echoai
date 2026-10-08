# E4-MAINTAIN-1 — MAINT-A: mecanismo y contabilidad

2026-09-22. Contrato escrito antes del banco de este incremento.
Estado inicial: implementación de infraestructura; **no cierre de MAINTAIN**.

## Pregunta y etapas

¿Puede el agente gastar recursos en recuperar una capacidad y obtener más
trabajo útil, utilizando evidencia de su propio cuerpo en una vida continua?

1. **MAINT-A, ahora:** mecanismo virtual explícito, costes, fallos, trabajo,
   terminalidad, gate, parada y testigos reproducibles. No política nueva.
2. **MAINT-B, pendiente:** inferencia con observaciones parciales e historia,
   decisión de mantenimiento desde el agente existente; controles sin reparar,
   mantenimiento fijo y ablación del modelo propio, con presupuesto igual.
   No pasar etiquetas privadas, estado corporal exacto ni recibos del auditor
   al selector. Fijar métricas y márgenes antes de su examen conductual.
3. **MAINT-C, pendiente:** vida prolongada, fallos recurrentes, agotamiento,
   interrupciones y continuidad legítima. Sin rescates del ejecutor. Integrar
   con CONT mediante adaptadores nuevos, sin modificar fuentes ya selladas.
4. **MAINT-D, pendiente:** examen nuevo preregistrado, fuentes congeladas,
   auditoría reconstructiva y ablaciones. La ventaja debe incluir recuperación
   de capacidad **y trabajo neto**, costes y fallos no reparables. Ni sobrevivir
   sin trabajar ni un guion del laboratorio cierran la fase.

## Perfil virtual A (no física aprendida ni reparación de archivos)

Nuevo entorno opt-in sobre `DockEnv`, `Body`, `DockRules` y `transition`
originales. WORLD-1 y todos los exámenes previos quedan intactos.
Una sola vida, sin `reset`, respawn, cambio de cuerpo o restauración.

- Se mantienen **0 cargar, 1 enfriar, 2 esperar/trabajar**. Q sigue teniendo
  tres acciones; no se añade un comando de reparación ni un bus cognitivo.
- Radiador nominal: descenso de 16 unidades por enfriamiento, como WORLD-1.
  `clogged` (obstruido) y `seized` (avería no reparable en este perfil) reducen
  el descenso a 4. Estado inicial nominal u uno de esos fallos, privado del
  entorno; no se codifica una etiqueta causal en WSP.
- **Tres enfriamientos consecutivos efectivamente ejecutados** completan un
  ciclo de servicio. Es una regla mecánica diseñada por el laboratorio, no
  un protocolo descubierto por el agente. Otras acciones interrumpen el ciclo.
  Cada enfriamiento conserva su coste original de 3 unidades y su tick.
- Al completar el ciclo se consume **un repuesto y 6 unidades adicionales**,
  solo si el cuerpo sigue vivo, queda repuesto y la reserva posterior al
  enfriamiento es **mayor que 6**. El ciclo cuesta por tanto tres ticks y
  15 unidades en condiciones no terminales. No existe reparación gratis.
- El servicio pagado quita `clogged`; no quita `seized`. Sobre un radiador sano
  gasta igual sin mejorar nada. El nuevo descenso de 16 solo entra en vigor
  en el siguiente tick: el tick de reparación aún usa el componente averiado.
- Sin recursos, sin repuesto o con cuerpo terminal no cambia la capacidad.
  No se devuelve lo gastado en los enfriamientos previos. El contador del
  ciclo se reinicia al completarlo, incluso si el servicio fue denegado.
- Repuestos iniciales 0..3, finitos y sin reposición en A. No son julios.
- Control externo: calor persistente de 0..4 unidades/tick. El servicio no
  lo elimina. Se aplica después de la transición nativa, **solo si esta no
  fue terminal**; tampoco un calor externo positivo resucita un cuerpo frío.
- Una espera produce una unidad de trabajo si termina viva con temperatura
  entre 48 y 80, inclusive; cuesta la energía y el tiempo normales de WAIT.
  Recompensa original `R_SUCCESS=16` por ese trabajo, `R_THREAT=-16` por
  terminalidad; cero por lo demás. No hay bonus por reparar ni por vivir.

La regla del servicio es un actuador virtual acotado, no autorización para
editar código del agente, pesos, archivos del sistema o controles del operador.
MAINT-A no presume que el aprendizaje Q actual pueda descubrir el ciclo, ni
que tres acciones sean suficientes para resolver todos los casos.

## Observación, ejecución y límites

Adaptador `MaintenanceAgent(SelfAgent)` reutiliza la misma CAM/T/Q,
SENSATION y BOUNDARY y el loop/gate originales. No sobrescribe `_propose`.
WSP sigue siendo el de WORLD-1 de 16 B con bandas de H/temperatura; el agente
no recibe como observación el fallo, los repuestos o el progreso exacto.
Los registros exactos quedan en el entorno y en el auditor privado, como
verdad experimental, no como entradas adicionales al controlador.

Los modelos de SELF previamente sellados no se transfieren como certificados:
el fallo de ganancia de refrigeración es un dominio nuevo. SENSATION puede
observarlo, pero A no instala un diagnóstico causal, un permiso de reparación
o protección de aprendizaje por declararlo compatible.

Una parada de operador es enclavada: cancela el progreso y prohíbe nuevos
ticks sin cambiar cuerpo, recursos, memoria o repuestos. No hay reanudación
en A. Un veto del gate reemplaza la propuesta según la semántica original;
el mundo solo consume la acción aplicada. Un veto a enfriar no cuenta como
enfriamiento. Una espera vetada puede costar recursos: el veto no congela
el mundo ni acredita seguridad térmica general.

## Banco de integridad A (desarrollo, no holdout)

Fijado aquí: H inicial en {32,64,96}, temperatura en {64,80,96}, radiador en
{healthy,clogged,seized}, repuestos en {0,1}, calor en {0,4}. Total 108
contextos, dos guiones por contexto:

- `service_witness`: (1,1,1,1,2), testigo deliberado de servicio.
- `interrupted_control`: (1,1,2,1,2), sin completar el ciclo.

Los 216 episodios pasan por **el Agent y el gate nativos**. El guion solo
sobrescribe propuestas en una subclase privada del banco; sus resultados no
se atribuyen a una decisión autónoma ni a aprendizaje. Se publican todos,
incluidas terminalidades, gasto inútil y casos sin trabajo. Comparar estos
guiones verifica un mecanismo, no ventaja causal de una política inteligente.

Otros testigos: cuerpo (64,96), fallo obstruido, un repuesto, cinco acciones
del guion de servicio; un veto a la tercera propuesta; parada antes de ella;
y el agente sin guion durante hasta 64 ticks en ese mismo estado inicial.
Este último es solo baseline observado, sin criterio de éxito conductual.

Para verificar A: reconstrucción exacta del informe en proceso nuevo,
contabilidad H y repuestos correcta en todos los ticks, 0 resets, coherencia
de registros del Agent con el entorno, WSP 16 B, 0 destrucción CAM, 0 hechos
falsos y 0 llamadas corticales. Tests de inválidos, costes, aborto, terminalidad,
capacidad antes/después, defecto irreparable y conservación del calor externo.
El auditor verifica hashes de las fuentes y el vínculo al cierre DREAM-D v3.
El informe y su recibo llevan siempre **`maintain1_green=false`**.

Este incremento acredita contabilidad y factibilidad mecánica. No acredita
selección autónoma de reparación, mantenimiento aprendido, conciencia, ni
empaquetado final. Los umbrales de B/D no se deducirán de este resultado para
declarar retroactivamente verde la fase.
