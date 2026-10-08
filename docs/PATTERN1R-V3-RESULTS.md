# PATTERN-1R v3 — rojo auditable y defecto de etiquetado del juez

2026-09-14. **Aceptación roja, evidencia válida; fase todavía abierta.** Diseño y criterios:
[PATTERN1R-V3-DESIGN.md](PATTERN1R-V3-DESIGN.md).
La aceptación v2 queda [roja y auditable](PATTERN1R-V2-RESULTS.md).

## Desarrollo conservado

| Candidato | Vuelos | Resultado |
|---|---|---|
| `baro-covariance` | Seis nuevos, todos con 48/48 objetivos | 3/6 verdes; identidad roja en w0, w1 y w3 |
| Replay de abstención | Mismas seis trazas anteriores | Identidad verde en 6/6; diagnóstico, no confirmación |
| `baro-abstain` | Seis vuelos nuevos, semillas 20261531–20261536 | 5/6 verdes; identidad verde en 6/6; w5 falla tiempo causal y empujón |
| `baro-abstain-preinit` | Seis vuelos nuevos, semillas 20261541–20261546 | 6/6 verdes; misma configuración antes de arrancar EKF2 |

La primera corrección cambia únicamente la incertidumbre barométrica del
estimador, derivada del ruido declarado del sensor. El sensor físico simulado,
el PID y la geometría no cambian. El vuelo alcanza los objetivos, pero eso no
basta para distinguir familias entre vistas.

La segunda evita crear una familia nueva cuando el aprendizaje empata entre
dos familias compatibles dentro del radio. Deja esa observación sin asignar,
la contabiliza y conserva la memoria original de ECHO-2. La misma regla de
abstención ya existía en el examen. Se guarda el primer código y todos sus
resultados en `lab/pattern1r-v3/review/baro-covariance-code/` y `dev/`.

El ULog de `baro-abstain-w0` confirma `EKF2_BARO_NOISE=0.01` y `EKF2_HGT_REF=0`.
La z observada durante su recorrido abarca 0,948–2,043 m: llegar a 48 objetivos
con tolerancia de 500 mm no implica altura perfecta ni aerodinámica realista.
La verificación y el hash del ULog quedan en `review/`.

En `baro-abstain-w5`, el cuerpo seguía en suelo al iniciar el recorrido mientras
PX4 estimaba altitud global 2,287 m; el recorrido posterior sí alcanzó 48/48.
Ese fallo se conserva. La revisión de inicialización usa el hook oficial
`px4-rc.params` antes de EKF2, y MAVLink sólo verifica los valores después.
No se alteran cifras ni se reemplaza únicamente el vuelo fallido.

La tanda completa verde con el mismo candidato habilitó la aceptación de v3.
Se ejecutó A 8+2; el banco 12+6 permaneció cerrado por su rojo. Se completaron
la recomputación independiente y siete manipulaciones del informe.

Lock de aceptación vigente:
`7070588ab86e3ea40493e23d061e7910540cc1ae40145a852a32469692edd144`.
Cuatro suites previas: 62 pruebas correctas (11 v3, 22 v2 con su fixture aislada,
16 PATTERN-1R original y 13 DYNAMIC-1 v2). El primer preflight fallido se conserva
en `review/preflight-attempt1/`; no llegó a congelar ni lanzar vuelos.

Los ULog de los dos primeros vuelos `preinit` confirman los parámetros desde
su estado inicial. Durante sus recorridos la altura observada queda entre
1,460 y 1,537 m y se alcanzan 48/48 objetivos en ambos. La verificación se guarda
en `review/preinit-first-two-verification.json`; no se generaliza ese intervalo
a vuelos todavía no evaluados ni a un dron real.

## Alcance

Dos paredes de longitudes distintas, firmas anónimas de LiDAR y memoria de
familias evaluada por replay, con examen sin escrituras. El consumidor aislado
extrae firmas durante el vuelo y no recibe identidad, geometría ni recorrido.
El arnés prepara objetivos con geometría privada y PX4 los ejecuta. La política
de echoAI todavía no decide el vuelo. No acredita objetos semánticos generales,
transferencia a salas reservadas, manipulación, hardware ni Akida.

## Resultado final v3

`lab/echo3_pattern1r_v3_report.json`, SHA-256
`bb70829b199c20368f6638828ef551ce0bc8059564158c31f9141cbfc38c928d`.
A: 8 vuelos + 2 controles, completos y sin reinicios. Los ocho recorridos
alcanzan 48/48. **89 comprobaciones, 0 hallazgos, evidencia válida**; 7/7
manipulaciones del informe detectadas. Banco no abierto.

Falla sólo identidad en `clean-e1c8883e1f8ca3b2`: acierto 177/449 (39,42%),
231 confusiones (51,45%), 41 desconocidos; ambos objetos reciben el mismo nombre
de familia del juez. Los demás grupos, incluidos vuelo y respuesta causal,
permanecen verdes. Este resultado y su criterio original no se cambian.

El diagnóstico posterior encuentra un defecto en el juez: usa asignaciones
hechas durante el aprendizaje para nombrar familias que después han cambiado.
El modelo final tiene P0 de 9 bits y P2 de 13. Pasando sólo la escuela por ese
modelo congelado, los objetos reciben P0 y P2; con ese mapa escolar el mismo
examen obtiene 408/449, 41 desconocidos y ninguna confusión, sin cambiar memoria.
Es diagnóstico posterior; **no convierte v3 en verde**.

La corrección y un nuevo examen prospectivo se declaran en
[PATTERN1R-V4-DESIGN.md](PATTERN1R-V4-DESIGN.md). El diagnóstico queda en
`lab/pattern1r-followup/v3-family-diagnosis.json`; los vuelos nuevos son de v4.
