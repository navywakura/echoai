# Estado conservado de ECHO al 10 de octubre de 2026

El propietario solicita guardar los avances recientes en el repositorio
oficial privado `navywakura/echoai` antes de comenzar ECHO-5. Este corte
conserva código, documentación, inventario e ideas de investigación. No es
una publicación final de ECHO-4.5 ni el comienzo de una campaña ECHO-5.

| Línea | Estado respaldado por los archivos revisados |
|---|---|
| ECHO-4.5 | Distribución beta existente. S6 permanece sin pase; el cierre oficial sigue pendiente de las mediciones acordadas. |
| B23-R4 | Cerrado sin propuestas aceptadas. Su autopsia y límites están documentados. |
| B24-R1 | Último estado local: `WAITING_GPU_QUOTA`, versión 3. Conserva checkpoint antes de la auditoría independiente de `s-B24-C/candidate/003`. La renovación anunciada es el 17 de octubre a las 02:00 de Madrid. No se certifica aquí su finalización ni se relanza. |
| ARC V3 por lotes | Evaluador y calibración disponibles. El recibo registra 32 tareas conocidas, 0 exactas, 0 errores, 0 timeouts y 0 llamadas LLM. El lote público completo continúa sin abrir; esa calibración no es una puntuación oficial ARC. |
| ECHO-5 | Entorno de preparación, comandos de comprobación e inventario estático. No contiene todavía un agente nuevo integrado, GUI, adversario ni entrenamiento ECHO-5. |
| ECHO-5.1 / 5.5 | Visiones de organización multiagente y sistema persistente, pendientes de implementar y validar. |
| ECHO-RSI | Programa futuro; los resultados históricos permanecen con su veredicto. La nueva investigación de S6 se retomará después de 5.5. |

El inventario de ECHO-5 revisa las familias existentes antes de integrarlas:
representación WSP/QN, memoria CAM, control y aprendizaje, cuerpo y robótica,
continuidad, interacción y tribu, simulación de hipótesis, memoria causal,
DSL de rejillas, interfaces, herramientas y bancos. Las dependencias
identificadas por AST no equivalen a cobertura de pruebas ni a certificación
nueva. La robótica parte del trabajo previo de Gazebo/PX4; HIL y jaula física
siguen pendientes.

La idea nueva inspirada en GAN propone un generador de soluciones, un buscador
de contraejemplos comprobables y un verificador independiente. El aprendizaje
se mediría frente a búsqueda actual y casos aleatorios con el mismo
presupuesto total, sobre problemas nuevos. El ciclo no garantiza mejora
ilimitada ni convierte al discriminador en detector universal de verdad.
Su [propuesta completa](../ECHO-5/docs/ADVERSARIAL-LEARNING-PROPOSAL.md) conserva
las referencias científicas, límites, piezas reutilizables y comparaciones
pendientes. Todavía no se ha programado ni medido.

Documentación de referencia:

- [Inventario previo a ECHO-5](../ECHO-5/docs/MODULE-INVENTORY.md).
- [Visión de ECHO-5, 5.1 y 5.5](ECHO5-51-55-RESEARCH-VISION.md).
- [Decisión de transición desde 4.5](ECHO45-TO-ECHO5-DECISION-20261009.md).
- [Forensia B23-R4](ECHO45-S6-B23-R4-FORENSICS-20261008.md).
- [Contrato B24](ECHO45-S6-B24-DESIGN.md) y [recuperación R1](ECHO45-S6-B24-R1-RECOVERY-20261009.md).
- [Evaluador ARC por lotes](ECHO45-ARC-V3-BATCH-20261009.md).
- [Plan ECHO-RSI-1](ECHO-RSI-1-LAB-PLAN.md), [RSI-2](ECHO-RSI-2-RESEARCH-PLAN.md) y [familia futura de modelos](ECHO-PRODUCT-FAMILY-AND-SAAS-PLAN-20261007.md).

El repositorio oficial tiene la antigua carpeta `echoai/` como raíz y los
seis auxiliares matemáticos bajo `core/`. Al sincronizar se conservan esas
rutas de distribución y las mejoras del instalador y de echo-nexus 1.5.2.
Los documentos y catálogos históricos mantienen las rutas y hashes de su
origen: describen aquel expediente, no una nueva certificación de los
archivos reorganizados. Los scripts operativos archivados pueden contener
rutas del laboratorio y se guardan como evidencia; no se ejecutan al instalar.

Las claves, entornos virtuales, pesos externos, cachés de dependencias y
binarios CUDA descargados no forman parte del código del proyecto. La web
heredada y echo-discord continúan separados según las decisiones anteriores.
La copia de evidencias de investigación conserva procedencia y hashes; sus
estados son una fotografía de este corte, no un servicio de estado en vivo.
