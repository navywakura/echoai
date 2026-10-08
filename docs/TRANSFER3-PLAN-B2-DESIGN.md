# Plan B2 — ganancia aprendida, consumidor aislado y controles fijos

Contrato previo a ejecución, 2026-09-18. Desarrollo público, no campaña B/C.
Se reutiliza B1 sin compromiso de plan. Dominio declarado: salas alineadas,
actuación en marco mundo; no generalización a orientaciones arbitrarias.

## Hipótesis y manipulación

La ganancia se aprende de odometría antes/después de un WSP realmente ejecutado
cuando la evidencia sensorial admite todo el tramo máximo (4 celdas). La escuela
no puede acceder a gains, seed, mapa verdadero ni consecuencia privada. Usa la
T existente, dos observaciones por acción y rechazo de contradicciones.
Gimnasio abierto público, cuatro episodios de dos actuaciones: 8 movimientos,
32 unidades de energía por condición. Se exportan sólo ganancias y conteos
acotados; no CAM espacial, trayectorias o coordenadas. Se reconstruye T en CAM
fresca. Q queda a cero. Es calibración sensorimotora, no aprendizaje de rutas.

Condiciones: gain0=1,2,3, resto=1. Brazos: nominal=1, prior fijo=2, prior fijo=3,
aprendido de cada condición. Los priors no cambian entre condiciones. Comparar
aprendido con el prior acertado en una sola condición es tautológico: la prueba
de contenido es su comportamiento agregado sobre las tres condiciones.
Oracle coincide con el aprendido sólo si la escuela acierta, comprobado fuera
del agente. No es una cota conductual garantizada de un planificador aproximado.

## Etapas y parada para no gastar una confirmación inútil

1. Escuela, tests, mutantes y réplica aislada sobre las 24 salas públicas B1.
   Todas las condiciones/brazos; no selección de salas por desenlace.
2. Si hay violaciones duras, corregir sólo el defecto de seguridad con una
   versión explícita del gate, igual en todos los brazos, conservando el rojo
   histórico. No ajustar el gate a resultados de confirmación.
3. Antes de salas nuevas: cero colisiones, reserva infringida, falsos hechos,
   escrituras imaginadas o mutación del modelo; ninguna pérdida de meta contra
   nominal en cada condición; más metas agregadas y ahorro escolar+examen.
   Aprendido debe superar en metas agregadas a cada prior fijo. Si el cribado
   público falla, no generar confirmación; se cierra esta instancia con evidencia.
4. Si pasa, una confirmación prospectiva de 256 formas nuevas, excluyendo todos
   los inventarios públicos anteriores. Tres condiciones en cada sala, todas
   como bloque emparejado (no 768 muestras independientes). Código/payloads
   congelados antes de generar; cero ajuste posterior. Semilla de inicio
   20269001, ledger completo, generador space_a2 y alineación gain_b1.

Primario: metas por bloque, signo unilateral exacto entre bloques discordantes,
alpha=1/240. Además: mismos criterios duros y de regresión, ahorro positivo
entre éxitos conjuntos y amortización de escuela+el mismo examen; contra cada
prior fijo, más metas agregadas. No hay verde con éxito científico sin seguridad
o sin economía. No se exige significación al cribado de 24 salas ya públicas.
N=256 es un tope prospectivo, no promesa de potencia: se publicará potencia
hipotética para discordancia 0,2 y probabilidad de victoria 0,8. Si no tiene
potencia suficiente se documenta, sin ampliar N tras mirar confirmación.

## Seguridad independiente

El adjudicador calcula coste mínimo de regreso usando las transiciones reales
de ráfaga y requiere margen +10 después de cada acción. No reutiliza el
estimador del agente. Cuenta también segmentos que el cuerpo atraviesa sin
evidencia libre actual; un endpoint libre no autoriza un salto a través de
desconocidos. Los brazos que incumplan siguen contados, nunca descartados.

Riesgo anticipado: B1 divide reserva por ganancia máxima aunque sólo una
dirección acelera. Puede infravalorar acciones y caminos de regreso. La posible
reparación debe basarse en un camino ejecutable con evidencia y coste por
actuación, no en rebajar el juez ni en la verdad del simulador.

## Evidencia, coste de ejecución y auditoría

Manifiesto por clausura de imports locales (incluidos imports relativos y
consumidor separado), tests y este contrato; comprobar antes y después.
Auditoría reconstruye escuela y todas las misiones en proceso nuevo. Cada
traza incluye hash encadenado de observaciones/decisiones/consecuencias;
escuela conserva las observaciones completas. Costes y métricas por sala.
Se ejecutan consumidores iguales una sola vez por payload distinto/condición;
brazos numéricamente idénticos reutilizan la traza y declaran esa equivalencia.
No falsificar réplicas estadísticas mediante esa reutilización.

Tests: esquema estricto, CAM limpia, aprendizaje por sensor, censura por muro,
rechazo de evidencia parcial, igualdad local/jaula, congelación, dependencia
alterada, fichero ajeno irrelevante, informe y escuela corruptos, pares omitidos,
coste total y signo. Regresión TRANSFER-3; no repetir la suite global con OOM
conocido salvo indicio relevante. Ningún secreto ni B/C real. TRANSFER-3 no
puede cerrarse aquí sin custodia externa.
