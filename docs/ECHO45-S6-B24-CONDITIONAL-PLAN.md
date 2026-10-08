# B24 — cooperación entre investigadores, condicionada a B23

8 de octubre de 2026. **PLAN_FUTURO_CONDICIONAL. Sin implementación,
partidas, entrenamiento ni lanzamiento.** Decisión del propietario: conservar
esta propuesta para B24 si B23 termina sin una mejora validada; si B23 supera
su diagnóstico y conservación, trasladarla al programa ECHO-5, en la línea
de organización y cooperación prevista para 5.1.

## Condición de activación

Se esperará al cierre y auditoría de B23. Un error de transporte, falta de
cuota, timeout o discrepancia de replay significa instrumento incompleto;
primero requiere recuperación y no cuenta como refutación científica.

Actualización del 8 de octubre: [B23-R3 cerró sin ganador](ECHO45-S6-B23-KAGGLE-RESULTS-20261008.md)
con 54 propuestas medidas de buscadores y 36 llamadas a Qwen que no
produjeron ninguna propuesta ejecutable. La auditoría de la sesión es válida;
la comparación de capacidad 7B/14B queda inconclusa por el formato de
salida. Antes de iniciar la comparación de cooperación, se estudiará esa
interfaz en una condición nueva. Esta constatación no cambia B23-R3.

Si ningún finalista de B23 supera micro, desarrollo amplio y conservación,
esta propuesta será candidata a B24, precedida por una revisión de por qué
falló B23. Si alguno supera esas fases con recibos válidos, la propuesta
queda en ECHO-5 y se continúa la confirmación de S6 desde SEMILLA.
Un pase de B23 no equivale a S6 verde: el ejecutor actual deja explícitos
`s6_green=false`, campaña y confirmación pendientes, y examen sin abrir.

Si el diagnóstico muestra un límite de representación o un fallo del juez,
añadir investigadores no se presentará como solución suficiente. Primero se
documentará qué mecanismo puede mejorar la cooperación. No habrá lanzamiento
automático de B24 ni cambios sobre la ejecución congelada de B23.

## Pregunta y antecedentes

¿Compartir resultados comprobados entre investigadores permite descubrir
más políticas que conservan su mejora en casos nuevos, dentro de los mismos
límites de propuestas, llamadas, tokens y partidas?

ROLES-1 v5 dedujo competencias en una tribu de tres agentes y redujo consultas
aproximadamente un 25–27 %, pero obtuvo menos producción neta que el orden
fijo. Es un antecedente de selección de interlocutores; la ventaja de una
organización multiagente sigue siendo una hipótesis.
[Resultados de Tribu](ECHO4-ROLES1-V5-RESULTS.md).

B22 encontró problemas de transferencia y búsqueda. B23 separa selector y
neocórtex con cinco brazos independientes. Varios procesos de evaluación de
partidas no constituyen varios investigadores que aprenden juntos.

## Comparación propuesta

El actor, DSL, modelo base, cuantización, herramientas, juez y presupuesto por
partida serán comunes. Se estudiarán varios investigadores sobre el mismo
actor; introducir varios cuerpos cooperando en un mundo es otro experimento.

| Condición | Contextos y experiencia disponible | Máximo de propuestas |
|---|---|---:|
| Individual | Un investigador secuencial con su historial completo | 18 |
| Independientes | Tres investigadores; cada uno recibe solo su historial | 3 × 6 |
| Cooperativos | Tres investigadores con intercambio de recibos de desarrollo | 3 × 6 |

El primer contraste aislará el intercambio: instrucciones y funciones
disponibles serán iguales en las tres condiciones. Exploración, reparación
y búsqueda de contraejemplos estarán disponibles para todos. No se añadirá
simultáneamente una personalidad, un modelo distinto y un selector adaptativo
solo al brazo cooperativo.

Para los dos grupos de tres se proponen tres rondas de seis plazas, dos por
investigador. En cooperación se compartirá el archivo al terminar cada ronda;
en independientes seguirá aislado. La primera ronda parte del mismo material
inicial. El orden se sembrará y el intercambio será una barrera determinista,
evitando que la velocidad de un proceso cambie los datos de otro.

Una instancia del modelo puede atender los contextos por turnos en las dos
T4. El número de investigadores lógicos no exige otras tantas copias de
pesos. Se registrarán memoria, latencia, tiempo GPU, consultas y coste de
coordinación; igualdad de límites no garantiza igualdad del gasto realizado.

## Memoria, crédito y verificación

El archivo compartido conservará identificador de propuesta y padre,
programa exacto, autor, contexto, resultados por caso, pérdidas, coste y hash
del recibo. Separará hipótesis, mediciones y políticas aceptadas. Las ganancias
de un padre nunca se atribuirán a un descendiente sin evaluarlo.

El intercambio utilizará estructuras existentes y mensajes de investigación;
no añadirá otro bus al núcleo ni activará un LLM en NEXUS-0. Los prompts
exactos serán auditables. El visor mostrará observaciones, propuestas,
explicaciones declaradas y resultados; no inventará pensamientos internos.

En el primer contraste, el reparto de plazas será fijo. Queda reservada una
ablación posterior para asignarlas por contribución verificada: una mejora,
una reparación útil o un contraejemplo reproducido. El desacuerdo verbal y
la mera acumulación de fallos no acreditarán competencia. Las contribuciones
compartidas conservarán su linaje para no premiar varias veces la misma idea.

La recompensa de investigación y el criterio de promoción estarán separados.
Seleccionar propuestas, actualizar memoria o dar más oportunidades a una rama
no modifica los pesos del LLM. Entrenarlos mediante RL o ajuste fino corresponde
a otro contrato, en la línea futura RSI-2.

El juez seguirá fuera del alcance de escritura de los investigadores. La
aceptación conservará ganancia de al menos dos niveles y ninguna pérdida
individual de niveles o score, con la tolerancia registrada, replay y
auditoría. Las ramas rechazadas podrán orientar investigación sin cambiar
la política estable. Un resultado inconcluso será «no resuelto con este
presupuesto»; declarar imposibilidad requeriría un certificado verificable
en un dominio acotado, sin puntos gratuitos por abandonar.

## Medición y cierre que habría que congelar

Se contará cada propuesta inválida, repetida o rechazada y cada llamada,
token, partida, replay, auditoría y comprobación adicional. Un coordinador
LLM, si se añadiera en otra condición, consumiría el mismo presupuesto total.
El contraste inicial no necesita un cuarto LLM coordinador.

Los indicadores serán: pases sin regresiones, tiempo y gasto hasta el primer
pase, niveles y score por caso, diversidad de propuestas, duplicados,
reparaciones útiles y supervivencia en desarrollo amplio y reserva nueva.
Se reportará tanto éxito dentro del presupuesto como coste realizado.

Antes de medir se fijarán modelo y hashes, cohortes y exposición histórica,
semillas de investigación, orden, límites totales de cómputo, reglas de parada,
selección de finalistas y criterio estadístico. La calibración tendrá datos
separados y no se incorporará después como confirmación. Una sola ejecución
serviría para diagnosticar el instrumento, no para afirmar superioridad.
El tamaño de la confirmación se dimensionará antes de abrir su reserva.

La selección usará solo desarrollo. Se congelarán todos los finalistas antes
de validarlos; las pérdidas reservadas no se devolverán al enjambre ni se
sustituirá al ganador tras verlas. Un fallo de integridad o replay detendrá
el ensayo y quedará separado de un resultado científico negativo.

Cooperativos frente a independientes medirá la aportación del intercambio.
Independientes frente a individual medirá el efecto de dividir contextos.
Si cooperativos no supera ambos controles con coste y conservación
comparables, no se acreditará ventaja de cooperación. Ninguno de esos pases
sustituirá piloto, campaña y examen B1–B5 para el cierre de S6.

## Destino si B23 funciona

La misma propuesta pasará a ECHO-5, especialmente su línea 5.1 de organización,
memoria compartida y eficiencia. ECHO-5.5 estudiará retención entre sesiones;
RSI-1, mejora del investigador; RSI-2, actualización de adaptadores o pesos.
No se presuponen inteligencia general, alucinaciones cero ni mejora recursiva
por el mero hecho de aumentar el número de agentes.

Fuentes de la discusión previa: [OpenAI, incidente y medidas](https://openai.com/index/hugging-face-incident-and-the-road-ahead/),
[investigación independiente de METR](https://metr.org/blog/2026-08-26-openai-hugging-face-incident-investigation/),
[autojuego multiagente con entrenamiento PPO](https://openai.com/index/emergent-tool-use/)
y [comparación controlada de arquitecturas de agentes](https://arxiv.org/abs/2512.08296).
Sirven como antecedentes; no son resultados obtenidos por ECHO.
