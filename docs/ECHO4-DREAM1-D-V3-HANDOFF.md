# Prompt de continuidad — implementar DREAM-D v3

**Actualización 2026-09-22: este prompt ya se ejecutó.** DREAM-D v3 está verde
en su perfil WORLD-1 restaurado; auditoría válida, `dream1_green=true`.
Consultar [resultados y límites](ECHO4-DREAM1-D-V3-RESULTS.md) y el
[roadmap actual](ROADMAP.md). Siguiente fase: MAINTAIN-1, todavía pendiente.
El texto siguiente se conserva como registro de la planificación previa;
no volver a abrir los mismos exámenes como si fueran casos nuevos.

Guardado originalmente el 2026-09-22, cuando v3 estaba en PLAN, no implementada.
Este documento se utilizará cuando el usuario retome el trabajo. Guardarlo
no inicia experimentos ni programa una ejecución automática.

## Prompt para la próxima sesión

Retoma el desarrollo de ECHO-4 en `/home/roger/REALRXOS/RXos/echoai`.
Implementa DREAM-D v3 partiendo de la evidencia de v2. El objetivo es mejorar
la exploración mediante **ensayos más informativos y seguros**, no conseguir
un verde cambiando umbrales, semillas o etiquetas de resultados anteriores.

### 1. Lee y comprueba el punto de partida

Lee primero `CLAUDE.md`, después `docs/05-NEXUS-0-SPEC.md` y `AGENTS.md`;
respeta también sus instrucciones de lectura. Después consulta:

- `docs/NOW.md` y `docs/ROADMAP.md`.
- `docs/ECHO4-DREAM1-D-V2-DESIGN.md`.
- `docs/ECHO4-DREAM1-D-V2-RESULTS.md`, incluido el diagnóstico posterior y
  su código de reproducción de la cota del catálogo.
- `echo4/dream_v2.py`, `echo4/dream_v2_bench.py` y sus pruebas.
- Las dependencias que se reutilizan: `dream_policy.py`, `dream_probe.py`,
  `dream_qwen.py`, `self_attribution.py` y `self_probe_world.py`.
- `lab/echo4/dream1-d-v2/report.json`, `audit-receipt.json` y `lock.json`.

Hay muchos cambios previos y archivos sin seguimiento en el repositorio.
Inspecciona el estado real; no hagas limpieza, reset ni commit global.

### 2. Estado confirmado: no empezar de cero

WORLD, SENSATION, BOUNDARY, SELF y CONTINUITY tienen los estados y límites
documentados en el roadmap. DREAM-A/B/C están implementados; DREAM-D v1 y
v2 permanecen rojos. ECHO-4 completo NO está cerrado.

V2 ya incorpora Qwen local real, feedback de replay, selección por peor
margen histórico, comparación contra incumbente y fijo, versionado,
reversión, presupuestos y auditoría reconstructiva. No hay que reescribir
esa infraestructura para llamar a v3 algo nuevo.

| Ciclo v2, 320 casos | DREAM | Fijo | Aleatorio | Sin Qwen |
|---|---:|---:|---:|---:|
| 1 | 245 | 180 | 206 | 245 |
| 2 | 245 | 210 | 230 | 245 |
| 3 | 240 | 200 | 238 | 240 |

Se exigían +32 frente al fijo y +16 frente al aleatorio **en cada ciclo**.
El primero pasa; los otros fallan frente al aleatorio (+15 y +2).
El agregado 730/960 no sustituye esa condición. El control sin Qwen empata:
no hay beneficio exclusivo demostrado del LLM. SELF activo alcanza 250 en
el tercer ciclo, frente a 240 de DREAM.

Nueve llamadas reales, 36 candidatos válidos, pesos intactos. Cero errores
de atribución y terminalidades, invariantes conservados. 891 pruebas:
890 aprobadas y un fallo esperado histórico. Auditoría válida sin hallazgos,
`dream1_green=false`. Digest:
`f5d36371c330c8d3ee439f3710391c744789a9026927b995aa1ae450fd4585ee`.
Las 76 fuentes congeladas y los artefactos vinculados de v1 quedaron intactos.

### 3. Hallazgo que debe guiar v3

En el segundo ciclo v2, el catálogo actual contiene cinco ensayos de ocho
pasos y uno de cuatro. Con presupuesto 12 y sin repeticiones caben seis
ensayos individuales o diez secuencias ordenadas de dos ensayos.

Se enumeraron esos 16 programas sobre datos ya abiertos:

- Mejor programa: 245/320.
- Unión de casos resueltos por cualquiera de los 16: 245/320, incluso con
  selección retrospectiva por la verdad privada.
- Umbral exigido frente al aleatorio: 246/320.

Es una cota posterior de ese catálogo, presupuesto y banco, NO una política
desplegable ni una prueba de imposibilidad general. Reordenar esas mismas
pruebas o cambiar el prompt no consigue el acierto que falta en ese banco.
La cota y su reproducción están en los resultados v2.

### 4. Primera tarea: desarrollo de observabilidad, antes de más inferencias

1. Reproduce la cota usando solo el historial abierto. Identifica las
   hipótesis propias/externas/mixtas que siguen compartiendo observaciones.
   Separa cuantización, falta de intervención y limitación de presupuesto.
2. Busca un catálogo acotado de secuencias alternativas de las tres acciones
   nativas que separen esas hipótesis. Empieza por horizontes cortos y el
   presupuesto 12; no des por hecho que hace falta ampliar sensores o WSP.
3. Comprueba seguridad de cada propuesta para **todas las hipótesis aún
   compatibles**, no solo para el cuerpo real que conoce el juez. Conserva
   gate, abstención, parada, cuotas y validación de recibos.
4. Mide en desarrollo cobertura y cota alcanzable con el catálogo propuesto.
   Compara un selector adaptativo basado en observaciones permitidas y una
   búsqueda sin LLM. No inicies un examen cuyo criterio ya resulte imposible
   en el diseño de desarrollo; documenta el problema sin tocar verdes antiguos.

No se prescribe una secuencia ganadora en este recordatorio: hay que medirla.
V1 y v2 ya abiertas son desarrollo, nunca confirmación independiente de v3.

### 5. Implementación versionada e integración cortical

- Importa/reutiliza física, predicción, gate y mecanismos originales.
  No edites el `CATALOG` global sellado ni hagas monkeypatch de producción
  sobre SELF para habilitar el catálogo nuevo.
- Inspecciona las restricciones de longitud, índices y tipos de planes,
  recibos, intérprete y archivo antes de extenderlos. Implementa un perfil
  v3 separado y explícito donde sea necesario; no clones el núcleo ni
  invalides certificados existentes.
- Si hace falta cambiar horizonte, presupuesto o esquema, justifícalo en
  un contrato nuevo antes del examen. No atribuyas más recursos a mejor
  algoritmo. Todos los brazos comparables deben tener el mismo catálogo,
  información permitida y límites; conserva además el control legado.
- Qwen sigue proponiendo programas declarativos de pesos fijos, sin Python
  arbitrario, shell, causas privadas, checkpoints o resultados futuros.
- Conserva experiencia → archivo → propuesta → replay → selección congelada
  → examen nuevo → promoción/reversión → ampliación del historial.
- Para cada rama nueva del catálogo, primero recoge ejecución real con
  procedencia. Una rama ausente en replay devuelve desconocido, no una
  predicción etiquetada como observación exacta.

### 6. Protocolo, controles y cierre

Fija tareas, particiones nuevas, semillas, métricas, márgenes, costes y
repeticiones **antes** de abrir el examen. Conserva la exigencia de ventaja
por ciclo de DREAM; no la sustituyas por un agregado favorable ni reduzcas
el umbral para acomodar v2. Un cambio sustancial de pregunta debe explicarse
y acordarse, no presentarse como cumplimiento del criterio anterior.

Incluye fijo, aleatorio, incumbente, selector sin Qwen, selector adaptativo
y ablaciones de historial/feedback/replay. Equilibra los presupuestos de
propuesta cuando se quiera atribuir un efecto causal al feedback o al LLM;
v2 mezclaba cuatro frente a ocho candidatos en algunas ablaciones.

Añade pruebas de límites, evidencia ausente/corrupta, recibos incompatibles,
veto, parada, rechazo de propuestas inseguras, selección sin fuga de futuro,
reversión y manipulación de informes. Mantén las regresiones basales.

Publica costes reales: colección, calibración, pasos online, consultas de
replay, llamadas/tokens/tiempo Qwen. Un stub no acredita el modelo local.
Solo una auditoría reconstructiva de los artefactos en proceso nuevo puede
conceder el verde dentro del contrato; pruebas unitarias no bastan. Si no
cumple, conserva el rojo y explica qué falló. Un empate sin Qwen no acredita
ventaja exclusiva del modelo; un verde funcional no acredita conciencia.

### 7. Herramientas y límites de alcance

Usa Python del sistema. No editar, arrancar, importar ni reutilizar nada
de `echo-discord`: proyecto legado archivado y congelado.

Modelo y servidor utilizados en v2; comprobar existencia/identidad antes
de arrancar y solicitar permisos de loopback si el entorno los requiere:

```text
/home/roger/models/qwen3-4b-instruct-2507/Qwen_Qwen3-4B-Instruct-2507-Q4_K_M.gguf
/home/roger/src/llama.cpp/build/bin/llama-server
```

El GGUF tiene SHA-256
`2fde00ce69dd4899c70d020845e2638353015bba0fdf161b3eb965f2bca4464e`.
V2 usó CPU, cuatro hilos y hasta nueve llamadas; tardó unos 15 minutos de
peticiones acumuladas. No reinferir v2 para verificarla: auditar sus recibos.
No descargar ni entrenar pesos por defecto.

Desde `echoai/`, comprobaciones útiles al retomar:

```bash
git status --short
PYTHONPATH=.. python3 -m unittest echoai.tests.test_echo4_dream1 echoai.tests.test_echo4_dream1_v2 -q
PYTHONPATH=.. python3 -m echoai.echo4.dream_v2_bench verify lab/echo4/dream1-d-v2
```

No añadir `--write-receipt` sobre un recibo que ya existe. Las campañas
nuevas usan directorios nuevos; ninguna sobrescribe `dream1-bcd-v1` ni
`dream1-d-v2`. Mantén WSP16, CAM sin destrucción, camino rápido entero,
firewall epistémico y NEXUS-0 con córtex OFF. No hay Akida en el laboratorio.

No abrir MAINTAIN ni otras fases como sustituto de este trabajo. No tocar
hardware, kernel, ISO, METAVERSE-1 ni la web. No publicar en Hugging Face,
hacer commit/push o desplegar sin nueva petición. Hardware irá después;
METAVERSE-1 permanece último.

### 8. Entrega esperada

Contrato v3, perfil implementado con pruebas, evidencia nueva no sobrescrita,
auditoría reproducible, análisis de controles y costes, y documentación del
resultado real en README, ROADMAP, NOW, STATUS y programa ECHO-4. Distingue
siempre implementación terminada de cierre científico. Empieza por la tarea
de observabilidad del apartado 4 y comunica sus resultados antes de lanzar
la campaña cortical nueva.
