# SIM-3 — manifiestos y runners reproducibles

**Estado:** capa de reproducción implementada el 2026-09-10. No vuelve verde
por sí misma el banco histórico: cambió el inventario de código y el backend
debe ejecutarse otra vez bajo lock nuevo antes de publicar un resultado comparable.

## Manifiestos congelados

| Artefacto | Propósito | Puede llegar al consumidor |
|---|---|---|
| `sim3-world-family.schema.json` | rangos declarativos de las tres topologías v1 | no |
| `sim3-campaign.schema.json` | protocolo, lock, código, particiones, KPI y compromisos | no |
| `echo3-slice.schema.json` | contrato de aceptación de una fase ECHO-3 | no |

```bash
cd /home/user/REALRXOS/RXos/echoai
PYTHONPATH=.. python3 -m echoai.nexus0.sim3 declaration family docs/examples/sim3-families/rehearsal-v1.json
PYTHONPATH=.. python3 -m echoai.nexus0.sim3 declaration campaign docs/examples/sim3-campaigns/sim3-rehearsal-20260910.json
PYTHONPATH=.. python3 -m echoai.nexus0.sim3 declaration slice docs/examples/echo3-slices/sim3.json
```

La campaña de ejemplo reconstruye el ensayo publicado el 2026-09-10. Sus
semillas y C son públicos; no es una campaña conductual ni consume un C real.
La familia reproduce los doce hashes de paquetes publicados. Los rangos salen
ahora de JSON validado, pero la topología v1 sigue cerrada para evitar plugins,
sensores o una ruta oracle.

Para una campaña real, Nav conserva fuera del repositorio secreto, salt,
inventario B/C y registro de accesos. Se genera C sólo tras el freeze; ningún
prompt, runner ni agente debe crearla en el árbol de trabajo.

## Runner de host

```bash
PYTHONPATH=.. python3 -m echoai.nexus0.sim3 run --accept-lock-change
```

El runner realiza `imagen → preflight → bench → audit`. Construye la imagen
local digest-pinned sólo si no existe, con `--pull=never`; si falta la base,
Podman/Bubblewrap o el sandbox efectivo, devuelve `not_run`, el motivo y el
siguiente comando. No hay backend sustituido.

Antes de escribir un lock compara imagen, versiones instaladas, sandbox y
hashes de código con el lock previo. Si cambian, se niega a sobrescribirlo sin
`--accept-lock-change`. Aceptarlo no recicla resultados: congela el nuevo lock
y obliga a ejecutar el banco completo antes de considerar su informe. Un
auditor rechaza informes que mezclen locks entre ejecuciones.

En el entorno de Codex, Podman no pudo usar su configuración bajo
`/run/user/1000/libpod`: el intento devolvió `not_run` y por eso allí no se
actualizó el informe ni se declaró corrida nueva.

Confirmado después en el host de laboratorio, con backend real:

```bash
PYTHONPATH=.. python3 -m echoai.nexus0.sim3 run                        # exit 1
#   status=not_run, reason="runtime lock changed; existing report is not comparable"
PYTHONPATH=.. python3 -m echoai.nexus0.sim3 run --accept-lock-change   # exit 0
#   status=pass, sim3_green=true, evidence_valid=true, 624,8 s
```

El banco completo se repitió bajo lock nuevo
`80ef5a38853b6b92d4b21093857f7cda6d0a7966f259764475e3668604fdbf2a`
(código `00c4061af6cefabc511380706734f756cbef39deb90d3ef7b3a81b6895752346`,
29 archivos) y cerró verde en los diez grupos; informe
`lab/echo3_sim3_report.json` (`2d4fc12d…`),
auditoría `lab/echo3_sim3_audit.json` con 416 comprobaciones, 0 hallazgos y
los diez mutantes de informe rechazados. Las medidas de física salieron
idénticas a las de la primera corrida.

Guardas verificadas por separado, cada una con su código de salida real:
`bench` sobre un lock que no pina el código actual devuelve 3 y
`lock_stale`; el auditor sobre un informe cuyo inventario cambió devuelve 1 y
`code_sha256`; `run` sin `--accept-lock-change` devuelve 1 y nombra los dos
locks. `ci` sin `SIM3_CI_BACKEND` devuelve 0 con `backend=not_run`, su motivo
y el siguiente comando.

## CI

```bash
# rápido: pruebas unitarias; backend=not_run si no se solicita
PYTHONPATH=.. python3 -m echoai.nexus0.sim3 ci

# worker provisionado: banco real mediante el runner
SIM3_CI_BACKEND=1 PYTHONPATH=.. python3 -m echoai.nexus0.sim3 ci
```

El CI rápido puede pasar sus pruebas unitarias y publicar `backend=not_run`;
no es un certificado SIM-3. Con `SIM3_CI_BACKEND=1`, un backend no disponible
o rojo conserva su causa y hace fallar esa ejecución.

## Comprobación de diseño

- El runner no ramifica por sala, semilla ni partición.
- Los manifiestos no exportan mapa, waypoint, rol, hash, semilla ni solución
  al consumidor. El transporte sigue limitado a `v`, `seq`, `sim_time_ns`.
- Un informe cita un solo lock por ejecución; mezclar locks falla auditoría.
- Las pruebas parten de ejemplos válidos y rechazan campos desconocidos.
- No se ha generado ni abierto un examen C reservado.
- La familia de mundos no entra en el inventario de código: mutarla no cambia
  `code_sha256`. Queda cubierta por otra puerta, comprobada mutándola de
  verdad — el auditor regenera los doce paquetes y falla en `package_sha` y
  `fingerprint` de los mundos afectados. El manifiesto de campaña además fija
  su `family_sha256`.
