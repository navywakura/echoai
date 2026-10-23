# ECHO 5.8.2 · cierre público · 24/10/2026

Por RxLabs / Nav. Agente determinista y código de investigación; no pesos de
un LLM. Licencia GPL-3.0-or-later. Publicación consolidada de 5.8 y 5.8.2.

| Pista | Resultado | Límite que forma parte del resultado |
|---|---|---|
| A · MEMORIA-X | Verde científico: transferencia de memoria de roles | No transferencia universal; lava en A2/ASG queda fuera |
| B v3 · ACUMULA-3 | Verde científico: fallos 94,3 → 13,8; daño 58,6 → 0 | Las cinco piezas las diseñó Claude fuera del agente; ECHO selecciona y encadena |
| C v1 · ENJAMBRE-1 | Verde científico: 691 frente a 920–1866 | La ayuda solo beneficia a los mundos de placa diseñados para cooperación |
| W+ · archivos .wsp | Verde técnico: 1.288 comprobaciones exactas, 12/12 trayectorias idénticas al recargar memoria | Ahorro total 0,803 % frente a JSON columnar base85, 0,544 % con zlib; JSON gana en memoria. No ventaja general del 15 % |
| D1 · veto | Verde técnico: GPT-OSS 31/32 tareas, daño 1 → 0; Qwen 32/32, daño 0 → 0 | Empata con autorización explícita; banco propio de herramientas simuladas, no AgentDojo |
| D2 · memoria para LLM | Utilidad simbólica acotada: ambos modelos 24/24 con memoria, 9/24 sin, 0/24 barajada | Selector determinista 24/24 también. No demuestra necesidad del LLM ni reducción de alucinaciones factuales |
| P · PERCIBE-X | Integración Gazebo/PX4: reconocimiento 94,13 % y 98,98 %; inspecciones 3 frente a 32 | Caché simple hace 2. Ruta prefijada, memoria vacía por vuelo; no transferencia entre vuelos ni navegación autónoma general |
| E | Rojo definitivo: deuda residual, autopsiada | Baja coste pero falla progreso; no se reabre |
| C v3 | Rojo científico | 9 puertas incumplidas; 75/80 resueltos por ataque; falsa alarma 64 daños frente a 57 del ingenuo |
| CRECE F2 | Rojo en desarrollo | F0/F1 técnicos no demuestran automejora científica |
| W R2 | Rojo de tokens | WSP 309.597 frente a JSON 309.319; se conserva |

C v2 fue desfavorable en desarrollo. B v1, B v2, C v1 inicial y los rojos ARC
se conservan. Un piloto posterior SimpleQA/Kaggle de 20 preguntas tampoco
mostró ventaja: ECHO se abstuvo en todas; no es un examen ni evidencia de
reducción útil de alucinaciones. 5.9/WORLDBENCH no forma parte de esta versión.

Los informes originales de cierre y de cada estudio se incluyen en `docs/`.
Las revisiones cruzadas son internas por agentes de IA; no certificación
externa ni revisión humana independiente. El vídeo de PERCIBE-X en la web es
una reconstrucción de telemetría guardada, no una captura de un vuelo nuevo.

## Contenido y alcance de la auditoría pública

Se publican código, pruebas, documentos, agregados y cuatro archivos WSP de
muestra. `results-5.8.2/EXPORT-INVENTORY.json` identifica los originales por
SHA256; `SOURCE-MANIFEST.json` protege los bytes públicos. La supresión de
identidad/rutas puede cambiar bytes de documentos, código y metadatos; no
se recalculan las métricas ni se sustituye la evidencia privada original.
Los hashes internos de congelaciones históricas no deben confundirse con
una firma válida sobre esta copia editada. Se conservan como procedencia.

Se omiten respuestas/cachés de proveedores, datos personales, trazas crudas
voluminosas de C/E/P y bundles de simulación. Los agregados y recibos históricos
permiten consultar resultados; **no bastan para rehacer la auditoría profunda**
de esas campañas. Los controles reproducibles incluidos comprueban el código
público y la recarga WSP. No requieren claves, API ni reabrir exámenes.

Una carga pesada cada vez. No cambiar facturación ni lanzar campañas históricas
sobre carpetas existentes. Antes de una reproducción completa se necesita
preparar los datos y dependencias declarados en el contrato correspondiente.

## Comprobación de esta copia pública

40 pruebas de WSP, JSON compacto y memoria simbólica pasan; cinco pruebas del
verificador de fuentes pasan. La CLI recarga la memoria de ejemplo: 15 decisiones
comparadas, cero diferencias entre recargas, ocho distintas del control vacío.
Son comprobaciones técnicas locales, sin API ni nuevos resultados científicos.
