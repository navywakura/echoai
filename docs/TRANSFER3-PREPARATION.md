# TRANSFER-3 — preparación y custodia

**Revisión recibida y reparaciones:** [v5](TRANSFER3-REPAIR-V5.md) añade
verificación del inventario bajo el pestillo y vinculada al aviso completo.
Es un fixture público probado, no custodia externa: la API nueva rechaza
campañas reales. No reutilizar `custody.py` v1 como plantilla de campaña.

**Estado más reciente:** [v4](TRANSFER3-REHEARSAL-V4.md) comparó las tres
variantes con 128 movimientos de aprendizaje cada una en 64 salas nuevas.
Ninguna pasa el cribado; no existe aún candidatura para el examen final.
[Requisitos pendientes](TRANSFER3-FINAL-PROTOCOL-DRAFT.md) y
[reparaciones tras revisión](TRANSFER3-REPAIR-V5.md).
No generar secretos.

**Actualización:** [v3](TRANSFER3-REHEARSAL-V3.md) corrige la doble
contabilización y prueba recompensa/cobertura por separado. Hay mejoras
parciales y un nuevo fallo en la variante de recompensa; aún no se promueve
una candidatura para custodia. Los apartados siguientes conservan el recorrido.

2026-09-18. **Preparación, no cierre. ECHO-3 continúa en 13/15.**
Nav confirma que todavía no ha preparado la custodia. No hay compromiso
de campaña registrado en esta preparación. «C sin consumir» en los informes
anteriores no demuestra que exista un examen final generado y sellado.

## Qué está implementado

`nexus0/transfer3/custody.py` reutiliza las primitivas de `sim3/seal.py`:
compromiso del protocolo, derivación HMAC de semillas, compromiso salado de
inventario y apertura persistida única. Añade validación estricta del aviso
público y cotejo del inventario revelado contra **el compromiso publicado**.
No basta con comparar un inventario con su propio hash local. No se modifica
SIM-3 ni ningún código certificado anterior.

El único comando de custodia disponible es un ensayo con secretos públicos de SIM-3 y
hashes de paquetes ficticios. No crea mundos, no entrena, no vuela y no abre
el examen real. Usa archivos temporales que se eliminan al terminar.

Desde `echoai/`:

```sh
PYTHONPATH=.. python3 -m echoai.nexus0.transfer3.custody rehearsal
PYTHONPATH=.. python3 -m unittest echoai.tests.test_transfer3_custody -v
```

El resultado separa `rehearsal_ok` de `transfer3_green=false` y
`campaign_C_opened=false`. Los tests comprueban alteraciones de protocolo,
secreto, salt, compromiso e inventario; duplicados y campos privados;
apertura concurrente y consumo incluso si el examen falla.
Estos checks no acreditan publicación externa, aislamiento del custodio,
autenticidad de los paquetes ni ventaja conductual.

Verificado en esta preparación: 10 tests propios y 44 tests de SIM-3,
ambas suites con exit 0; ensayo CLI con `rehearsal_ok=true`.
La regresión amplia NEXUS-0 ejecutó 488 tests: ocho errores por sockets
locales prohibidos en el sandbox y un fallo esperado. Repetidas las tres
clases GUI afectadas fuera del sandbox, sus 29 tests pasan (exit 0).
No se presenta la ejecución amplia original como exit 0.

## Protocolo conductual: borrador, todavía no congelable

Pregunta vigente: lo aprendido en A debe mejorar B y C frente a scratch,
sin recibir mapa, nombre, seed, hash o solución del mundo.

- Reutilizar la percepción y el controlador de COMPOSE y las tablas T/Q
  existentes. No introducir otro bus ni un LLM.
- Definir una exportación por lista blanca de parámetros aprendidos de A.
  No importar el snapshot completo de COMPOSE sin auditarlo: contiene CAM,
  T y Q. Prohibidos mapas, episodios de A o índices ligados a coordenadas.
- Reiniciar pose, mapa, visitas, tracks y evidencia episódica en cada caso.
  Percepción y seguimiento siguen vivos; parámetros aprendidos y reglas no
  cambian durante B/C. Comprobarlo antes y después de cada episodio.
- Transferido y scratch comparten código, sensores, gate, presupuesto y
  condiciones iniciales; difieren sólo en el aprendizaje permitido de A.
  Registrar también el coste del entrenamiento. No atribuir a aprendizaje
  una ventaja procedente de priors programados o información desigual.
- Separar resultado funcional de resultado SITL. Los vuelos antiguos de
  COMPOSE no son nuevos mundos de confirmación. Semillas distintas tampoco
  prueban geometrías distintas: aplicar el criterio geométrico de SIM-3 §5.
- Congelar N, KPI principal, umbrales, tratamiento de empates/fallos y
  comparación pareada antes de la campaña. No seleccionarlos mirando B/C.

**Avance posterior:** formato de efectos sin episodios, control scratch,
control programado, runner aislado reutilizado y reconstrucción de trazas
están probados en el [primer ensayo público](TRANSFER3-REHEARSAL-V1.md).
El ensayo revela solapamiento geométrico y una ventaja limitada a disponer
de cinemática aprendida frente a T vacía. No cierra la hipótesis general.

**Pendiente:** generador conductual de confirmación y auditor de geometría
completo, resolver el alcance de la comparación, cálculo de potencia/N y
criterios numéricos; después, integración del examinador con custodia real.

**Actualización v2:** el [segundo ensayo público](TRANSFER3-REHEARSAL-V2.md)
ya excluye geometrías equivalentes y compara Q transferida contra scratch
con la misma cinemática. Ambos llegan en 15/16 casos: ventaja no demostrada.
Estas dos limitaciones de v1 están corregidas en el banco funcional, pero
todavía no hay candidatura justificada para el examen final ni hace falta
que Nav genere secretos. Se conserva el resultado negativo.
El ensayo de custodia no sustituye ese banco. No iniciar aún entrenamiento
de campaña, generar B/C finales ni pedir secretos al custodio.

## Cómo lo haremos sin que tengas nada preparado

1. El implementador termina el banco usando exclusivamente ensayos públicos,
   fija el protocolo y entrega código, dependencias y hashes verificables.
2. Nav prepara un entorno privado fuera del acceso de los agentes:
   preferiblemente otro equipo o una cuenta aislada sin acceso desde esta
   sesión. Una carpeta fuera del repo, `.gitignore` o permisos `0700` bajo
   el mismo usuario **no bastan**. No es necesario hacerlo ahora.
3. En ese entorno, el custodio ejecuta la futura herramienta de campaña:
   genera el secreto de 256 bits, B/C y salts; conserva el ledger de rechazos
   (máximo 100 intentos por caso), inventarios y registro de accesos. No
   escoge mundos según cómo se comporte la política.
4. Antes del aprendizaje de campaña en A, Nav registra fuera de este repo,
   con fecha, su identidad y los hashes del protocolo y compromisos B/C.
   Al implementador sólo le entrega el aviso público, sin secretos, seeds,
   salts, mapas, inventarios privados ni paquetes reservados.
5. Tras entrenar A y congelar snapshot/código, se ejecuta B con el examinador
   aislado. C sólo se abre tras superar B, sin retocar el candidato. C pasa
   `sealed → opened → consumed`, también ante fallo. Se publican todas las
   corridas y revelaciones al terminar; un reintento es reproducción, no un
   nuevo examen independiente.

La futura herramienta real debe ligar el aviso publicado y el freeze al
examinador antes de abrir paquetes, comprobar hashes de sus bytes y rechazar
rehearsal como campaña. **No existe todavía un comando de campaña listo para
Nav**; no ejecutar el ensayo con secretos reales ni interpretarlo como tal.

Referencia normativa: [SIM3-DESIGN §5](SIM3-DESIGN.md#5-abc-aislamiento-y-examen-sin-consumir)
y [contrato ECHO-3](ECHO-3-ACCEPTANCE.md).
