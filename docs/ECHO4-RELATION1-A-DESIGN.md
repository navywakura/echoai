# E4-RELATION-1 — inicio oficial y contrato A

2026-09-22. Autorizado tras INTERACTION B/C/D. Sus 110 fuentes y evidencias
permanecen congeladas; no se cambia su resultado ni se reutiliza D como examen.

## Pregunta y etapas

¿Una historia compartida de acciones y consecuencias aporta una ventaja
causal transferible, más allá de identificar y predecir una contraparte?
Una relación se estudia aquí como historia funcional, no vínculo sentido,
alma o certificación de conciencia. «Compartida» no significa CAM común ni
que ambos sepan lo mismo: cada individuo conserva su observación privada
de encuentros conjuntos, que puede ser incompleta o distinta de la ajena.

1. **RELATION-A, esta entrega:** episodios ordenados en la CAM original,
   procedencia, separación por contraparte, costes propios y resultados
   observados; unión con ejecuciones nativas y reconstrucción de esa memoria.
2. **RELATION-B, pendiente:** usar esa historia en decisiones aprendidas ante
   otra tarea. Contrastar transferencia con historia completa, solo OTHER,
   orden eliminado, identidades agrupadas y agente sin historia relacional.
   Igualar preformación, recursos, experiencia y oportunidades de actuación.
3. **RELATION-C, pendiente:** ruptura, reencuentro, historia contradictoria o
   incompleta, identidad nueva y límites de memoria/continuación. Ninguna
   reputación histórica equivale a ejecución o garantía presente.
4. **RELATION-D, pendiente:** fijar código, escenarios y umbrales antes de
   cohortes nuevas; ganancia por cohorte, costes completos, control causal
   de orden e identidad, auditoría independiente. Registrar también si el
   aprendiz amortiza la formación; INTERACTION no la amortizó en 480 rondas.

No se fijan todavía cifras de ventaja de B/D: falta implementar su dominio.
A no cambia la política ni acredita transferencia. `relation1_green=false`
en su informe y recibo, aunque A sea válida. Sigue habiendo 9/13 hitos software
cerrados, no 10/13. ROLES, INTEGRATE y RELEASE quedan después.

## Memoria A: recibos, no intenciones

Se añaden observadores a la sesión INTERACTION existente, sin copiar Agent.turn,
sin cambiar su Q/T/gate, física, incentivos privados ni canales públicos.
Cada observador solo recibe contexto y recibos WSP de OTHER, tick del encuentro,
su propio coste físico y su propia producción. Nunca recibe recursos, Q,
preferencias, incentivo privado ni recompensa ajenos. Tampoco propuestas,
predicciones o etiquetas «fiable/bueno/amigo» como hechos.

Después de liquidar ambas acciones y completar los recibos se reserva una
ranura CAM factual por episodio. El extracto es un recibo canónico validado,
no prosa generada. WSP16 usa YO/RECORDAR/OTRO/ANTES, domain 9, generator 8,
style 32/33 (bit alto del tick), slot 1/2 (contraparte) o 0 (no identificada),
seq = byte bajo del tick. E[6] permanece cero; no se coloca delta Q en E.
Los datos del recibo y los enlaces viven en el payload host existente de CAM,
sin ampliar WSP. No se empaquetan todas las acciones en un pensamiento de 16 B.

Enlaces al episodio anterior global y al anterior de la misma contraparte,
usando `CamSlot.see` y claves WSP en el extracto. Solo cabeceras escalares
acotadas fuera de CAM; no lista paralela de episodios ni otra tabla de política.
Los episodios sin identidad solo tienen enlace global: consultarlos juntos
no afirma que sus contrapartes sean la misma ni crea una relación ficticia.
Máximo 512 episodios y ticks 0..511 por observador. Los huecos son válidos
(una contraparte puede no estar activa); repetición, retroceso o wrap no.
Agotamiento CAM bloquea, sin borrar, sobrescribir ni caer en slot cero.

Un recibo ausente permanece ausente: no se convierte en WAIT ni aceptación.
Sin identidad se conserva historia sin atribución, nunca se añade a una
contraparte conocida. Una ejecución conjunta intentada no garantiza éxito:
se distinguen acciones concurrentes observadas, producción propia positiva y
resultados desconocidos. Solo se deriva éxito conjunto confirmado si hay
ambas ejecuciones UNIR observadas y producción propia positiva. Los resúmenes
son consultas derivadas, no nuevos hechos ni puntuaciones emocionales.

La validación del recibo corresponde exclusivamente a la física A heredada.
Un nuevo dominio B requerirá su propio contrato; A no generaliza leyes físicas.
Si falla la grabación tras ejecución, se conservan costes y la sesión se para:
no se promete rollback de física ni escritura atómica entre las dos CAM.

## Banco y requisitos A

- Semillas de desarrollo 113, 127, 139; 144 rondas, formación 96 y luego greedy,
  recursos 4096 por individuo, contrapartes y calendario balanceados como
  INTERACTION. Son desarrollo, no examen de transferencia.
- Mismas acciones, costes, predicciones y netos con y sin grabación relacional;
  mismo resultado al invertir orden. A solo añade memoria, no mejora conducta.
- 288 episodios por vida: 144 del aprendiz y 144 repartidos entre contrapartes.
  Comprobar orden global/por identidad, recuentos y suma exacta de costes propios.
- Reconstruir en CAM nuevas a partir exclusivamente de recibos observados;
  digest de episodios/enlaces independiente de direcciones de ranura CAM.
- Pruebas de identidad, observación parcial, ausencia, conflicto, gate, fallo
  parcial, capacidad, ticks 255/256, límites 512, corrupción y fuentes alteradas.
- Fijar fuentes antes de campaña; auditoría completa en proceso nuevo. La
  auditoría repite evidencia, no añade una cohorte nueva. Custodia de INTERACTION.

Sin LLM, Discord, hardware, web, commit, push o publicación HF. No integración
de CONTINUITY con la sesión social: el replay de historia no reanuda el agente
ni transfiere capacidad. METAVERSE-1 permanece último.
