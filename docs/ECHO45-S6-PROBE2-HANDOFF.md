# S6-PROBE2 · revisión y encargo de ingeniería

2026-10-01. Preparación del siguiente control de capacidad a partir de
[PROBE1](ECHO45-S6-PROBE1-RESULTS.md). Este documento es una revisión para
Claude; no es el contrato congelado y no lanza partidas. S6 sigue pendiente.

## Decisión

Sí: preparar un sondeo **dirigido después de conocer PROBE1** que busque
conservar la mejora de la partida A53 y eliminar las pérdidas de score.
Mantener primero la gramática actual y una sola reparación por propuesta.

Corrección de la interpretación: **+4 niveles en A53 sin ninguna pérdida
individual ya bastaría para V3: 378 → 382 ≥ 380**. No hace falta sumar el
+1 de A18. La combinación no puede suponerse aditiva y no debe ser el primer
objetivo. El candidato 77 ya consigue +5 con un solo parche, aunque falla
por pérdidas de score; el 178 consigue +4 y también falla por score.

## Evidencia contrastada por Codex

Lectura de los 200 recibos individuales y 50 pares; recálculo de ganancia,
niveles y V3 desde sus efectos por partida: cero discrepancias. Solo A18 y
A53 ganan niveles. HOLD cambia acciones en 30/105 candidatos; REVALIDATE_NOOP
en 28/30, sin ganancias de niveles. La lectura inicial de tres HOLD no
sustenta que el operador carezca de efecto.

| Candidato | Cambio | Ganancia neta | Pérdidas |
|---|---|---:|---|
| 77 | HOLD=1 | +5 | Score en A51 y A76; sin pérdida de niveles |
| 178 | HOLD=0 | +4 | Score en A68 y A77; sin pérdida de niveles |

El SHA-256 del `result.json` contrastado es
`16afe62ed26ff783f320fe65cc998103e0587683dbced0318b60b17a9102ba64`.
Este recálculo documental **no sustituye** las reejecuciones independientes
previstas en §10 del [contrato PROBE1](ECHO45-S6-PROBE1-DESIGN.md).

## Encargo a Claude: contrato y código aislado

1. Crear `docs/ECHO45-S6-PROBE2-DESIGN.md`, `seed/s6probe2.py` y
   `tests/test_s6probe2.py`, con artefactos en un directorio PROBE2 propio.
   Importar y reutilizar lo existente; preservar fuentes y resultados
   congelados de B12/PROBE1. En esta preparación no se juegan partidas.

2. Declarar la selección posterior a PROBE1, las hipótesis y el presupuesto.
   Primera hipótesis: las observaciones disponibles al consumir HOLD
   permiten distinguir cuándo una espera corta ayuda de cuándo empeora
   el score. Segunda: las guardas actuales expresan esa distinción.
   El fallo de una búsqueda acotada no refuta por sí solo esas hipótesis.

3. Analizar las lecturas reales de HOLD, las primeras divergencias y los
   efectos de los candidatos 77 y 178 en A53, A51, A76, A68 y A77; incluir
   A18 al describir sus efectos. Usar los datos existentes para preparar
   candidatos, no para declarar que ya funcionan. Las trayectorias de la
   base y de los programas modificados pueden divergir después.

4. Generar variantes de **HOLD 0 y 1** con las guardas legales de la
   gramática actual. Congelar lista, orden, selección, límites y hashes
   antes de las mediciones nuevas. Deduplicar propuestas idénticas;
   una firma de activación común no demuestra equivalencia de conducta.
   Fijar cuántos representantes se medirán si se agrupa por firmas.

5. Las guardas solo pueden consultar observaciones disponibles al decidir.
   No introducir índices de partida, semillas, identidad del mapa,
   respuestas esperadas, datos futuros o reglas que reconozcan un caso
   concreto. Los números A53/A51/etc. sirven para analizar y seleccionar
   las mediciones, no son entradas de la política. No añadir condiciones
   fuera de la gramática sin un contrato distinto y explícito.

6. Definir un cribado económico y determinista: primero comprobar la mejora
   objetivo en A53 y las pérdidas conocidas, con criterios y orden fijados.
   Aclarar que puede descartar soluciones de otros tipos; no es un censo
   exhaustivo. Todo candidato que sobreviva se mide en **las 80 partidas A**.
   Solo estas cinco partidas no permiten declarar V3 ni ausencia de pérdidas.

7. Mantener V3 exactamente: **≥380 niveles y cero pérdidas individuales de
   niveles o score**, con la tolerancia nativa. Cada éxito necesita replay
   completo idéntico. Prerregistrar también replays de negativos; una
   discrepancia, error o timeout detiene la medición y conserva evidencia,
   sin convertirse en un resultado negativo de capacidad.

8. Coste y custodia: cero LLM, B y examen cerrados, rechazo de especificaciones
   ajenas a A antes de jugar o consultar caché; cuatro procesos, mismo runtime
   congelado. Presupuestar base, cribado, evaluaciones completas, replays e
   intentos interrumpidos. Guardar recibos de forma duradera antes de borrar
   diarios efímeros; conservar diarios de errores y replays. Medir un pequeño
   `estimate` después de la revisión, sin inventar una duración previa.

9. Tests sin partidas para separación A/B/examen, paridad, límites de
   gramática, orden y hash del plan, reanudación, presupuesto, discrepancias
   de replay y borrado seguro. Mantener observabilidad mediante los registros
   existentes, sin un bus nuevo ni texto de observación como entrada al agente.

## Responsabilidad de Codex y puerta de ejecución

Codex revisa contrato, plan, código y pruebas antes de congelar y calibrar.
Antes de medir PROBE2 debe quedar cerrada la auditoría independiente pendiente
de PROBE1: fuentes, planes, procedencia y una muestra reejecutada en proceso
y caché distintos. Fijar la muestra antes de esa reejecución; debe incluir
los candidatos 77 y 178, además de un +1 sin pérdidas y un control negativo.
Mantener este recibo de auditoría separado de los 25 replays internos.

Después de una calibración válida, su tiempo y recursos medidos determinan
la estimación y permiten continuar dentro del presupuesto autorizado. Un
perfil cambiado, paridad incorrecta o replay distinto bloquea la ejecución;
no se modifica retrospectivamente el contrato para aceptar el resultado.

## Interpretación y continuidad hacia S6

- Si una reparación individual pasa, demuestra capacidad de la gramática
  para alcanzar V3 desde 378 en A. No demuestra descubrimiento autónomo ni
  cierre de S6. No mostrar al modelo los parches ganadores, sus guardas como
  respuestas sugeridas ni etiquetas del sondeo; tampoco promoverlos a ECHO.
- Si ninguna pasa, informar «sin solución en esta búsqueda dirigida y con
  este presupuesto». Separar rechazo del cribado, fallo en A completo y
  mediciones incompletas. No afirmar que el lenguaje está agotado.
- Una ampliación de features, guardas, operadores o propuestas de dos
  parches requiere otra condición declarada; no entra silenciosamente aquí.
- Solo tras el control de capacidad procede una condición nueva de piloto
  autónomo, campaña y examen reservado de cuatro brazos con B1–B5. ECHO y
  FIJO tendrán las mismas posibilidades; SIN FILTRO recibirá las propuestas
  reales de ECHO. El control humano no se cuenta como victoria de ninguno.
