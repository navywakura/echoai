# FLIGHT-1S v4 — separación del control y recuperación física

Estado inicial: protocolo prospectivo, sin vuelos v4. Autorizado por Nav al
pedir continuar tras el diagnóstico v3. Los resultados v1–v3 se conservan.

## Pregunta y cambio de alcance

¿Este X500/PX4 simulado distingue una perturbación aplicada de la deriva
nominal y recupera estabilidad? V4 **no certifica precisión nominal ≤250 mm
en cada vuelo**. Sustituye esa exigencia de v2 por contraste emparejado entre
condiciones. Es una relajación de aquella garantía de precisión, explícita,
y una pregunta de aceptación distinta; no convierte retrospectivamente v2
en verde. No se modifican sensores, fuerza, PID ni criterios tras los vuelos.

Los datos v3 son desarrollo, incluidas todas las campañas fallidas. No se usa
la validación verde aislada como autorización. Las observaciones apoyan una
limitación de estimación de esta configuración, pero no prueban un límite
universal del GNSS ni que ningún estimador pueda mejorarla. Las muestras de
pose están correlacionadas: no equivalen a cientos de ensayos independientes.
La probabilidad calculada a partir de 1 fallo entre 68 tampoco es una tasa
poblacional conocida. Ausencia de solape histórica no garantiza separación
en nuevos vuelos.

## Configuración única y muestra fijada antes de ejecutar

- Stock `echoai-flight1s-px4:v1.15.4`, fijado por ID de imagen; sin parche eph.
- Único candidato: `noaid_7n` de v3. GPS_DELAY=0, P=3, D=0.4, I=0,
  EKF2_NOAID_NOISE=0.5; fuerza 7 N durante 600 ms, exactamente una publicación.
- A: 4 mundos, 8 pares por mundo, **64 vuelos nuevos + 4 controles sin fuerza**.
- Banco posterior sólo si A pasa: 12 mundos rehearsal, 2 pares por mundo,
  **48 vuelos nuevos + 3 mutantes físicos**. No es transferencia reservada.
- Dos contenedores aislados concurrentes. Permutación de condiciones fijada
  con semillas de orden 20260921 (A) y 20260922 (banco). Estas semillas no
  fijan las realizaciones GNSS ni la planificación temporal del host.
- Sin reintentos automáticos ni exclusión de fallos de infraestructura.
  Se ejecuta el denominador completo de cada etapa; un fallo impide el verde.
  Una etapa roja se conserva y no autoriza repetir hasta conseguir un pase.
- Código, diseño, protocolo, imagen, historia y plan se fijan antes de A.
  El mismo lock cubre A, banco y controles. Los ficheros son de una escritura.

## Criterios obligatorios

| Grupo | Criterio rojo, fijado antes de medir |
|---|---|
| Ejecución | Falta cualquier vuelo previsto o firma PX4/armado/modo/ULog |
| Estímulo | Cualquier perturbado incumple wrench única, retirada o 500–1500 ppk |
| Desafío | Cualquier perturbado no supera 250 mm; nominal ≤250 queda como diagnóstico histórico |
| Recuperación | Cualquier perturbado no permanece dentro de 200 mm durante 3 s continuos dentro de los 10 s posteriores al pulso |
| Seguridad observada | Colisión, regresión de reloj, actitud >25° en ventanas evaluadas, aterrizaje fuera de tolerancia histórica, o excursión horizontal >1000 mm desde posición inicial en cualquier muestra registrada |
| Separación | A: alguno de sus 4 promedios de diferencia por mundo ≤50 mm, o mediana de esos promedios <100 mm. Banco: menos de 10/12 promedios >50 mm, o mediana <100 mm |
| Repetición | Tolerancias v2: RMS horizontal entre primeras dos repeticiones >230 mm o recuperación >5000 ms; restantes repeticiones A se incluyen en todos los otros grupos |
| Controles | Sin fuerza parece estímulo válido, fuga de datos privados, red habilitada, hash de mundo no rechazado, o cualquier pareja nominal/perturbado invertida |
| Auditor | Hash, identidad, secuencia, configuración leída en ULog, aritmética independiente o grupo reconstruido discordante; mutante aceptado |

El nuevo límite físico de 1000 mm usa la columna libre de 1100 mm ya exigida
por el contrato del cuerpo y deja 100 mm de margen; se comprueba además la
geometría con la envolvente real. Se refiere a las muestras disponibles, no
garantiza ausencia de eventos entre ellas. No se amplía el radio de recuperación.
El impulso es cambio de momento estimado desde poses, incluye la reacción
del controlador: no se presenta como sensor independiente de fuerza.

## Contraste distribucional, unidad e incertidumbre

Por pareja: d = máximo radial perturbado − máximo radial nominal durante
pulso y recuperación, según aritmética v2. Por mundo: media de sus d.
El margen práctico de 50 mm procede del margen de medición v2; el efecto
mediano requerido de 100 mm es la mitad del radio de recuperación.
Se publican todos los d, medias por mundo, rangos de ambos brazos, solape,
nominales por encima de 250 mm y resultados del contrato antiguo.

Banco: contraste unilateral de signos frente a mediana de diferencia ≤50 mm,
con 12 bloques de mundo, no 24 parejas ni miles de poses independientes.
10/12 signos positivos dan p=79/4096=0.019287109375, inferior a α=0.025;
empates cuentan como no positivos. Se publica límite inferior exacto unilateral
95% para la proporción de bloques positivos. Su interpretación supone bloques
independientes con probabilidad común; estos mundos públicos y el host compartido
limitan extrapolación. A sólo es puerta de ingeniería, sin afirmación inferencial
con cuatro mundos. Cero fallos observados no significa tasa de fallo cero.

## Evidencia e implementación

`nexus0/flight1s_v4/` reutiliza sesión, evaluadores, runner y generador existentes.
Está fuera del inventario recursivo v3 para conservarlo también intacto.
No hay bus, IA, aprendizaje ni sensores privilegiados nuevos. WSP/Q/T/CAM y
kernel siguen intactos; cortex_calls=0, agent_in_gazebo=false.

El auditor recalcula A y banco desde trazas y hashes ULog; reconstruye grupos,
contraste, orden y denominadores, y diferencia evidencia válida de resultado
verde. Pruebas de adulteración con hash de informe recalculado incluyen cambio
de medida, omisión de vuelo, relajación del protocolo y verde inventado. Se
conservan también los logs de regresión y los mutantes físicos.

Sólo un banco nuevo completo y auditado podrá cerrar FLIGHT-1S **bajo v4**.
No acredita autonomía echoAI, precisión de navegación, vuelo real ni sim-to-real.
