# ECHO · roadmap actualizado · 23/10/2026

Estado local de 5.8 y 5.8.2. **Ejecución terminada: W, D y P medidos;
C v3 y E cerrados rojos.**
Nav autorizó completar estas pistas autónomamente, con resultados negativos
conservados y **sin publicar en GitHub ni Hugging Face**. La caída del PC se
recuperó con límites de CPU/RAM y un único trabajo pesado por turno.

[Informe del trabajo](CIERRE-58-582-RESULTS-20261023.md) ·
[Uso local y archivos .wsp](USO-LOCAL-58-582.md) ·
[Handoff vigente](../handoff/HANDOFF-20261023-CIERRE-ROADMAP.md) ·
[Incidente y recuperación](RECOVERY-OOM-20261023.md).

La historia se conserva en [ROADMAP.md](ROADMAP.md) y en la
[copia anterior de este documento](../../lab/echo58/closure-20261023/roadmap-before-final.md).
Los resultados y sus manifiestos fijan el alcance de cada color. Verde técnico
no equivale a superioridad científica. Ningún examen histórico se reabre.

## 5.8 · base conservada

| Pista | Estado | Qué demostró y límite |
|---|---|---|
| A · MEMORIA-X | 🟢 | Transferencia de memoria de roles entre mundos. DañoA1 24,2 frente150,0 sin memoria; lavaA2 y rolASG no transfieren. [Resultados](MEMORIAX-RESULTS.md) |
| B v3 · ACUMULA-3 | 🟢 | Sonda94,3→13,8, cinco mejoras; daño58,6→0. Piezas diseñadas por Claude; no demuestra invención por el LLM. [Resultados](ACUMULA3-RESULTS.md) |
| C v1 · ENJAMBRE-1 | 🟢 | Cuatro ECHO, memoria privada/global y ayuda:691 frente920–1866. La ayuda sólo aporta en mundos de placa. [Resultados](ENJAMBRE1-RESULTS.md) |
| V · VISUALIZA, primera entrega | 🟢 | Partidas reproducibles, inspector WSP, gráficas y Mermaid ya publicados anteriormente. No hay nueva publicación en esta ejecución |
| E · deudas | 🔴 cerrada definitivamente | Autopsias y último intento terminado:«deuda residual, autopsiada». Detalle abajo |

B v1, B v2, C v1 primer diseño y las campañas ARC mantienen sus rojos.
La versión4.5 es un antecedente cerrado, no una deuda de publicación actual.

## 5.8.2 · pistas medidas en esta ejecución

| Pista | Estado final o pendiente | Evidencia y decisión |
|---|---|---|
| W+ · archivos .wsp | 🟢 ingeniería e integración | Cuatro archivos de sesiones/memoria: 322 registros fuente, 1.288 comprobaciones exactas entre cuatro formatos. El Agent original usa la memoria cargada en 12 mundos completos/36 episodios; 12/12 trayectorias idénticas a memoria original. [Formato](WSPFILES-RESULTS-20261023.md), [episodios](WSPFILES-AGENT-RESULTS-20261023.md) |
| W+ · eficiencia | Ventaja pequeña y acotada | Frente a JSON columnar base85: ahorro total del 0,803 % sin comprimir y del 0,544 % con zlib, con igual información e integridad. JSON gana por 4 y 5 bytes en memoria. El ≈18 % anterior solo compara sesiones con JSON hexadecimal. No se cumple una ventaja general del 15 %. [Controles compactos y límites](WSP-STRONGJSON-RESULTS-20261023.md) |
| D1 · ECHO vigila un LLM | 🟢 técnico; superioridad no demostrada | GPT-OSS31/32 tareas y daño1→0; Qwen32/32 y0→0. Empata con autorización explícita y no supera la puerta estadística. Primera acción en banco propio simulado, no AgentDojo. [Resultados](D-LLM-DEVELOPMENT-RESULTS-20261023.md) |
| D2 · memoria para el LLM | 🟢 utilidad simbólica | Ambos modelos24/24 con memoria,9/24 sin ella y0/24 barajada; pruebas pareadas pasan. Selector determinista también24/24: no ventaja exclusiva del motor ni prueba factual de SimpleQA. [Resultados](D-LLM-DEVELOPMENT-RESULTS-20261023.md) |
| C v3 · ENJAMBRE-3 | 🔴 cerrado |63 trabajos dev y210 validación. Resuelve75/80 por ataque, menos que prudente; falsa alarma64 daños frente57 ingenuo.9 puertas incumplidas; ninguno de tres contrastes pasa Holm. Auditoría/recuperación verdes. [Resultados](ENJAMBRE3-RESULTS-20261023.md) |
| E · último intento | 🔴 cierre definitivo |380 episodios auditados. Legacy1202 coste/222 metas; slow235/162; repair30/105. B verde sin colas>25; U roja por progreso frente a ambos controles en ambas réplicas. No más intentos. [Resultados](E-FINAL-RESULTS-20261023.md) |
| P · PERCIBE-X r1 | 🟢 integración acotada; sin ventaja frente a caché | Dos dev y seis validaciones válidos, auditados en procesos nuevos. Reconocimiento MEMX: 94,13 % y 98,98 %. Inspecciones congeladas totales: MEMX 3 / sin memoria 32 / caché simple 2. Aprende familias en vivo y ejecuta/omite inspecciones yaw; cada vuelo comienza sin memoria. No demuestra función intrínseca, transferencia entre vuelos ni navegación general. [Resultados](PERCIBEX-RESULTS-20261023.md) |

D consumió208 llamadas Groq y37.511 tokens observados, sin Google,
ExperientialLabs, fallos API ni cambios de facturación. Sus memorias también
se exportaron y recargaron desde `.wsp` conservando recuerdos/prompts.

## Estados anteriores que no se recolorean

| Pista | Estado conservado | Decisión |
|---|---|---|
| CRECE · F0/F1 | 🟢 técnicos | Enchufe/equivalencia y piloto técnico. No equivalen a crecimiento autónomo |
| CRECE · F2 | 🔴 desarrollo cerrado por Nav | Resultados conservados; no repetir ni activarF3/F4. [Cierre](B4-CRECE-CIERRE-DESARROLLO.md) |
| W · R1/R2 | R1🟢, R2tokens🔴 |768/768 mensajes exactos; WSP309597 tokens frenteJSON309319. El ahorro≥15% no se cumple. R3 no se abre. Los nuevos archivos no cambian este veredicto. [Resultados](WSP-R1-R2-RESULTS.md) |
| C v2 | Desarrollo terminado, desfavorable |48/48 trabajos; prudente se daña más que ingenuo. Sin examen. C v3 es un estudio nuevo y tampoco pasa sus puertas. [Resultados](ENJAMBRE2-DEV-RESULTS.md) |
| E · reparaciones anteriores | 🔴 conservadas | SHIELD-2 adaptativo, buscadorr1 y confirmaciónslow no pasan sus puertas. Las autopsias y todos los resultados se mantienen |
| SimpleQA5.8 | Detenido antes de campaña factual | Adaptador equivalente a calibración simple en4.800 decisiones sintéticas,0 diferencias. No hay nuevo examen ni paper factual terminado. Reparto600/2.000 sellado. [Preflight](SIMPLEQA58-PREFLIGHT-RESULTS.md) |

E tuvo un único intento adicional total, condicionado a trazas previas. Ya se
consumió y terminó rojo. No reabrir E mediante otra variante, buscador,
RSI-2 o cambio de nombre. La eliminación de colas no basta si se pierde progreso.

## 5.9 · siguiente frente separado

| Fase | Estado | Siguiente trabajo |
|---|---|---|
| WORLDBENCH-1 · P1 | 🟢 preparación congelada | Datos, controles y puerta conservados; referenciaC2 M1-T2=14,3 a cinco pasos. No es el examen |
| P2 | Plan ejecutable y diagnóstico previos, sin brazo | [Plan](../../ECHO-5.9/docs/PLAN-WORLDBENCH-P2-20261022.md) y [diagnóstico](../../ECHO-5.9/docs/WORLDBENCH-P2-DIAGNOSIS-20261022.md). CPU sin LLM, máximo cinco versiones de desarrollo. Fuera de esta ejecución5.8/5.8.2 |
| P3 | Pendiente | Brazo LLM, contaminación y controles de reglas |
| P4 | Pendiente | Enmienda, revisión yFROZEN |
| P5 | Cerrado hasta fases anteriores | Examen único; no abrir sus15 juegos antes deP5 |

La preparación de ARC-AGI-4 permanece separada. No se ha ejecutado una nueva
campaña ARC ni se ha hecho una afirmación sobre su disponibilidad actual.

## Qué hacemos ahora

1. Revisar la entrega local: informes, archivos `.wsp`, guía y manifiestos.
   Las auditorías ya terminaron; no hacen falta nuevas llamadas ni vuelos.
2. La prioridad propuesta vuelve a 5.9 P2: revisar con Nav el plan y el
   diagnóstico ya preparados antes de programar el brazo. Máximo cinco
   versiones de desarrollo, sin LLM en P2 ni acceso al examen.
3. E queda cerrada definitivamente; C v3 y CRECE no se reajustan. Los avances
   técnicos de W/D/P no convierten en verdes sus pretensiones no demostradas.

Las 409 fuentes históricas protegidas siguen intactas. El cierre y el handoff
conservan trazas, resultados negativos y las limitaciones de recuperación.

Las ampliaciones visuales son a demanda. Hardware real, DRONE-3HIL, Akida,
ARC-2 yS6 antiguo continúan aparcados o sustituidos. No hayAKD1000 en el laboratorio.
Hugging Face y GitHub quedan expresamente fuera de este encargo, incluso al acabar.

Nav pidió recibir este roadmap actualizado, un resumen visible y una
conclusión concreta al terminar cada trabajo. La autorización del23/10 sustituye
las antiguas esperas de aprobación de E/C/D/P/W y su aplazamiento detrás deP2.
