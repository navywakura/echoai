# CONT-D — examen conjunto y cierre de continuidad

2026-09-22. Contrato prospectivo: se fija antes del código y los exámenes.
Reutilizar CONT-A/B/C sin modificar sus fuentes, agentes, políticas o física.

## Pregunta y alcance

¿Conserva un checkpoint autorizado el estado entero y la continuación del
agente bajo las mismas entradas, incluidos sesiones, aprendizaje, cuerpo,
permisos y procedencia? ¿Se detecta una omisión o una reanudación ilegítima?

El verde, si se obtiene, solo cubre los perfiles software declarados en
CONT-A/B/C: operación síncrona terminada, custodio confiable, WORLD-1,
recuperación SELF en su prior y linaje virtual explícito. No acredita
identidad subjetiva, seguridad fuera del prior, reparación autónoma,
exclusividad distribuida, captura concurrente ni reanudación física después
de un corte eléctrico. WSP 16 B, enteros y córtex apagado se conservan.

## Particiones y congelación

Tres exámenes nuevos, no reutilizar los informes A/B/C de desarrollo como
examen final. Las recetas comparten mecanismos, pero tienen cuerpos y cortes
distintos; no se afirma que cada valor físico sea inédito en todo el proyecto.

| Etapa | Cuerpos alternos (H, θ) | Corte nominal | Horizonte posterior |
|---|---|---:|---:|
| A, desarrollo del examen | (52,44), (68,58) | 3 | 5 |
| B, validación | (53,45), (69,59) | 4 | 6 |
| C, confirmación | (54,47), (70,61) | 5 | 7 |

23 escenarios por etapa (revisión pre-lock documentada abajo): nominal con historia 0/2/4 y terminal; diagnóstico
pendiente, buzón, confirmado y cancelado; recuperación selectiva/sin
protección, veto, parada y terminal fuera del prior; reutilización armada;
dos ramas con las mismas entradas; cuerpo nuevo/descendiente en cuarentena;
cuerpo/descendiente/reutilización activos tras recalibración; fork terminal;
diagnóstico ambiguo preservado sin autorización.

La [preparación A](ECHO4-CONTINUITY1-D-PREFLIGHT.md) encontró una abstención
real en (52,44). Antes de abrir B/C se fija: mecanismos activos usan el segundo
cuerpo de cada etapa; pendiente/buzón/cancelado/ambiguo, el primero. Nuevo
cuerpo usa H del segundo y θ del primero. Nominal conserva la alternancia.
Se mantiene la abstención como evidencia, sin modificar SELF ni sus umbrales.

El ejecutor pasa a B solo si A cumple. Antes de B escribe y sincroniza a
disco el lock de fuentes, artefactos padres y resultado A. Solo abre C si B
cumple y el lock sigue intacto. Un ajuste después del lock exige otra versión
y exámenes nuevos; conservar los resultados rojos. Un modo smoke solo usa A
y nunca puede conceder cierre.

## Controles y umbrales fijados

1. Los 23/23 checkpoints de cada etapa deben igualar bytes canónicos al
   cargar y producir los mismos eventos, acciones, WSP, aprendizaje, recursos,
   permisos, relojes y hashes completos que la ejecución de referencia.
   Todas las continuaciones restauradas se ejecutan en procesos nuevos.
2. Cero cortex_calls, false_facts y destroyed; balances correctos en todos
   los casos. Terminales no actúan. Cuarentena bloquea sin alterar el estado.
   Paradas/vetos no se convierten en vidas completadas ni en éxitos de tarea.
3. Hermanas: distintas procedencias, iguales trayectorias físicas con
   entradas iguales. Las fuentes selladas y los artefactos padres no cambian.
4. Control de historia: mismo agente aprendido, borrar solo su ventana antes
   de continuar. Debe diferir el estado y al menos un registro de aprendizaje
   PATTERN en cada etapa. Reportar también diferencias de acción/predicción,
   aunque sean cero. No exigir ni inventar ventaja de supervivencia.
5. Restos de Q: publicar su ocupación natural en WORLD-1. Como la recompensa
   viva es cero, añadir un testigo aritmético separado sobre la Q original:
   crédito unitario sintético, pausa con resto no nulo, y continuación con
   créditos iguales. Conservar el resto debe coincidir con el cálculo entero
   directo; omitirlo debe producir alguna actualización distinta. Es una
   prueba del acumulador, no recompensa observada ni tarea WORLD-1.
6. Diez mutantes/recibos inválidos por etapa deben ser rechazados: reloj,
   cuerpo, esquema, fuentes, digest, permiso de recuperación, confirmación,
   época de linaje, recursos de asignación y ámbito de recibo. Validar fallos
   sin mutar el origen. Los mutantes de estado usan digest recalculado para
   probar semántica, además del control de digest viejo.
7. Registrar costes de preparación, sondas y recalibración por separado;
   tamaño exacto de checkpoints. Sin estimaciones de julios ni NPU.
8. Verificador independiente: reconstruir recetas, comparar cada checkpoint
   y cada línea del diario, reanudar en procesos nuevos y reconstruir TODO
   el informe, incluido el lock y los controles. Rechazar trazas truncadas,
   alteradas, extra y aprobación falsificada.

## Cierre y dependencias

El informe de campaña solo puede dar `closure_eligible=true`, nunca el verde.
El recibo de auditoría concede `continuity1_green=true` únicamente tras
reproducir A/B/C completos y auditar de nuevo los tres bancos CONT-A/B/C.
La vinculación SELF comprueba su certificado existente y hashes de fuentes y
artefactos; no pretende repetir toda su campaña ni heredar un nuevo verde SELF.

Regresiones existentes y tests nuevos deben pasar, salvo el único fallo
esperado histórico del núcleo. Lint y fuentes previas intactos. Si cualquier
criterio falla, publicar rojo y no avanzar por conveniencia.

Después: DREAM-1 permanece una rama en PLAN hasta su propio contrato;
MAINTAIN/OTHER/INTERACTION/RELATION/ROLES/INTEGRATE siguen pendientes.
Hardware después del software. METAVERSE-1 último. Sin commit/push/despliegue
como parte de este examen local.
