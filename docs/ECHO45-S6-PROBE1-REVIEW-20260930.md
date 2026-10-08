# S6-PROBE1 — Revisión de ingeniería antes de medir

30 septiembre 2026. Codex revisa la entrega de Opus. B12-R1 continúa su
auditoría; **el sondeo todavía no ha jugado partidas**. Esta revisión modifica
solo código, pruebas y contrato del sondeo, antes de congelarlos.

## Decisiones sobre la entrega

| Propuesta de Opus | Decisión y condición |
|---|---|
| Replay de positivos y uno de cada diez candidatos | Aceptado como cribado, declarado distinto del verificador original. Negativos sin replay quedan `not_checked`. Un fallo de replay detiene todo y conserva evidencia. Auditoría independiente posterior pendiente. |
| Diarios efímeros para primeras mediciones | Aceptado. El worker guarda primero el resultado duradero en caché; después elimina únicamente su diario. Un error de ejecución conserva el diario. Base y replays se conservan. |
| Pares complementarios y pares con interacción | Aceptado como búsqueda limitada. Se conserva el orden canónico y el plan prefijado; no implica cobertura de todas las composiciones. |
| Diez procesos | Sustituido por cuatro antes de congelar. El determinismo no garantiza memoria suficiente ni ausencia de timeouts. `estimate` recogerá pico RSS de workers y tiempos reales. |

## Problemas corregidos

1. El inicio solo exigía la auditoría B12. Ahora exige también la auditoría
   independiente R1, cierre `CAMPAIGN_NO_PROMOTION`, fuentes y perfiles íntegros,
   hashes de la campaña y ausencia física de un examen abierto.
2. `play_one` ya rechazaba partidas protegidas. Ahora también se rechazan
   solicitudes B/examen antes de acceder a la caché de mediciones.
3. Las propuestas guardadas no se revalidaban al reanudar. Ahora se cotejan
   E0, `PLAN_SHA`, selección de pares y asociación entre plan y resultados.
4. Una discrepancia de replay antes solo excluía el candidato. Ahora detiene
   el sondeo e impide presentar un fallo del instrumento como conclusión
   negativa sobre capacidad.
5. Se retira la cota global «regla del 3, 95%»: cinco controles dirigidos y
   muestreo estratificado no justifican ese cálculo sin más. Se informan
   recuentos y éxitos por estrato.
6. La documentación indicaba el Python del sistema. Se corrige al Python 3.12
   del entorno ARC congelado de B12; otro runtime no pasa la integridad.
7. Un bloqueo exclusivo evita dos comandos simultáneos. La cola `wait-estimate`
   detecta cambios de fuentes y solo ejecuta la calibración cuando B12-R1 cierra
   válidamente; termina después de base y cinco candidatos. No lanza `run`.

## Alcance de la comprobación

Se añaden pruebas de procedencia, rechazo de acceso protegido, arranque de un
worker con `spawn` sin jugar, persistencia antes de borrar diarios, conservación
de errores, rechazo de rutas externas, discrepancias de replay, manipulación
del plan y cola de ejecución. Los tests del censo vuelven a comprobar sus
recuentos y los hashes `E0_SHA` y `PLAN_SHA` usando únicamente artefactos A.

**Resultado:** 25/25 tests aprobados con Python 3.12, en 167,259 segundos,
sin partidas nuevas. Los perfiles B12 y R1 siguen verificándose con sus hashes
originales (`9192295d…b77` y `8bf07510…ff4`).

Todavía falta la comprobación real de base, partidas en paralelo y tiempos.
La calibración deberá reproducir los 378 niveles y el digest exacto B12 antes
de medir candidatos. Ningún test de software certifica esa paridad por sí solo.

El siguiente paso autorizado es **`estimate` después del cierre auditado**.
Con `estimate.json` se revisarán paridad, recursos y coste antes de continuar
el sondeo completo. Sus éxitos seguirían siendo controles de capacidad A,
con V4 sin evaluar; no descubrimientos autónomos ni S6 verde.

**22:28 CEST:** servicio `echoai-s6probe1-estimate.service` activo, estado
`WAITING_B12_AUDIT`. Se ha fijado el manifiesto de espera de 144 fuentes, con
cuatro workers. `games_started=false`; todavía no existen `budget.json`,
`parity.json` ni `estimate.json`. No hay un `run` completo encolado. No editar
las fuentes del sondeo durante esta espera: un cambio detendrá la cola.

[Estado del sondeo](../lab/seed/s6probe1-20260930/status.json) ·
[Lanzamiento](../lab/seed/s6probe1-20260930/estimate-launch.json).

[Contrato revisado](ECHO45-S6-PROBE1-DESIGN.md) ·
[Código](../seed/s6probe1.py) · [Pruebas](../tests/test_s6probe1.py).
