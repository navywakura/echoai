# HOST-1 — contrato prospectivo

2026-09-17. Pregunta: ¿la autoridad de fuente + signo + contexto sigue las
consecuencias observadas, en lugar de premiar la pulsación del signo?

## Dominio y reglas previas al examen

Banco funcional de instrucciones norte/sur de 1 m a 2,5 m de altura.
Dos fuentes de máquina, cuatro signos WSP (A–D), dos contextos públicos.
La identidad de fuente procede del adaptador, no del contenido del signo.
Antes de elegir fuente se conocen sus identificadores, signo y contexto;
su instrucción concreta se recibe después. No se afirma que el agente
desconozca la geometría si ya recibe una instrucción concreta.

Calibración supervisada, balanceada: el banco ejecuta instrucciones de ambas
fuentes, no sólo de la preferida. No es exploración autónoma. Una cinta
inmutable, generada antes de la interacción, fija todas las instrucciones y
sus fases; la máquina emisora no recibe acciones, elecciones ni rendimiento.
Esto es el control Anti-Clever-Hans, no una prueba con humanos.

Cada afirmación se registra antes de actuar. Sólo una consecuencia fresca,
con secuencia/WSP coincidentes, ACK y finalización del movimiento, más
extracto de posición, modifica estadísticas. El recibo debe llegar fresco
(≤250 ms) y la consecuencia ocurrir ≤15 s tras publicación. Llegar al objetivo afirmado
(error ≤350 mm) confirma la afirmación; un movimiento completado que acaba
fuera la contradice. ACK solo, rechazo, timeout, silencio, edad o repetición
no son consecuencias negativas. La afirmación nunca se escribe como FACT.
No nuevas CAM/Q/T, recompensas de botón en la política completa ni LLM.

Estado entero, acotado: ocho resultados por combinación, hasta 8 fuentes,
4 signos y 16 contextos (512 entradas). Autoridad = 256*aciertos//n;
se acepta con n≥4 y ≥75% de aciertos. Ventana sin decaimiento temporal:
desde ocho aciertos pierde permiso tras tres contradicciones; desde ocho
fallos recupera tras seis confirmaciones nuevas. No hay recuperación por
esperar o pulsar. Se rechazan secuencias reutilizadas y evidencia mal ligada.

## Comunicación y arbitraje

Actuador de salida SILENCIO|A|B|C|D sobre WSP 16 B (PREGUNTAR a OTRO,
style 1–4; silencio OBSERVAR style 0). Signo recibido: RESPONDER de OTRO.
Son símbolos acotados, no lenguaje libre ni un bus semántico adicional.
El mismo Host mantiene autoridad, registro pendiente y gasto comunicativo.

Prioridad: veto de seguridad → intención de vuelo → silencio si ocupado →
comunicación. Un símbolo cuesta 2 sim_u, exige oportunidad, reserva de 40
intacta y enfriamiento de 1 s. `budget` es la asignación acumulada para esta
sesión, no un saldo al que volver a restar débitos anteriores; Host descuenta
su gasto acumulado al conceder cada emisión. La intención de vuelo sólo es candidata:
para ejecutarla sigue siendo obligatorio SAFE/PX4/POWER; el arbitraje no
autoriza actuadores. Un WSP comunicativo no puede pasar por intención PX4.
Se prueban las cinco salidas, energía, oportunidad, ocupación, prioridad,
repetición y seguridad. No se confunde coste comunicativo con energía física.

## Banco, comparación y congelación

A: 20263901–20263916. B: 20264001–20264064. C: 20264101–20264164.
Una sesión por semilla y política: completa y control recompensa-botón.
Tres fases: fiabilidad inicial, inversión y restauración, ocho observaciones
por cada una de las 16 combinaciones en cada fase. Cada fase termina con
ocho decisiones de fuente (4 signos × 2 contextos), sin aprendizaje de examen.
Cada sesión tiene 384 observaciones y 24 decisiones; ambas políticas reciben
la misma cinta. Control: registra un acierto por pulsación, no por consecuencia.
Fuentes renombradas/orden permutado por semilla. Sin fuente privilegiada.

Verde B y C por separado: identidad completa del banco; completa ≥95% de
elecciones útiles y >control, contraste pareado por semilla p<0,025; pérdida
y recuperación dentro de 3/6 evidencias respectivamente en todas las claves;
cero cambios sin evidencia, atribución cruzada o bypass de comunicación.
El consumidor completo y control corren en namespaces SIM-3 sin mundo,
semilla, cinta o resultados futuros; se reejecuta cada traza para auditar.
Intervalos Wilson descriptivos, no fiabilidad social de producción.

Replay físico complementario: nominales A SAFE-1 y B/C SAFE-1 v2, tres
vuelos existentes auditados. Afirmaciones verdaderas/falsas se fijan respecto
al objetivo comandado antes de leer llegada; la llegada posterior medida
adjudica. No se acumula evidencia duplicando un mismo vuelo: son tres
observaciones por fuente, no un entrenamiento ficticio de cientos de vuelos.
No nuevos vuelos, control autónomo social, identidad autenticada, herencia
semántica, batería instrumentada ni cierre de DRONE-3/TRANSFER-3.

Congelar fuentes, tests, contrato, A y certificados previos antes de B;
B rojo bloquea C. C no consume TRANSFER-3. Mutantes: eliminar fuente/signo/
contexto, aprender por botón, ignorar consecuencia y saltar gate comunicativo.
Corrupciones de publicación, recibo, atribución, elección y numeradores/hashes.
Artefactos `lab/host1/` e informe `lab/echo3_host1_report.json`.
