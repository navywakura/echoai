# E4-RELATION-1 — RELATION-A implementada y verificada

2026-09-22. **Inicio oficial de RELATION; A válida, fase completa todavía abierta.**
Auditoría reconstructiva en proceso nuevo válida, cero hallazgos,
`phase_a_valid=true`, **`relation1_green=false`**, también en el recibo.

115 fuentes fijadas, las 110 de INTERACTION y su evidencia intactas. Digest:
`ce24ccaa61f9d8b9b781274857b6ce15a9e75817bbf8d0b5fd2649a403369539`.
[Contrato](ECHO4-RELATION1-A-DESIGN.md) ·
[Informe](../lab/echo4/relation1-a-v1/report.json) ·
[Recibo](../lab/echo4/relation1-a-v1/audit-receipt.json).

## Lo que ya hace

Cada agente conserva en **su CAM original** episodios de encuentros: contexto,
acciones realmente observadas, coste propio, producción propia y tick.
Los enlaces permiten recorrer la historia global o la de una contraparte.
No copia Q ajena ni comparte una memoria global entre individuos.

«Historia compartida» significa que participaron en el encuentro, no que sus
recibos o conocimientos coincidan. Si uno no observa la acción del otro,
su historia conserva esa ausencia. Sin identidad, el episodio no se asigna
a una persona ni crea una cadena ficticia de pareja. Un intento conjunto
sin producción no cuenta como éxito; propuesta y predicción no son ejecución.

WSP16 conserva su layout; E[6] queda a cero. Recibos y enlaces utilizan los
campos host existentes de CAM. Los resúmenes se calculan al consultarlos;
no son hechos nuevos ni puntuaciones de afecto/confianza. La validación es
estructural y de consistencia con el simulador, no autenticación criptográfica
de sensores del mundo real. La procedencia nativa se contrasta reconstruyendo
la campaña completa y comparándola con los artefactos fijados.

Código: [memoria](../echo4/relation_memory.py),
[conexión nativa](../echo4/relation_session.py),
[banco y auditor](../echo4/relation_bench.py),
[pruebas](../tests/test_echo4_relation1a.py).

## Resultado del primer banco

Tres semillas de desarrollo, 144 rondas cada una; 96 de formación y 48 greedy.
Mismas contrapartes, incentivos privados y física que INTERACTION. Se compara
con la sesión original sin memoria relacional y con ejecución en orden inverso.

| Semilla | Episodios del aprendiz / contrapartes | Neto físico por identidad | Neto conjunto |
|---|---|---|---:|
| 113 | 144 / 72 / 72 | 279 / 24 / 144 | 447 |
| 127 | 144 / 72 / 72 | 274 / 24 / 144 | 442 |
| 139 | 144 / 72 / 72 | 298 / 24 / 174 | 496 |

**Acciones, costes, resultados y predicciones idénticos al control sin
grabación.** El orden inverso también reproduce trazas y digests de historia.
Los incentivos privados de contrapartes se excluyen del neto y de su memoria
relacional. No se atribuye ventaja conductual a esta igualdad: A es pasiva.
El banco corto no es el examen conductual D de INTERACTION, que sigue intacto.

864 episodios primarios en esas tres vidas y 48 en la prueba de observación
parcial: **912 episodios primarios reconstruibles**, más las réplicas de orden
inverso. La prueba parcial conserva seis encuentros sin identidad en la
historia del aprendiz, sin asignarlos a una contraparte conocida.

El banco principal ejecuta **7440 turnos nativos** incluyendo preformación,
controles, orden inverso y observación parcial; las pruebas unitarias son
trabajo adicional de desarrollo. El auditor repite la evidencia, no constituye
otra cohorte. No hay aún examen de transferencia.

## Verificación y límites

**36 pruebas nuevas; 181 pruebas distintas con regresiones seleccionadas,
todas aprobadas, sin omisiones.** Incluyen INTERACTION A/B/C/D, OTHER y
Q/T/inverso/encoder/gate, además de:

- Repetición, retroceso, límite 512 y transición de tick 255 a 256.
- Identidades separadas, ausencia de recibo y perspectivas asimétricas.
- Igual resumen agregado pero distinto orden → historia/digest distintos.
- Capacidad CAM, corrupción de enlaces/procedencia, entrada inválida y veto.
- Fallo de recibo o grabación tras ejecución: conservar costes y parar, sin
  fingir rollback ni escritura atómica entre ambas CAM.
- Replay en otra CAM con direcciones diferentes, sin acceder a memoria privada
  ajena ni ejecutar física; custodia y reconstrucción nativa en proceso nuevo.

No se modifica Agent.turn, T/Q ni gate. Cero borrados, hechos falsos y llamadas
al LLM en el banco. El presupuesto está acotado a 512 episodios/ticks por
observador; los huecos temporales son válidos, el wrap no. No sincroniza las
creencias de los agentes ni reanuda la sesión completa mediante CONTINUITY.

## Siguiente: RELATION-B

Conectar esta historia a decisiones aprendidas en otra tarea y medir ventaja
transferible frente a solo OTHER, sin historia, sin orden y sin identidad.
Igualar formación y recursos; publicar coste de toda la vida y comprobar si
se amortiza. Registrar una biografía o reproducirla no demuestra esa ventaja.
Después: C (ruptura/reencuentro y límites) y D (nuevo examen preregistrado).

RELATION no suma aún otro cierre: permanecen **9/13 hitos software (~69%)**,
no porcentaje de esfuerzo. Sin afirmación de conciencia subjetiva.
ROLES → INTEGRATE → RELEASE quedan después; hardware posterior y METAVERSE-1 último.
No Discord, web, commit, push ni publicación HF en esta entrega.

Desde `RXos`, con Python del sistema:

```bash
python3 -m unittest echoai.tests.test_echo4_relation1a
python3 -m echoai.echo4.relation_bench verify echoai/lab/echo4/relation1-a-v1
```

Para otra campaña usar un directorio nuevo; no sobrescribir los artefactos
sellados. `verify --write-receipt` se usa una vez en otro proceso tras crear
esa copia; repetir la auditoría existente no requiere escribir otro recibo.
