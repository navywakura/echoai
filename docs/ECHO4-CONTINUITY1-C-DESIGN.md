# CONT-C — procedencia, cuerpos y ramas

2026-09-22. Contrato de desarrollo escrito antes del código y del banco.
No modifica fuentes selladas SELF/CONT-A/B. No concede `continuity1_green`.

## Cuatro operaciones distintas

Perfil inicial: envolver checkpoints CONT-B de los agentes originales
SelfRecoveryAgent/SelfReuseAgent. CONT-A sigue disponible, no se convierte
silenciosamente. Metadatos de custodia, nunca un segundo bus ni entrada LLM.

- Reanudar: misma identidad, cuerpo, rama, relojes, permisos y estado exacto.
- Bifurcar: dos copias virtuales independientes del mismo punto, con ramas
  distintas y origen común. Conservan el diagnóstico y el cuerpo simulado
  copiado, no certifican un nuevo cuerpo físico. La historia previa es común;
  sus nuevas acciones/recibos no pueden intercambiarse entre ramas.
- Nuevo cuerpo: misma identidad administrativa y rama, nueva etiqueta de
  cuerpo y época. Conserva memoria aprendida y reloj global; empieza otra
  vida local. No es reanudación ni reparación autónoma.
- Descendiente: nueva identidad, rama y cuerpo, generación incrementada;
  hereda memoria aprendida, no los turnos vividos ni los permisos del padre.

Identidad = etiquetas explícitas del custodio y una rama derivada de hashes;
no se infiere de WSP iguales. Copias de un checkpoint pueden coexistir: no
se promete exclusividad distribuida, anti-rollback ni una identidad subjetiva.
El custodio gestiona qué proceso usa cada cuerpo real; aquí solo software.

## Herencia y revocación

Nuevo cuerpo/descendiente copian la única CAM, Q y restos, T/inverso y
PATTERN/contextos aprendidos. Son experiencia heredada, no observaciones
nuevas del receptor. No se borran hechos del origen ni ranuras CAM.
Se reinician ventana sensorial, predicciones, contexto del turno, BOUNDARY,
referencia SELF, diagnóstico, recibos, recuperación y permisos de ensayo.
El origen queda intacto y su hash identifica la evidencia revocada.

El receptor queda en **cuarentena**: no puede elegir sondas diagnósticas,
autorizar recuperación ni actuar hasta una recalibración nominal supervisada
con 16 pares públicos (ocho por acción), recibo nominal y ámbito correcto.
Después requiere una sesión SELF nueva y confirmada antes del control.
La calibración no transfiere diagnóstico por semejanza sensorial y no enseña
T/PATTERN gratuitamente. Si el cuerpo no admite el prior, falla o se abstiene.

Cada recibo nuevo se vincula al hash de identidad/cuerpo/época/rama.
Un recibo del padre, de un cuerpo anterior o de una hermana se rechaza aunque
sus bytes WSP y token coincidan. El vínculo lo atestigua un custodio confiable:
no autentica por sí mismo un sensor ni impide que ese custodio mienta.
Bifurcar con plan pendiente o recibo en buzón se rechaza: terminar o cancelar
antes, para no duplicar trabajo externo pendiente.

Un individuo terminal puede reanudarse/bifurcarse solo como terminal. No
admite cambio de cuerpo para revivirlo; sí un descendiente explícito separado.
Las nuevas reservas del cuerpo se registran como asignación externa, no como
recompensa, aprendizaje o recurso creado por el agente.

## Custodia y pruebas prospectivas

JSON cerrado, digest externo, fuentes fijadas y publicación sin reemplazo.
Reutilizar codecs/validadores A/B. Cadena limitada a 32 enlaces, referencias
compartidas dentro de cada agente, ninguna memoria mutable entre ramas.
Serializar cuarentena, recalibración y ejecución activa; validación de la
recalibración mediante reconstrucción de las entradas públicas guardadas.

Banco antes de CONT-D: reanudar diagnóstico/recuperación/reutilización;
bifurcar y comprobar igualdad bajo entradas iguales, divergencia observada
bajo acciones permitidas distintas y aislamiento del origen/hermanas;
cambiar cuerpo y crear descendiente desde agentes recovery y reuse;
cuarentena, recalibración, nueva confirmación y turnos nativos; testigos
terminales. Comprobar memoria heredada exacta, relojes global/local, asignación
externa, revocación y ausencia de trasplante de recibos entre ámbitos.

Mutantes: identidad, rama, época, generación, parent hash, cuarentena falsa,
calibración ausente/manipulada, tokens y campos desconocidos, corrupción,
cadena excesiva. Proceso nuevo y replay reconstructivo desde recetas; nunca
confiar solo en un booleano de aprobación del informe. Integridad y regresiones
A/B/SELF/núcleo. Registrar costes de calibración y sondas aparte de los turnos.

El banco de desarrollo de CONT-C no es el examen A/B/C nuevo de CONT-D.
DREAM permanece PLAN; hardware después del software, METAVERSE-1 último.
