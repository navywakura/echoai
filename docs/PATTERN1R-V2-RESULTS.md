# PATTERN-1R v2 — desarrollo y resultados conservados

Fecha: 2026-09-14. **Aceptación ROJA, evidencia válida; fase abierta.**
Diseño: [PATTERN1R-V2-DESIGN.md](PATTERN1R-V2-DESIGN.md).
DYNAMIC-1 v2 se cerró primero y permanece inalterado.

## Qué se ha corregido

- Correspondencia entre una firma emitida y los haces que la produjeron:
  omitir un fragmento ya no desplaza las etiquetas de todo el vuelo.
- Segmentación circular sin duplicar haces, y una asignación por pista.
- Recorrido que respeta la envolvente del X500: el arco anterior invadía su
  margen en los doce mundos; el rectángulo tiene separación nominal de 1.200 mm.
- Confusión agregada, controles sin recorrido, cobertura por objeto y examen
  de mutantes. Un colapso a una sola familia no puede acreditar identidad.
- Referencia de altitud DO_REPOSITION y configuración tipada del estimador.

## Tandas de desarrollo

| Tanda | Resultado | Interpretación |
|---|---|---|
| `development` | 4/6 mundos verdes | w1: confusión 18,67%; w5: 38/48 objetivos, pérdida de altura. Conservada completa |
| `maturity32-baro` | 0/6, sin frames ni despegues | Error de lista de parámetros del driver; no prueba la hipótesis |
| `maturity32-baro-driver` | 0/6, sin despegues | PX4 rechaza el tipo REAL32 de `EKF2_HGT_REF`; no prueba reconocimiento |
| `maturity32-baro-int` | 6/6 mundos verdes | Seis vuelos nuevos completos, semillas 20261441–20261446; habilita congelación de A, no cierre |

El único presupuesto de madurez alternativo ensayado es 32 frente a 4.
Un replay sobre los seis vuelos iniciales reduce la confusión (peor 13,90%)
sin alcanzar aún confirmación independiente. No se reemplazan esos resultados
iniciales por el replay. Las revisiones y snapshots de código están en
`lab/pattern1r-v2/review/`; planes, logs y evaluaciones permanecen en el mismo
namespace y bajo `dev/`.

El ULog de `maturity32-baro-int-w1` confirma el cambio de `EKF2_HGT_REF` de 1
a 0, coherente con la lectura MAVLink. Se guarda esa verificación en `review/`.
En w0 sólo se alcanzan 44/48 objetivos por deriva vertical: cumple el mínimo
prerregistrado del 90%, pero se conserva como limitación del candidato.
No se cambia ese umbral ni se seleccionan únicamente los vuelos con 48/48.

## Qué significa un eventual cierre

Firmas anónimas de LiDAR y memoria congelada capaces de distinguir dos paredes
de distinta longitud en vistas posteriores del mismo vuelo. Las firmas se
extraen durante la simulación; el aprendizaje y examen de familias se ejecutan
por replay en el evaluador. El consumidor no recibe geometría, identidad ni
recorrido. El arnés sí conoce la geometría para mandar los objetivos a PX4.

No acredita navegación elegida por echoAI, identidad semántica de cualquier
objeto, transferencia A→B/C, manipulación, compensación general del movimiento
propio, vuelo físico ni hardware Akida. Los mundos son rehearsal; otras semillas
no los convierten en un conjunto reservado.

La aceptación se abrió tras seis mundos de desarrollo verdes con
el mismo candidato. Cadena: lock, regresiones, A 8+2 controles, banco
12+6 mutantes, auditoría por recomputación y siete manipulaciones del informe.
Un fallo se conserva y mantiene la fase abierta.

## Resultado de aceptación v2

Lock `7f7d7342554f092b947a64db0c934064bc192b3000b18af7e888d6f8c2e6d2eb`.
Informe final `lab/echo3_pattern1r_v2_report.json`, SHA-256
`62c625e71935ab23fd6e7fed3772880a02dfbc8d99a545e15b604ed762450f7f`.

A completa: 8 vuelos + 2 controles, sin reinicios. Auditoría: **89 comprobaciones,
0 hallazgos, evidencia válida**; 7/7 manipulaciones del informe rechazadas.
Las tres suites previas suman 51 pruebas, todas correctas. El banco no se abrió.

Tres vuelos alcanzan sólo **33/48, 38/48 y 37/48** objetivos. El primero queda
sin observaciones de examen de uno de los objetos y registra movimientos bruscos
fuera de la ventana del empujón. Fallan `survey`, `identity` (cobertura) y `push`.
No se compensan con medias agregadas ni con los controles, que pasan su contrato
negativo. Se conservan también los vuelos que sí completaron el reconocimiento.

El ULog de `clean-11b2f9bdbbccf260` muestra pérdida de altura física con una
estimación global próxima al objetivo; el barómetro sí refleja el descenso.
La siguiente revisión [v3](PATTERN1R-V3-DESIGN.md) ajusta la incertidumbre de ese
sensor al ruido que declara su SDF, sin modificar v2 ni relajar la aceptación.
