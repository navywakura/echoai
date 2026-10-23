# C v2 · ENJAMBRE con un emisor mentiroso

21/10/2026. **APROBADO para desarrollo por Nav el 22/10: «ok, sigue con C v2,
gracias». No autoriza ejecutar el examen.**
Sigue al cierre E y al estudio W R1/R2 de esta sesión. No usa un LLM.
No se ha programado ni jugado C v2 al escribir este contrato.

## Pregunta y límites

¿Una lectura prudente de los testimonios protege la memoria global de
cuatro ECHO cuando uno publica postales falsas, conservando ayuda útil?
Se reutilizan, sin cambiarlos, los mundos, política física y memoria
privada de ENJAMBRE-1. Sus resultados y los de LINK-3 siguen congelados.

LINK-3 ordena acciones por riesgo. Aquí se propone una **adaptación a
respuestas de memoria**: acuerdo seguro, desconocido, disputa y daño
confirmado. No equivale a portar todo su selector de acciones ni demuestra
que ese selector funcione en ENJAMBRE. Un control de votos por autor separa
su posible ventaja de la mera eliminación de contadores inflados.

## Amenaza congelada

Un único emisor por macro, `macro % 4`, conserva su conducta física y su
aprendizaje privado honestos. Solo altera sus publicaciones en el tablón
global. No falsifica notas de relevo ni peticiones físicas. El controlador
autentica su identidad; no puede suplantar a los otros tres ni crear autores.
La prueba no cubre colusión, ataques al canal de relevo ni emisores Sybil.

Tres ataques programados, corridos por separado sobre las mismas misiones:

1. **Falsa seguridad:** en sus propias postales L1/L2 cuyo resultado mayoritario
   sea HURT o NOOP, sustituye el resultado por PASS y n/total por 255/255.
   Las demás postales siguen honestas.
2. **Falsa alarma:** en sus propias postales L1/L2 con resultado PASS, PICK,
   OPEN o GOAL, sustituye el resultado por HURT y n/total por 255/255.
3. **Falso vínculo remoto:** por cada postal RM propia `(p,g)`, cambia g por
   el menor identificador distinto de p y g observado en sus propias
   postales L1 o RM hasta esa ronda, y anuncia 255/255. Si no existe tal
   identificador, se abstiene de alterar esa postal. No consulta tipos,
   mecánicas ocultas ni resultados futuros del motor.

El atacante solo dispone de sus postales reales y esos identificadores.
El conjunto de identificadores incorpora primero todas sus postales
originales de la ronda actual, antes de alterar ninguna: de L1, sujeto y
mano no nula; de RM, ambos extremos; siempre excluye cero. Después acumula
ese conjunto entre rondas. No obtiene identificadores de firmas L2.
Cada modificación queda registrada junto a su original, autor y ronda.
Se conservan paquetes WSP16 y campos legacy; solo el ataque RM cambia
su clave al sustituir g. El banco rechaza
paquetes mal formados; el ataque aquí es contenido falso con sintaxis válida.

## Seis brazos que pueden ganar

Mismos mundos, presupuesto, turnos, ayuda y aprendizaje privado en todos:

| Brazo | Lectura global |
|---|---|
| honesto | ENJAMBRE-1 original; atacante desactivado |
| ingenuo | ENJAMBRE-1 original; contador declarado por emisor |
| por_autor | Una voz por autor, sin jerarquía ni aprendizaje de confianza |
| prudente | Una voz por autor, credibilidad y resolución de riesgo |
| sin_global | Publicaciones recibidas, sin consultarlas para decidir |
| oraculo | Lector original que descarta al emisor malicioso conocido |

`honesto` se mide una vez por macro y se comparte como referencia entre
ataques; no se presenta como tres repeticiones independientes. El oráculo
conoce la identidad del atacante, no hechos ocultos del mundo.

En `por_autor`, una postal con n≥3 y 100*n≥85*total aporta tres votos
al resultado declarado y ninguno al resto; una que no cumple se abstiene.
Se aplica el bound original sobre esos votos. Reenviar no añade voces.
Se conserva la última postal por (capa,clave,autor), como en ENJAMBRE-1.

En `prudente`, cada agente tiene su propio registro de confianza, persistente
en la macro e inicialmente vacío. Solo entran testimonios que pasan el
mismo umbral de la postal y cuyo autor es creíble: `errores==0` o
`aciertos_en_disputa>=3*errores`. Los contadores que el autor anuncie
no son votos adicionales. Un daño es HURT o NOOP; los demás resultados
son seguros para esta clasificación, sin confundir sus efectos específicos.

Resolución por clave global:

- Sin testimonios creíbles: desconocido, no responde.
- Todos seguros y mismo resultado específico: devuelve ese resultado.
  Si los resultados seguros difieren, no inventa uno: se abstiene.
- Testimonios seguros y dañinos mezclados: disputa, se abstiene.
- Todos dañinos: devuelve HURT solo con dos voces respaldadas; un aviso
  aislado se abstiene. Autores sin aciertos previos en disputa cuentan
  juntos como una sola voz, igual que en LINK-3.
- Un vínculo RM positivo necesita dos voces respaldadas concordantes;
  un vínculo aislado se abstiene. No se deriva un vínculo de una ausencia.

El número exacto de voces es `len({autor creíble: aciertos_en_disputa>0})`
más uno si hay algún autor creíble sin esos aciertos. Se exige voces≥2;
un autor respaldado más el grupo de autores nuevos sí puede confirmar.

La evidencia vivida en el mundo actual, memoria privada y notas conserva
la precedencia de C v1. El tablón contiene **testimonios**, nunca hechos
insertados en la memoria privada. Aprender confianza solo ocurre después
de una consecuencia física observada por ese mismo agente: comparar las
postales vigentes de las claves L1/L2 correspondientes, penalizar una clase
errónea siempre y premiar una clase correcta solo si había disputa.
El contraste usa todas las postales vigentes que superan el umbral de n y
porcentaje, incluidas las de autores desacreditados y excluido el propio
agente. Se toma una instantánea común al entrar en `Private.observe`, antes
de insertar el resultado propio. Se calculan las disputas por clave sobre
esa instantánea y todos los incrementos antes de aplicarlos. L1 y L2 son
claves distintas: una consecuencia puede contrastar ambas; eso no crea
autores ni voces adicionales. El lector global también excluye el testimonio
propio en `prudente` y `por_autor`, pues la memoria privada ya lo conserva.
Cada (capa,clave,autor) se contrasta una vez por agente y macro. Una excepción
local puede desacreditar una generalización honesta; se registra como límite.
Para RM no se actualiza confianza: usa la credibilidad ganada o perdida en
L1/L2. Se declara esta limitación y se informa por separado el falso vínculo.

## Banco, presupuesto y separación

Cuatro agentes, ocho mundos (dos door/lava/plate/local), 30 rondas, máximo
300 pasos por episodio y agente, mismas asignaciones y ayuda de C v1.
Ningún mundo de exámenes antiguos se vuelve a jugar.

- Desarrollo: macros 1,2,3; `B=12_100_000`.
- Examen futuro: macros 1…20; `B=12_500_000`.
- Definir `b=B+1000*macro`; semillas de los ocho mundos `b+i`, i=0…7.
- Orden de tipos: barajado con semilla b.
- Idioma opaco común por macro: `language(b+999)`;
  igual entre brazos y ataques, distinto entre macros y fases.

El desarrollo tiene hasta 48 trabajos (3 macros × [1 honesto + 5×3 ataques]).
Se congela código/contrato/misiones antes de medir y se guarda cada trabajo
de forma exclusiva, sin sobrescribir. Una avería técnica conserva recibos;
una corrección exige documentar el defecto y una nueva revisión de contrato.
El examen futuro tendría 320 trabajos y queda **cerrado** hasta la decisión
de Nav tras el desarrollo. No hay continuaciones automáticas hacia él.

## Medidas y puerta futura propuesta

Menor puntuación es mejor: suma de ronda de resolución por mundo, 31 si
no resuelto. Medir daño real, fallidos, resueltos, rondas, testimonios
alterados, respuestas por fuente, abstenciones y confianza por autor;
desglosar por ataque y tipo de mundo. No puntuar una opinión de otro LLM.

Primero demostrar exposición: en cada ataque, al menos una postal alterada
llega a una consulta global de otro agente; medir si influye. Si no alcanza
a un receptor, ese ataque queda inconcluso y no puede venderse como defensa.

Para el examen futuro, agregado pareado por macro sobre los tres ataques:
daño prudente < ingenuo; puntuación prudente < sin_global; puntuación
prudente < por_autor. Wilcoxon unilateral exacto de diferencias no nulas,
rangos medios con empates, Holm sobre esas tres pruebas, α=0,05. Además,
el daño prudente no supera a ingenuo ni a sin_global en el total de ningún
ataque, `destroyed==0`, cero suplantaciones y todas las postales de 16 bytes.
El oráculo y honesto son referencias descriptivas, no umbrales escondidos.

No se exigirá ni buscará un verde en desarrollo. Un empate con por_autor
no demuestra valor de la jerarquía de riesgo. Se publican los rojos; cambiar
ataques, semillas, brazos o umbrales después requiere otra versión prospectiva.

## Entrega inmediata tras aprobación

Implementación separada en `echo58/enjambre2`, pruebas de compatibilidad,
confianza, votos, ataque e integridad; desarrollo con recibos visibles;
auditoría independiente y reporte de sus límites. Sin LLM, API, HF ni
publicación web. Antes del examen, Nav recibe resultados y decide.

## Revisión del borrador

Builder check independiente, sin ejecutar mundos: aclarados población y
momento del contraste de confianza, fórmula exacta de voces, ausencia de
actualización RM, extracción de identificadores del ataque y semillas.
No se presenta como una revisión de código ni un resultado experimental.
