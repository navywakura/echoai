# CONT-C — reanudación, cuerpo nuevo, descendencia y bifurcación

2026-09-22. **CONT-C completado y verificado en su perfil virtual CONT-B.**
CONTINUITY completo sigue abierto hasta CONT-D. No concede `continuity1_green`.
[Contrato previo](ECHO4-CONTINUITY1-C-DESIGN.md).

## Qué hace

`echo4/continuity_lineage.py` añade `LineageRun` alrededor del ejecutor CONT-B,
sin modificar sus agentes, políticas, física, codecs o certificados previos.
Cada agente sigue teniendo una sola CAM/Q/T y WSP de 16 bytes; córtex apagado.

| Operación | Identidad y relojes | Diagnóstico/permisos |
|---|---|---|
| Reanudar | Mismos individuo, cuerpo, rama, época y turnos | Conservados exactamente |
| Bifurcar | Dos ramas distintas del mismo punto virtual | Heredados del prefijo común; nuevos recibos vinculados a cada rama |
| Cambiar cuerpo | Mismo individuo/rama, nueva etiqueta y época; reloj global conservado, vida local en 0 | Revocados, cuarentena y recalibración |
| Descendiente | Nuevo individuo/cuerpo/rama; generación +1, turnos propios en 0 | Revocados, cuarentena y recalibración |

La igualdad sensorial no concede identidad ni permiso. Un individuo terminal
permanece terminal al reanudar o bifurcar; no puede cambiar de cuerpo para
revivir. Puede originar un descendiente separado, explícitamente registrado.

Las operaciones devuelven copias aisladas y dejan el origen intacto. Las
etiquetas son convenciones administrativas del custodio, no una deducción
del agente ni una prueba de identidad subjetiva. Una rama es una ejecución
virtual separada: no se asigna automáticamente a hardware.

## Herencia con revocación

La herencia transfiere CAM, Q/restos, T/inverso y PATTERN/contextos aprendidos
sin compartir memoria mutable con el padre. El hash de herencia se comprueba
durante cuarentena. Las observaciones heredadas no son experiencias nuevas
del receptor y sus tablas no garantizan rendimiento en un cuerpo diferente.

Se eliminan del estado operativo del receptor los permisos y el contexto
corporal anterior: BOUNDARY, referencia SELF, diagnóstico, recibos, recuperación,
ensayo de reutilización, último turno y ventana sensorial. La evidencia del
padre sigue intacta en su checkpoint, enlazado por hash; no se borran sus CAM.

El cuerpo nuevo no actúa ni diagnostica hasta recibir 16 pares públicos
nominales y una sonda nominal, vinculados al ámbito nuevo. La recalibración
es atómica: un recibo malo no deja media autorización. Después debe completar
otra sesión SELF confirmada para recuperar el control. El verificador vuelve
a construir la referencia a partir de esos pares; no acepta un booleano
`sealed=true` sin evidencia.

Los recibos nuevos llevan ámbito individuo/cuerpo/época/rama. Se rechaza el
ámbito del padre, del cuerpo anterior o de una hermana incluso cuando WSP y
token coinciden. Las bifurcaciones rechazan sondas pendientes o un buzón sin
consumir. Primero debe terminarse o cancelarse el trabajo externo pendiente.

## Verificación

**30 tests CONT-C pasan.** Cubren igualdad completa al reanudar, identidad
de referencias internas, independencia mutable entre ramas, revocación,
recalibración atómica y confirmación nueva, permisos ligados al ámbito,
terminalidad, herencia, relojes, costes declarados, corrupción/mutantes,
operación interrumpida, guardado sin reemplazo y proceso nuevo. Los 21 casos
del banco también pasan roundtrip dentro de esos tests. Lint aprobado.

El banco compara 21 continuaciones con procesos nuevos: **21/21 iguales,
125/125 eventos y 43/43 turnos nativos posteriores idénticos**, incluidos
hashes completos de estado, aprendizaje, recursos, permisos y relojes.

| Grupo | Casos | Eventos posteriores | Turnos posteriores |
|---|---:|---:|---:|
| Reanudar diagnóstico, recuperación y reutilización | 3 | 27 | 9 |
| Hermanas con entradas iguales y con objetivos diferentes | 4 | 10 | 10 |
| Cuerpos nuevos/descendientes en cuarentena | 4 | 4 | 0 |
| Recalibrados/activos, segundo cuerpo y fork posterior | 8 | 84 | 24 |
| Reanudar y bifurcar un individuo terminal | 2 | 0 | 0 |

Los cuatro eventos de cuarentena son rechazos de acción, no turnos físicos.
Los ensayos ya completados y terminales no se cuentan como vidas completadas.
Bajo entradas iguales las hermanas tienen la misma trayectoria física,
aunque sus hashes completos difieren por la procedencia. Bajo objetivos
distintos se ejecutan acciones distintas: 0 produce H=65/θ=62, y 1 produce
H=57/θ=30. Es divergencia medida, no una trayectoria contrafactual inventada.

Los ocho controles del banco pasan: reanudación exacta, invariantes, igualdad
física con entradas iguales, ramas distintas, divergencia observada,
terminalidad, cuarentena sin acciones y fuentes intactas. Cero cortex_calls,
false_facts y destroyed; balances conservados en todos los casos.
La reconstrucción independiente desde recetas devuelve **`valid=true`, sin
hallazgos**: vuelve a preparar cada padre/cuerpo, reproduce los checkpoints,
reanuda en procesos nuevos y reconstruye el informe entero. No se limita a
confiar en `equal=true` o `development_passed=true` del archivo guardado.
Un control negativo sustituye en memoria el primer checkpoint por `{}`:
el verificador lo rechaza con `resume_diagnostic: checkpoint differs from
reconstruction`. Los archivos originales no se modifican.

Ya completado en esta entrega: 805 regresiones generales (804 aprobadas y
un fallo esperado histórico), 37 tests CONT-B aprobados y auditorías CONT-A/B
válidas, sin hallazgos. Total: **872 pruebas, 871 aprobadas y un fallo esperado**.
Las 50 fuentes SELF final, 37 CONT-A y 50 CONT-B conservan sus hashes.
No se presenta esa integridad como una nueva campaña completa de cierre SELF.

## Uso y reproducción

[Informe de desarrollo](../lab/echo4/continuity1-c-v1/report.json):
`development_passed=true`, **`continuity1_green=false`**, 54 fuentes fijadas.
SHA-256:

```text
4c2bae3b6f68e74a30aa9712a42bdf0f47c9178b463b1af5459dab7639174b40
```

El custodio suministra el digest esperado del checkpoint CONT-B. Ejemplo de
API, sin ejecutar automáticamente calibración, física o recuperación:

```python
from echoai.echo4.continuity_lineage import LineageRun
from echoai.echo4.world import Body

run = LineageRun.import_active(raw_b, expected_sha256=trusted_digest_b,
                              individual="echo-1", body="body-1")
left, right = run.fork("left", "right")  # requiere no tener sondas pendientes
successor = run.allocate_body(Body(60, 46), body_id="body-2", token="allocation-1")
descendant = run.allocate_body(Body(60, 46), body_id="body-3", token="allocation-2",
                               individual="echo-2")
# Ambos quedan en cuarentena. Solo evidencia nueva del custodio permite:
successor.commission(new_pairs, new_nominal_receipt, scope=successor.scope)
# Todavía falta confirmar su nueva sesión SELF antes de autorizar acciones.
```

Desde `echoai/`:

```bash
PYTHONPATH=.. python3 -m unittest echoai.tests.test_echo4_continuity1c -v
PYTHONPATH=.. python3 -m echoai.echo4.continuity_lineage_bench verify lab/echo4/continuity1-c-v1
```

Para una campaña nueva se usa `campaign` con **otro directorio inexistente**.
No sobreescribir los checkpoints o el informe de desarrollo publicado.

## Costes y límites

Los 21 checkpoints ocupan **34.522.092 bytes**, entre 1.630.193 y 1.655.012
bytes cada uno. WSP sigue siendo el cable de 16 bytes; no es el tamaño total
del estado persistente. No se atribuyen aquí energía ni rendimiento en NPU.

Una recalibración completa cuesta 64 transiciones físicas de los 16 pares y
ocho de la sonda nominal: **72**, además de las sondas de confirmación SELF.
No se atribuyen gratuitamente al conocimiento heredado ni a los turnos nativos
posteriores. Los nuevos recursos corporales son una **asignación externa**
registrada (`external_h`), no recompensa o reserva creada por el agente.
Los padres proceden de las escuelas ya declaradas: 72 transiciones para
recuperación o 96 para reutilización, más sus diagnósticos y acciones previas
al checkpoint. Los 43 turnos de la tabla solo cuentan la continuación, no
todo ese coste de preparación ni una transferencia gratuita de conocimiento.

Cadena limitada a 32 enlaces. Hashes y digest externo ofrecen integridad bajo
un custodio confiable, no autentican sensores ni son firma criptográfica.
No hay registro global de exclusividad, anti-rollback, fusión de ramas,
trasplante físico autónomo, concurrencia ni recuperación exactamente una vez
tras apagón. Volver a cargar el mismo checkpoint no garantiza que no exista
otro proceso con esa identidad. El custodio debe gestionar esa exclusividad.
El verificador del banco reconstruye los padres desde las recetas; cargar
un checkpoint aislado no recupera por arte de magia los archivos ancestrales.

El formato CONT-C envuelve el perfil CONT-B; no importa CONT-A silenciosamente.
Los checkpoints privados contienen estado físico: no son entrada para Qwen.
Un fork con dos resultados medidos no implementa DREAM ni responde sobre
ramas que nunca se ejecutaron.

## Siguiente

CONT-D: examen conjunto A/B/C nuevo, fuentes congeladas, ablaciones y replay
de cierre. DREAM permanece PLAN; hardware después, METAVERSE-1 último.
Sin commit, push, publicación web ni despliegue en esta entrega.
