# PATTERN-1R v4 — resultados del 14 de septiembre de 2026

**Estado: VERDE en su alcance software/SITL.** `pattern1r_green=true`,
`evidence_valid=true`: 28 vuelos, 242 comprobaciones sin hallazgos, seis mutantes
y siete manipulaciones del informe detectados. Contrato: [PATTERN1R-V4-DESIGN.md](PATTERN1R-V4-DESIGN.md).
Los rojos [v1](PATTERN1R-RESULTS.md), [v2](PATTERN1R-V2-RESULTS.md) y
[v3](PATTERN1R-V3-RESULTS.md), su código y sus vuelos se conservan.

## Qué se corrigió

La revisión encontró firmas desalineadas con las observaciones del juez,
fragmentos LiDAR mal agrupados y un recorrido incompatible con la envolvente
de 400 mm del cuerpo. V2 corrigió esas interfaces, la asociación de haces,
el recorrido, el envío de altura y varios controles del banco. Sus vuelos
posteriores descubrieron deriva vertical; su aceptación quedó roja.

V3 corrigió la covarianza barométrica y aplicó los parámetros antes de arrancar
EKF2. Añadió una memoria opt-in que se abstiene ante empates dentro del radio
de coincidencia, evitando crear familias duplicadas. No cambia la memoria
original de ECHO-2. Su vuelo y aprendizaje pasaron, pero el juez confundió
asignaciones escolares intermedias con las familias del modelo final.

V4 corrige únicamente ese etiquetado: el juez nombra las familias del modelo
final usando sólo observaciones escolares, después del aprendizaje y antes
del examen. Las etiquetas privadas nunca entran al aprendiz. Percepción,
memoria, ruido, sensores, parámetros y vuelo son idénticos a v3, comprobado por
igualdad de archivos y configuración. No cambia ningún umbral de aceptación.
Cambiar cómo se evalúa un modelo no es por sí mismo una mejora de inteligencia.

Las pruebas reproducen el falso colapso de v3, impiden elegir etiquetas con el
examen y siguen rechazando colapso real y escrituras. La calibración escolar
y el examen deben conservar la memoria congelada.

## Cadena ejecutada

Seis vuelos nuevos de desarrollo `final-school-map`, semillas 20261621–20261626,
pasaron íntegramente con el candidato fijo. Después se congeló la aceptación:
A (20261611) abrió el banco (20261612) sólo tras pasar una auditoría independiente.
No se reemplazaron vuelos fallidos ni se modificó el candidato después del lock.
Antes de volar pasaron cinco suites: **66 pruebas correctas**.

| Evidencia | A | Banco |
|---|---:|---:|
| Vuelos principales | 8 | 12 |
| Controles estáticos / mutantes | 2 controles | 6 mutantes |
| Ejecuciones completas | 10/10 | 18/18 |
| Reinicios de arranque | 0 | 0 |
| Grupos aprobados | 29/29 | 29/29 |
| Objetivos alcanzados, vuelos principales | 384/384 | 576/576 |
| Frames del cable, incluidos controles/mutantes | 308.918 | 635.606 |
| Tiempo de etapa, sin regresiones ni auditorías posteriores | 770,02 s | 1.550,30 s |

## Reconocimiento medido

| Métrica de examen | A | Banco |
|---|---:|---:|
| Aciertos / observaciones | 2.939/3.169 (92,74 %) | 4.591/4.866 (94,35 %) |
| Confusiones | 54 (1,70 %) | 45 (0,92 %) |
| Desconocidos | 176 | 230 |
| Menor acierto por vuelo | 90,91 % | 91,35 % |
| Mayor confusión por vuelo | 9,09 % | 6,58 % |

El contrato exige acierto ≥75 %, confusión ≤15 %, dos familias separadas,
pureza escolar ≥60 % y cobertura suficiente de cada objeto. Los desconocidos
permanecen en el denominador. Las observaciones de un vuelo están correlacionadas:
estos porcentajes describen el banco, no miles de experimentos independientes.

Los seis mutantes volaron sanos y fallaron su caso previsto; el procesamiento
honesto de sus mismos datos pasó el grupo correspondiente:

| Mutante | Fallo comprobado |
|---|---|
| `constant_family` | Colapso de objetos en una familia |
| `range_leak` | Identidad que depende de distancia |
| `beam_index` | Identidad que depende del índice del haz |
| `replay` | Firma que no corresponde a las muestras actuales |
| `frozen_write` | Escritura durante el examen congelado |
| `extra_channel` | Canal adicional fuera del contrato |

## Auditoría

A fue recalculada de forma independiente antes de abrir el banco: **89
comprobaciones, diez episodios, cero hallazgos**. El cierre recalculó los 18
episodios del banco: 153 comprobaciones y cero hallazgos. Reutilizó el cálculo
independiente de los diez de A tras verificar otra vez sus archivos. En total,
los 28 episodios fueron recalculados por el auditor al menos una vez. Las siete
manipulaciones se rechazaron: omitir registro, falso verde, alterar grupo,
falsear conteo, firma o cable y declarar al agente activo.

Certificado final: `95acf440a16c269610bfd97b19321383effd094d06effb1df2556f66afac2df9`.
No hay errores de etapa ni hallazgos pendientes.

El primer cálculo del auditor no reutiliza las evaluaciones declaradas por
el banco. La caché posterior es local al proceso y sólo admite resultados
recalculados por el auditor; exige verificar otra vez archivos e inventario
y la clave completa de registro, protocolo y mundo. Una auditoría en proceso
nuevo comienza sin esa caché.

## Alcance y límites

Familias anónimas de LiDAR para **dos paredes de distinta longitud**, examinadas
en vistas posteriores del mismo vuelo. La extracción de firmas ocurre en un
consumidor aislado durante la simulación; el aprendizaje y examen de familias
se realizan por replay. El arnés conoce la geometría para preparar objetivos;
el aprendiz no recibe mapa, identidad ni recorrido. PX4 ejecuta el vuelo;
la política de echoAI todavía no lo decide.

Los doce mundos son rehearsal y sus geometrías ya estaban disponibles durante
el desarrollo. Las nuevas semillas no los convierten en C reservado. Este cierre
no acredita reconocimiento semántico general, seguimiento general con oclusiones
y movimiento propio, navegación autónoma integrada, transferencia conductual,
manipulación, hardware ni Akida. Tampoco sustituye las fases FUSION-1 o PX4-1.

## Huellas y reproducción

| Artefacto | SHA-256 canónico |
|---|---|
| Certificado final | `95acf440a16c269610bfd97b19321383effd094d06effb1df2556f66afac2df9` |
| Lock | `06ee88bdbc75eae99621fc4cb9896809bef05ea2255c82261adc3f7a341f0aec` |
| Desarrollo | `09f1566821bb6d7691f803aeed5e6e63a7dc1ea9fa4eef56ff229cbb99c949db` |
| A | `9cabd8cd0ae78e9be8336c868fe96d03f7df402ecf69316de307b26423579a5f` |
| Banco | `4c82592724003d86b3dc4feaa622567930b327cb0bbafb4a89f8bfb5ccab4036` |

Desde `echoai/`, para auditar los vuelos guardados sin repetirlos:

```bash
PYTHONPATH=.. python3 -m echoai.nexus0.pattern1r_v4.campaign audit
```

La cadena iniciada con `campaign start` es inmutable. Sus muestras privadas,
transcripts, ULog, protocolo, inventarios y lock en `lab/pattern1r-v4/` son parte
de la evidencia. El certificado se publica en `lab/echo3_pattern1r_v4_report.json`.
