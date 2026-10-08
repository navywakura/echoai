# DREAM-B/C/D — implementación y primera campaña real

2026-09-22. **Implementación completada; DREAM-D v1 rojo, DREAM-1 abierto.**
Qwen propone estrategias válidas y la selección mejora el historial, pero
no supera los controles fuera de muestra. Se conserva este resultado; no
se reajustan umbrales, políticas ni particiones después del examen.

## Entregables

- `echo4/dream_qwen.py`: adaptador llama.cpp local opt-in, pesos fijos,
  identidad de modelo/binario, gramática JSON, límites y recibos reales.
- `echo4/dream_policy.py`: validación estricta e intérprete de programas
  declarativos; selección con incumbente, parada y reversión por regresión.
- `echo4/dream_probe.py`: historial de seis ensayos SELF nativos restaurados
  y replay con revelación parcial. Rama ausente significa desconocido.
- `echo4/dream_bench.py`: campaña de tres ciclos, siete brazos, historial
  creciente, selección congelada antes del examen, versiones y auditoría.
- `tests/test_echo4_dream1.py`: 30 pruebas nuevas de límites, rechazos,
  causalidad del replay, presupuestos, reversión y detección de adulteración.

Ninguna modificación del núcleo, WSP16, CAM/T/Q/gate, física o criterios SELF.
Los ensayos utilizan el modelo diagnóstico y prior SELF existentes, no un
modelo corporal inventado por Qwen. El banco restaura/calibra el cuerpo;
eso no es reparación autónoma. No se toca ni reutiliza Discord.

## Protocolo y resultados

El [contrato](ECHO4-DREAM1-BCD-DESIGN.md) y sus fuentes se congelaron antes
del examen. Hasta 12 pasos diagnósticos por caso; cuatro propuestas por
llamada. Tres ciclos con 80 casos nuevos por ciclo. Historia disponible
antes de cada selección: 80, 160 y 240 contextos. Solo después de evaluar
se recogen las ramas del nuevo contexto para el siguiente ciclo.

Las celdas indican **aciertos / pasos de entorno**, sobre 80 casos por ciclo.

| Brazo | Ciclo 1 | Ciclo 2 | Ciclo 3 | Total aciertos / 240 |
|---|---:|---:|---:|---:|
| DREAM (Qwen + replay) | 40 / 640 | 40 / 640 | 50 / 640 | 130 |
| Incumbente | 40 / 960 | 40 / 640 | 50 / 640 | 130 |
| Orden fijo | 40 / 960 | 40 / 960 | 70 / 960 | 150 |
| Orden aleatorio | 41 / 856 | 42 / 848 | 72 / 752 | 155 |
| Qwen sin historial | 0 / 640 | 0 / 640 | 0 / 640 | 0 |
| Replay sin Qwen, seis rotaciones | 40 / 768 | 50 / 784 | 75 / 732 | 165 |
| SELF activo existente | 40 / 800 | 40 / 800 | 70 / 672 | 150 |

Los siete brazos tienen **cero atribuciones erróneas, cero terminalidades e
invariantes conservados**. Todo lo no resuelto es `unknown`, no un error
convertido artificialmente en acierto. La paridad online/replay es exacta
en todos los brazos y ciclos bajo el perfil de restauración declarado.

Para verde se exigían por ciclo +8 aciertos frente a fijo y +4 frente a
aleatorio. **Ningún ciclo pasa esas dos condiciones.** DREAM ahorra un
tercio de pasos respecto al fijo (1.920 frente a 2.880), pero obtiene veinte
aciertos menos en total. No acredita mayor eficiencia a igual rendimiento
ni ahorro total de CPU: hay además inferencia, calibración y recolección.

## Qué funcionó y por qué no basta

1. **DREAM-B, inferencia real:** seis llamadas generan 24 candidatos válidos;
   no se usó un stub para la campaña. Qwen no cambia pesos ni ejecuta código.
2. **DREAM-C, mejora histórica:** la primera selección pasa de 60/80 con
   960 pasos a 80/80 con 640. Elige orden `[5,3,1,0,2,4]`, presupuesto 8.
   En los ciclos siguientes conserva esa política; ninguna nueva propuesta
   de Qwen supera su puntuación histórica.
3. **DREAM-D, transferencia insuficiente:** esa estrategia resuelve menos
   casos nuevos que controles simples. En la tercera ronda pierde 20 frente
   al fijo y 25 frente al selector sin Qwen. No hay beneficio específico
   demostrado del LLM ni una secuencia de mejoras sostenidas entre ciclos.
4. **Reversión:** la primera política se acepta por empatar aciertos con el
   incumbente usando menos pasos; después se conserva. Nunca empeora frente
   a ese incumbente, pero sí termina peor que el control fijo original.
   Por tanto, comparar solo con el incumbente no garantiza conservar la
   ventaja frente a todos los controles bajo cambios de distribución.

Lectura técnica: el presupuesto elegido permite un solo ensayo de ocho
pasos. La resolución histórica favorece ese ensayo, pero no toda la nueva
distribución corporal se identifica con él. El control de rotaciones llega
a 165/240 con el mismo catálogo, así que no se puede atribuir todo el déficit
a un límite inevitable del sensor. Hay margen de propuesta/selección sin
necesidad de cambiar WSP o núcleo. Esta es una interpretación del resultado,
no una prueba de cuál será la mejor corrección.

La ablación sin historial toma la primera propuesta válida sin seleccionarla
por replay; cambia ambas cosas. Sirve de control del conjunto historia +
selección, no aísla por sí sola el efecto causal del texto histórico en Qwen.
El control sin Qwen explora seis rotaciones frente a un máximo de cuatro
candidatos generados por llamada: no iguala todo el coste computacional.

## Costes e identidad

- Modelo: Qwen3-4B-Instruct-2507 Q4_K_M, 2.497.280.736 bytes.
- SHA-256 GGUF: `2fde00ce69dd4899c70d020845e2638353015bba0fdf161b3eb965f2bca4464e`.
- llama.cpp: `0.3.0-dev`, commit `d230ddd`, GNU 15.2.1, Linux x86_64.
- CPU, cuatro hilos, cero capas GPU, contexto 8192, temperatura 0,
  seed `260922 + ciclo` (índice 0..2), máximo 512 tokens por llamada.
- Seis llamadas: 2.570 tokens de entrada, 1.588 generados;
  349.381 ms acumulados de petición/respuesta, más 6.078 ms de arranque.
- Historia inicial: 80 contextos, 3.520 pasos de recolección y 288 nominales.
- Cada ampliación: otros 80 contextos, 3.520 pasos y 288 nominales.
  Total colección + calibración: 14.080 + 1.152 pasos.
- Los siete brazos online suman 15.972 pasos; se reutiliza su calibración
  dentro de cada ciclo. No se presentan como coste exclusivo de DREAM.
- Replay para resúmenes/selección: 9.744 consultas, 67.376 pasos representados,
  cero pasos físicos nuevos y cero llamadas LLM durante esas consultas.

Estos contadores no incluyen las reproducciones de auditoría ni regresiones.
Son un vector de recursos, no una conversión entre tokens, pasos y energía.
No se midió consumo energético. El servidor propio se cerró al terminar.

## Evidencia y reproducción

Directorio: [lab/echo4/dream1-bcd-v1](../lab/echo4/dream1-bcd-v1).
Incluye lock de fuentes/modelo/particiones, peticiones y respuestas, ramas
observadas, selecciones, trazas online, versiones, informe y recibo final.

- [Informe](../lab/echo4/dream1-bcd-v1/report.json): `criteria_passed=false`.
- [Auditoría](../lab/echo4/dream1-bcd-v1/audit-receipt.json): `valid=true`,
  cero hallazgos, **`dream1_green=false`**.
- Digest de reproducción:
  `5feb033f72d84a673eca26af2ec9145d267d7781073dfed80817fbdfbecdba27`.

La auditoría reconstruye historias y ensayos desde física original, repite
selección y versiones, coteja las fuentes y el vínculo CONT-D, y audita los
recibos Qwen. No repite la inferencia: tokens/tiempos son mediciones guardadas,
no salidas deterministas del verificador. Los hashes dan integridad local,
no una atestación externa de ejecución ni una firma de terceros.

**Verificación de código:** 871 pruebas distintas, 870 aprobadas y un fallo
esperado histórico. Son 30 nuevas DREAM-B/C/D, 583 de DREAM-A/SELF-B/CONT-A/
NEXUS-0/Q y 258 de CONT-B/C/D, SELF final, WORLD, SENSATION y BOUNDARY.
Ocho errores iniciales de sockets GUI debidos al sandbox se resolvieron
repitiendo con permiso las 29 pruebas GUI: todas pasan, sin cambios de código
y sin contarlas dos veces. Las 72 fuentes selladas y el vínculo CONT-D se
comprobaron de nuevo después de actualizar la documentación.
`git diff --check` pasa. No se afirma haber ejecutado toda la suite histórica del repo.

```bash
PYTHONPATH=.. python3 -m unittest echoai.tests.test_echo4_dream1 -q
PYTHONPATH=.. python3 -m echoai.echo4.dream_bench verify lab/echo4/dream1-bcd-v1
```

## Próximo trabajo: DREAM-D v2

La implementación del bucle está disponible. Para cerrar científicamente:

1. Utilizar v1 como desarrollo, conservar su rojo y estudiar cobertura por
   cuerpo/ensayo, diversidad de propuestas y elecciones de presupuesto.
2. Probar selección más robusta y feedback del replay a propuestas posteriores;
   separar la aportación de Qwen de una búsqueda determinista equiparada.
3. Comparar también contra el control fijo original antes de promocionar;
   no interpretar retener incumbente como garantía de mejora general.
4. Fijar contrato v2 y nuevos casos antes de abrir un examen independiente.
   No rebajar el umbral ni reutilizar los casos v1 como confirmación.

No se acredita conciencia subjetiva, mejora de pesos, reparación autónoma
ni integración del agente completo. MAINTAIN sigue pendiente en la rama
basal; después siguen OTHER, INTERACTION, RELATION, ROLES, INTEGRATE y RELEASE.
Hardware posterior; METAVERSE-1 permanece último. Sin publicación web,
commit, push, descarga de pesos ni despliegue en esta entrega.
