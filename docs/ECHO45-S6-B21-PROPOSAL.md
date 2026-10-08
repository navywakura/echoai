# S6-B21: memoria temporal, crédito diferido y descubrimiento acotado

Propuesta privada original, 6 de octubre de 2026. **Actualización:** B21-A
ya está implementado y prerregistrado; espera el cierre auditado B20 para
medir. Este documento conserva el diseño de las etapas posteriores. El
contrato ejecutable vigente es [B21-A](ECHO45-S6-B21-A-DESIGN.md), con
[implementación](ECHO45-S6-B21-IMPLEMENTATION.md) y
[estado actualizado](ECHO45-S6-B21-A-RESULTS.md).

El objetivo es encontrar una mejora conservadora mediante experiencias
propias, sin insertar una regla conocida por el investigador. La inspiración
biológica se concreta en memoria temporal, asignación de crédito tardío,
revisión de experiencias y separación de exploración y consolidación. Cada
pieza necesita una ablación: su nombre no demuestra capacidad neuronal.

La mejora humana de capacidad B20 prueba que el lenguaje actual expresa una
reparación útil en desarrollo. Antes de ampliar representación hay que
comprobar si el bloqueo principal es la cobertura del buscador. El micro B20
produjo 85 intentos con pérdidas, 28 sin ganancias de niveles y 31 con +1
conservador. Ninguno alcanzó +2 sin pérdidas. El LLM solo propuso tres arranques.

| Hipótesis | Evidencia disponible | Prueba que la distingue |
|---|---|---|
| La selección de duración impide llegar a una regla útil | Sin objetivo, B20 solo explora HOLD=0; el control conocido usa otro valor | Balancear duración y condiciones sin cambiar el actor, comparado con B20 y muestreo de gramática |
| El crédito mezcla intervenciones y efectos tardíos | El ranking usa asociaciones por partida y conjuntos de lecturas | Intervenciones controladas con restauración exacta o nueva simulación; medir calidad de predicción de pérdidas |
| Falta historia observable para decidir cuándo reiniciar | Una feature instantánea no expresa toda la actividad iniciada antes | Contrastar situaciones de contexto instantáneo igual e historia distinta; evaluar si memoria temporal mejora predicción y decisiones |
| Los pocos arranques LLM aportan poca diversidad útil | Las tres semillas repitieron sus series de métricas | Leer respuestas completas; comparar inicialización sola frente a crítica durante el ciclo, con presupuesto explícito |
| Hay pérdida de diversidad al agrupar o seleccionar ramas | Muchas sintaxis se reducen a representantes; no existe prueba de equivalencia futura | Registrar disponibilidad, exposición y selección; probar rotación y archivos de conducta con ablación |
| El umbral de niveles se aproxima mal mediante el ranking | Abundan +1 conservadores y ganancias mayores con pérdidas | Aprender ganancia, pérdida y coste por separado; medir calibración sin cambiar V3 |

**B21-A: comprobar cobertura antes de cambiar el cerebro.** Mantener el actor,
modelo, lenguaje y juez. Comparar tres buscadores con las mismas observaciones,
base, máximo de 18 propuestas y partidas por propuesta: B20 congelado;
exploración balanceada por duración y condiciones; muestreo de la misma
gramática como control. La comparación inicial usa desarrollo ya consumido y
se etiqueta como diagnóstico, no confirmación de transferencia.

Una política de cobertura propuesta reservaría diez plazas para las diez
duraciones ya declaradas (0,1,2,4,8,12,16,20,24,32), con condiciones elegidas
por reglas generales y semillas registradas. Las otras ocho plazas se
repartirían entre reparar pérdidas y explorar contextos distintos. Un candidato
equivalente o inerte certificado se registra y consume su plaza lógica; no
habilita intentos gratuitos. Esta asignación es una propuesta que debe
congelarse antes de medir; no ha demostrado utilidad.

No se fuerza un orden favorable a la regla humana. Los valores y umbrales
proceden del lenguaje existente; no se añade una pareja valor/condición
especial. Todas las condiciones legales reciben una probabilidad o ruta de
exploración documentada. La selección informa cobertura efectiva, no solo
tamaño de la gramática. Los resultados B20 sirven al diseñador; no se
entregan sus reglas humanas o sus ganadores como memoria al agente nuevo.

Si mejorar cobertura consigue +2 sin pérdidas y conservación nueva, la memoria
temporal no se declarará necesaria para ese hallazgo. Si no lo consigue, se
informará el espacio medido, sin concluir agotamiento universal del lenguaje.

**B21-B: el paradigma temporal inspirado en biología.** Cuatro piezas propuestas:

| Pieza | Estado y función | Qué tendría que demostrar |
|---|---|---|
| EPISODE-1 | Memoria acotada de observación, acción, resultado y orden temporal por intento; reinicio correcto de su estado | Reconstrucción determinista, continuidad y distinción útil entre historias |
| CREDIT-1 | Huellas de intervenciones y consecuencias diferidas, separadas por base, valor, linaje y episodio | Mejor atribución predictiva de ganancias/pérdidas sin convertir correlaciones en hechos |
| REPLAY-1 | Selección de experiencias para revisar y simular contrastes con restauración comprobada | Mejor decisión por unidad de coste en juegos nuevos; ninguna predicción validada solo por leer trazas viejas |
| CONSOLIDATE-1 | Archivo de hipótesis por ganancia, pérdidas, incertidumbre y coste; solo promueve lo que pasa el juez | Aprender de un +1 rechazado sin integrarlo como mejora aceptada, y conservar las mejoras promovidas |

EPISODE-1 usará solo observaciones accesibles al agente. Features candidatas:
tiempo desde la última intervención relevante; progreso visual acumulado
desde ella; consistencia de predicciones recientes; número de reinicios sin
progreso; incertidumbre de que una actividad observada continúe. Sus límites,
cuantización y reinicio por nivel/partida se declaran antes de medir. No entran
IDs de tareas, semillas, score privado ni actividad interna oculta del mundo.
Una estimación de actividad se etiqueta como hipótesis, nunca como acceso
privilegiado al simulador.

Una huella de elegibilidad de ingeniería puede conservar qué intervención
estuvo activa al llegar una consecuencia:

\[
e_t=\lambda e_{t-1}+\mathbf 1\{\text{intervención relevante en }t\},
\quad 0\leq\lambda<1.
\]

Para el núcleo discreto, el decaimiento se representaría mediante enteros y
operaciones acotadas, reutilizando sus estructuras existentes. La ecuación
describe una propuesta temporal, no una implementación e-prop ni una prueba
de causalidad. Una recompensa tardía puede tener varias causas; debe
conservarse incertidumbre y limitar el horizonte del crédito. La actualización
del ranking no tiene permiso para modificar el verificador.

La inspiración para señales de aprendizaje tardías procede de
[Bellec y colaboradores](https://arxiv.org/abs/1901.09049), que estudian
trazas de elegibilidad en redes recurrentes de impulsos. Su trabajo no evalúa
ECHO, HOLD ni S6. La selección útil de experiencias se inspira en el modelo de
[Mattar y Daw](https://www.nature.com/articles/s41593-018-0232-z) sobre
replay hipocampal y planificación. Es una transferencia de ideas por investigar,
no evidencia de que ECHO reproduzca un cerebro.

REPLAY-1 necesita agente, entorno, memoria y RNG restaurables. Primero debe
reproducir exactamente la rama basal. Si no hay snapshots completos fiables,
se reejecuta la partida de desarrollo desde el inicio. Cambiar una política
crea observaciones nuevas; no se puntúa la nueva política únicamente sobre
frames de la anterior. Una divergencia de restauración bloquea el instrumento.
La GPU no convierte una traza estática en un simulador contrafactual.

CONSOLIDATE-1 conservará varias ramas no dominadas y huellas de conducta,
sin sumar mejoras incompatibles. El archivo puede estudiar propuestas
rechazadas, pero la política estable no cambia hasta pasar la aceptación.
Dos +1 sobre un mismo caso no se suman. Combinar dos parches requeriría una
subcondición nueva, precedencia definida y medición de interacciones; no se
introduce silenciosamente en el contrato de un parche.

**Prueba factorial propuesta.** Tras resolver B21-A, congelar un buscador común
y comparar memoria temporal apagada/activa por neocórtex solo inicial/en bucle.
Los cuatro brazos recibirán el mismo lenguaje permitido, límite de 18 propuestas
y presupuesto de juegos. La diferencia de historia disponible es la intervención
experimental. Los brazos de neocórtex inicial tienen una generación; los de
bucle, hasta tres generaciones en puntos predeclarados, con máximo de tokens
por llamada igual al modelo cualificado. Debe informarse el coste adicional:
no se presentará esta diferencia como igual cómputo total.

Antes del ensayo de ventaja a presupuesto total fijo se calibran segundos
CPU/GPU y tokens, y se fija un techo común que incluya generación, búsqueda,
juegos rechazados, replays y auditorías. No se cambia el techo tras ver resultados.
Un control adicional de síntesis sin LLM ayuda a distinguir utilidad del
neocórtex de utilidad de la memoria. Repetir un recorrido determinista sin
variación no añade muestras independientes. Tres semillas son un piloto de
sensibilidad, no una prueba estadística fuerte de superioridad general.

**Qué significaría descubrir autónomamente.** El agente comienza de la base
declarada y su historia autorizada. Puede crear hipótesis mediante lenguaje
común, medirlas en desarrollo y actualizar prioridades con sus propios
resultados. No recibe una regla ganadora, su posición en un ranking, datos
protegidos ni un prompt que codifique la solución. La propuesta, solicitud,
respuesta, parentesco y todas las evaluaciones quedan registradas. El diseño
del arnés es humano; la afirmación se limita al descubrimiento dentro del
espacio y presupuesto declarados.

Antes de lanzar, separar materialmente el paquete del agente de controles
humanos y archivos de investigación. Verificar el allowlist de entradas,
hashes y contenido: no basta con pedir al modelo que no los lea. Auditor y
buscador tienen cachés separadas; las trayectorias protegidas nunca regresan
al selector. Los datos de B20 ya consumidos no vuelven a denominarse ciegos.

**Puertas y mediciones.** V3 conserva ganancia >=2 y cero pérdidas individuales
de niveles o score (tolerancia 1e-10). Congelar antes de ampliar el primer
candidato que pase. Evaluar desarrollo amplio y después una reserva nueva
cuya ausencia de exposición se verifique. Si se usa una ampliación fallida
para reparar, pasa a ser desarrollo de otra condición y se cambia la reserva.
Hay replay completo, caché independiente y revisión aritmética separada.

Medir: tasa de propuestas aceptadas; coste hasta primer candidato conservador;
ganancia de niveles y vector de pérdidas; score; acciones y reinicios por nivel;
duraciones/condiciones realmente exploradas; ramas y conductas distintas;
calibración de predicciones de coste y pérdida; tokens y segundos CPU/GPU.
La mejora de eficiencia se informa aparte de la mejora de niveles. Los
porcentajes ARC exigen una evaluación ARC propia y separada.

Un pase de cualificación habilita el contrato posterior desde SEMILLA. S6
requiere piloto y campaña auditados, y el examen SEMILLA/FIJO/ECHO/SIN FILTRO
con B1-B5: ECHO >=105 % de niveles SEMILLA sin reducir score medio; superioridad
en niveles frente a FIJO y SIN FILTRO; retención oficial; auditoría/procedencia
válidas. No hay promoción automática a S6 verde por encontrar una guarda.

**Riesgos antes de invertir un ensayo largo.** Comprobar estado temporal
después de reinicios; horizontes de crédito que atraviesan indebidamente
episodios; crédito positivo por bucles repetidos; firma de observación que
confunde historias; pares de políticas no restaurables; contexto LLM que
omite la pérdida principal; formato correcto con condiciones sin efecto;
memoria que memoriza IDs; selección que solo recorre HOLD=0; equivalencia
observada usada como prueba universal; y evaluación de una variante elegida
después de inspeccionar reserva. Cada fallo del instrumento bloquea; un fallo
científico se registra aunque la narrativa biológica resulte atractiva.

**Decisiones visibles.** Reutilizar el diario y visor existentes. Cada evento
guardará observación real, memoria consultada, hipótesis registrada, candidatos
considerados, intervención, resultado, coste y veredicto. El neocórtex podrá
resumir esos campos con referencias al registro. Una explicación reconstruida
se identifica como interpretación; si falta una razón, se muestra como ausente.
No se fabrica una voz interior ni se devuelve la prosa del visor al agente.
No se instrumenta ni reabre reserva o examen para observarlo.

El siguiente trabajo autorizado por este documento es diseñar el contrato y
sus pruebas, no ejecutar un experimento por sí solo. No hay fecha, porcentaje
de mejora ni probabilidad de verde justificable antes de medir B21.
