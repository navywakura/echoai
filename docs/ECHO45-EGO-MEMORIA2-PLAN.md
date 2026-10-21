# EGO-MEMORIA-2 · desarrollo posterior a los límites de la aldea inicial

2026-09-28. Implementación autorizada por Nav: completar los pendientes de
ECHO-4.5. La aldea inicial y sus ocho resultados se conservan. No se modifica
ninguna fuente de S6-B4 ni se abre su examen.

La primera aldea devuelve también la utilidad de acciones no ejecutadas;
además comprobar una mentira ahorra turnos incluso sin deudas. Sus ventanas
tienen muy pocos contactos con mentirosos y algunas empiezan en el techo.
Eso impide aislar adecuadamente M5 y hace frágil M1. Esta segunda aldea es un
experimento distinto, con las mismas preguntas funcionales M1–M6; sus cifras
no reemplazan los resultados anteriores.

Los cinco interlocutores se presentan con frecuencia equilibrada. ECHO
elige entre actuar o verificar y entre escribir o no. Verificar obtiene un
recibo que permite demostrar después qué dijo el interlocutor; guardar ese
recibo cuesta un turno. El diario es la única fuente de información histórica
para responder reclamaciones o calcular confianza. La memoria de trabajo se
borra entre episodios; los valores enteros de acciones conservan aprendizaje.
No se entrega la etiqueta de mentiroso ni la verdad de una reclamación al
controlador. No hay instrucciones para documentar ni premios por escribir.

En esta condición verificar cuesta siete turnos; andar correctamente cuesta
tres y una pista falsa sin verificar cuesta nueve. Por tanto la verificación
de una pista falsa cuesta diez y no compensa por sí sola. La reclamación
posterior cuesta doce: solo un recibo verificado y conservado permite evitar
una reclamación falsa. Este cambio de costes se declara antes del desarrollo
para separar el valor futuro de la utilidad inmediata. No se afirma que
represente todos los mundos ni que sea integración del núcleo NEXUS-0.

El controlador aprende el retorno observado de cuatro acciones compuestas
(actuar/verificar × escribir/omitir), condicionado por el signo de confianza
obtenido del diario. Cada coste posterior se asigna a la acción realmente
ejecutada que lo originó; no se enseña el resultado de acciones alternativas.
El registro de crédito contiene solo contexto/acción, nunca pistas o pruebas,
y no puede contestar reclamaciones. Los mundos emparejados tienen idénticas
pistas y contactos aunque cambie la conducta; las reclamaciones tienen un
generador aleatorio independiente.

Primero desarrollo en semillas 1–8: 2400 episodios, primera ventana 80 y última
400, exploración 100/1000, dos mundos con y sin deudas y controles sin diario,
sin verificación y ablaciones de recuerdos. Inspeccionar tamaños de muestra,
costes, estabilidad, cadena de pruebas y diferencias causales. Cada intento
de desarrollo se conserva. M1/M5 deberán comparar crecimiento con el mundo
sin deudas, no solo una subida en el mundo principal. M2 incluye reclamaciones
y errores repetidos; M3 exige ablación selectiva frente a la misma cantidad
de recuerdos de otro agente; M4 requiere clones iniciales iguales y políticas
congeladas estables, con evidencia del diario; M6 exige replay exacto.

Antes de cualquier examen se redactará el contrato D con umbrales numéricos,
se congelarán fuentes y cohortes nuevas, y se ejecutará una auditoría en otro
proceso. Un desarrollo positivo no certifica el examen. Sin LLM, todo CPU y
coste de pago cero. Observabilidad usa el diario y visor ya existentes;
ningún texto del visor entra al controlador.

[Contrato original](ECHO45-EGO-MEMORIA1-DESIGN.md) ·
[Roadmap](ECHO45-ECHO5-ROADMAP.md).
