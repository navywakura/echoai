# DREAM-D v2 — feedback de replay y promoción con ancla fija

2026-09-22. Contrato prospectivo; se fija antes de ejecutar casos nuevos.
V1 permanece roja e inmutable. Su historial abierto es desarrollo, nunca
confirmación independiente para v2. No se cambia SELF, WSP, física o gate.

## Cambios motivados por desarrollo

V1 seleccionó una política de ocho pasos que no generalizó; comparar solo
con ella permitió conservar una estrategia peor que el fijo original.
V2 conserva el DSL y el intérprete sellados: seis ensayos, hasta 12 pasos,
sin código ejecutable generado. Añade:

1. Resúmenes públicos de estrategias completas (seis rotaciones), no solo
   ensayos aislados. No se entregan causas, cuerpos exactos ni checkpoints.
2. Dos llamadas Qwen por ciclo: propuesta y revisión con feedback medido por
   replay de sus primeras propuestas. Hasta ocho candidatos; sin reparar sus
   órdenes/presupuestos a mano. Pesos fijos y gramática/validador de v1.
3. Selección robusta: maximizar el mínimo margen de resolución frente al
   fijo por lote histórico, después resolución total y después menos pasos.
   Margen en partes por millón enteras; no se usa la verdad privada.
4. Promoción tras examen: invariantes, cero errores/terminalidades y ninguna
   regresión de resolución/coste lexicográfico frente a incumbente **y fijo**.
   Incumbente inicial: política activa de v1. Rechazo conserva incumbente;
   un candidato rechazado no puede dar verde aunque otro brazo sí pase.

Antes del primer examen se conserva el historial completo v1: 320 contextos
en cuatro lotes de 80. Durante v2 se añade cada lote solo tras evaluarlo.
Se persisten selecciones y versiones con fsync y enlace hash antes de abrir
el nuevo examen. Directorios exclusivos: no sobrescribir evidencia.

## Examen nuevo y criterio (sin facilitar el umbral)

Tres ciclos, 16 cuerpos × 20 condiciones = 320 casos por ciclo/brazo.
Misma familia SELF: acoplamientos booleanos y pulso -16,-4,0,4,16.
Dominio prospectivo: H 65..96, theta 40..60. Cada ciclo elige cuatro cuerpos
por estrato H 65..72, 73..80, 81..88, 89..96 mediante `random.Random(260923)`.
Muestreo de pares sin reemplazo; excluir pares de v1, tests DREAM y los
exámenes finales SELF. No filtrar por resultados, seguridad predicha o éxito.
El generador se ejecuta solo para el lock de campaña; tests usan otras recetas.

La estratificación evita que cada ciclo pertenezca a una banda corporal
diferente como en v1. Es un cambio explícito de diseño poblacional, no una
réplica del examen v1. No prueba generalización fuera de este dominio.

Verde exige **en cada ciclo** al menos +10 puntos porcentuales frente a
orden fijo y +5 frente a aleatorio: +32 y +16 aciertos sobre 320. Son las
mismas proporciones que +8/+4 sobre 80 en v1. Además: propuestas Qwen reales
válidas en las tres llamadas de cada ciclo, al menos una mejora histórica
estricta, promoción aceptada/conservada sin regresión, cero errores y
terminalidades en todos los brazos, invariantes, paridad replay/online y
auditoría reconstructiva íntegra. Regresiones de código deben pasar.
No mover umbrales, semillas, particiones ni fuentes tras ver un resultado.

## Controles

Nueve brazos con máximo idéntico de 12 pasos nativos por caso: DREAM,
incumbente, fijo, aleatorio por caso, sin Qwen, sin feedback, sin historial
en el prompt, sin selección replay y SELF activo existente.

- Sin Qwen: selección robusta entre ocho órdenes deterministas (seis
  rotaciones y dos permutaciones pseudoaleatorias con semilla fija).
- Sin feedback: solo los cuatro candidatos de la primera llamada.
- Sin historial en prompt: tercera llamada real Qwen, sin los resúmenes,
  pero sus candidatos sí pasan por el mismo selector replay.
- Sin selección: primera propuesta válida de la llamada con historial.

Las ablaciones con cuatro frente a ocho candidatos mezclan feedback con
presupuesto de propuesta; no aíslan por sí solas un efecto causal puro.
El control sin Qwen puede empatar o ganar: no se exige vencerlo, pero en tal
caso no se atribuye la ganancia al LLM. No se afirma equivalencia de CPU ni
energía por equiparar pasos nativos o número de candidatos.

## Costes, custodia y límites

Qwen local identificado por archivo/hash; llama.cpp propio, solo loopback.
Nueve llamadas como máximo, 512 tokens generados por llamada, contexto8192,
temperatura0 y semilla `260922 + 3*ciclo + ronda`; timeout240s. Se cuentan
errores, tokens, latencia y arranque, más calibración, recolección, pasos
online, consultas y pasos representados de replay. Los costes históricos
v1 se reconocen como coste hundido; reutilizarlos no los hace gratuitos.
Replay no ejecuta física ni LLM; ausencias son desconocidas y consumen cuota.

Fuentes v1 se importan, no se editan. Se cotejan las ramas v1 contra sus
digests y se reconstruyen físicamente para la auditoría; entradas privadas
solo para el juez. Certificado v1 y todos sus artefactos quedan vinculados.
La auditoría reproduce selección, física, decisiones, versiones e informe
y audita recibos del modelo sin prometer reinferencia bit a bit.
Solo su recibo concede `dream1_green`; el informe conserva ese campo false.

Verde sería acotado a exploración diagnóstica restaurada en WORLD-1, no
pesos autoentrenados, conciencia, autorreparación o agente integrado.
NEXUS-0 conserva córtex OFF. Discord, hardware y METAVERSE-1 no se tocan.
