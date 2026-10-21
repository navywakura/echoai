# TRANSFER-3 — requisitos del examen final, propuesta para revisión

2026-09-18. **Borrador no congelado; no autoriza generar una campaña.**
No hay candidato que haya superado el cribado v4. Este documento no sustituye
el contrato de ECHO-3 ni declara cerrados los puntos 2–4 solicitados por Nav.

## Dependencias de cierre

1. Candidato cuya ventaja tenga soporte en desarrollo con control competente
   y costes publicados. V4 no proporciona ese candidato.
2. Revisión del generador, representación y protocolo. Fijar después hashes,
   N y criterios; no elegirlos retrospectivamente para aprobar v4.
3. Integración del examinador real con compromisos, snapshot, inventario,
   apertura única, reconstrucción de trazas y auditoría adversarial.
4. Custodia externa y ejecución real A→B→C. No ejecutar este paso aquí.

## Tamaño de muestra y capacidad geométrica

La familia v2 tiene **450 combinaciones de parámetros pero sólo 126 formas**
distintas tras normalizar traslación/reflexión/rotación. Enumeración: ancho
5..9, semialtura 3..5, pared interior 1..ancho−2 y abertura distinta de cero
en −semialtura+1..semialtura−1. Ignorar nombres, semillas, salida y meta.
Tras v4 ya se usaron públicamente 84 geometrías distintas; quedan **42**.

No caben B=64 y C=64 independientes de ese desarrollo. No se debe contar
varias semillas con la misma sala como geometrías nuevas ni reducir N sólo
para poder sellar algo. Hace falta ampliar y probar el generador y verificar
su correspondencia con el dominio físico que se vaya a reivindicar. Un cambio
de tamaños/topología requiere desarrollo público antes de ser examen final.

Como cálculo prospectivo **hipotético**, no estimación demostrada: si el 30 %
de pares es discordante y el candidato gana el 70 % de esos pares, la prueba
de signo unilateral exacta con α=0,025 tiene esta potencia aproximada:

| N por partición | Potencia |
|---:|---:|
| 32 | 0,142 |
| 64 | 0,340 |
| 128 | 0,656 |
| 256 | 0,935 |

Se obtiene sumando, para n discordantes, Binomial(N,0,3)[n] por la probabilidad
Binomial(n,0,7) de alcanzar el umbral exacto bajo p=0,5. Supone pares iid;
el muestreo sin reemplazo y el diseño real pueden requerir otro cálculo.
Esta potencia es sólo la de la prueba de signo: no incluye la probabilidad
de superar conjuntamente los criterios de seguridad y regresiones.
**N=256 no queda aprobado**: ilustra que un efecto moderado con muchos
empates exige más casos que los 16 anteriores. No se fijará potencia a partir
de una ventaja seleccionada ni se multiplicarán semillas para fingir réplicas.

## Contrato estadístico y de costes a cerrar

- Un candidato principal, regla y snapshot congelados antes de B. Si se
  eligen múltiples candidatos, corregir multiplicidad y declarar la selección.
- Control scratch con misma cinemática, sensores, planner, presupuesto, gate
  y condiciones. Manipular sólo los parámetros aprendidos permitidos.
- Priorizar metas; movimientos comparables sólo entre llegadas conjuntas.
  Fallos conjuntos no son eficiencia. Publicar tabla completa por mundo.
- Definir por adelantado qué constituye una regresión de llegada y cómo
  se evalúa no inferioridad/ventaja. V4 usa cero fallos nuevos como cribado
  conservador; no cambiar esa regla para hacer verde el resultado ya visto.
- Publicar escuela + examen y unidades simuladas; no asumir amortización
  ni convertir movimientos en julios físicos. Comparar costes de candidatos
  a igual presupuesto medido, no sólo igual número de episodios.
- Restricciones duras del contrato: evidencia falsa, fugas oracle, escrituras
  imaginadas, bypass del gate/failsafe. Un banco funcional no prueba por sí
  solo PX4, HIL ni hardware. Fijar explícitamente el alcance final y sus datos.

## Integración y custodia que aún deben implementarse/verificarse

Lo actual (`transfer3/custody.py`) valida compromisos y ensaya una apertura
única, pero **no conecta una campaña real al banco**. Para cerrar esa conexión:

1. Publicar protocolo, código, dependencias, generador y criterios; el custodio
   genera secreto/salts y paquetes fuera del acceso de ambos agentes.
2. Comprometer B/C y ledger antes de aprender A. Registrar publicación externa,
   fecha y responsable. Un fichero editable en este repo no acredita custodia.
3. Entrenar A y congelar sólo el payload permitido, con trazas reconstruibles
   y hashes. Limpiar estado episódico antes de cada examen.
4. Antes de abrir, verificar freeze e inventarios. El consumidor debe ver sólo
   la interfaz aprobada. Leer paquetes privados sólo después de la transición
   persistida; verificar sus bytes contra compromisos, no sólo los metadatos.
5. Abrir B una vez. Si falla evidencia o criterio científico, no abrir C.
   Auditar B reconstruyendo trazas, no confiando en un booleano `green`.
6. Abrir C bajo exactamente el mismo freeze. Un crash consume independencia;
   un retry es reproducción rotulada. Bloquear concurrencia y sobrescrituras.
7. Publicar todas las corridas, fallos y revelaciones. Recomputar evaluación
   y certificados en otro proceso; ninguna marca `ready` manual sustituye esto.

Mutantes obligatorios: snapshot cambiado, Q dependiente de coordenadas,
paquete/salt/commitment alterados, fuga de seed, doble apertura/concurrencia,
crash, B rojo con intento de C, informe falsificado, caso omitido y escritura
de aprendizaje durante examen.

No pedir aún secretos a Nav ni usar a Claude como custodio mientras tenga
acceso al desarrollo. La revisión independiente sí puede hacerse ahora.
