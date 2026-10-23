# CRECE F2 v5 r1 · piloto completo, cierre técnico rojo

21/10/2026. **40/40 candidaturas terminadas. Puerta numérica de desarrollo
cumplida; auditoría estricta NO superada. Examen no ejecutado.**

Nav indicó al llegar a 38/40: «cuando acabes, no hagas el examen».
Se termina este piloto, se documenta el defecto y se detiene el trabajo.
F3 y F4 permanecen sin activar. No se cambia facturación.

## Resultado medido

Modelo único `openai/gpt-oss-120b` en Groq, temperatura 0, 2048 tokens/low.
Dos trayectorias de aprendizaje, cinco generaciones y siete brazos.
Las sondas usan 192 episodios por configuración, emparejados entre brazos
y generaciones; esos episodios no son 192 réplicas del aprendizaje.

| Brazo | g0 | g1 | g2 | g3 | g4 | g5 |
|---|---:|---:|---:|---:|---:|---:|
| crece | 142 | 142 | 136 | 132 | 132 | 132 |
| sin_fichas | 142 | 142 | 142 | 142 | 138 | 138 |
| sin_relevo | 142 | 130 | 130 | 130 | 131 | 131 |
| acepta_azar | 142 | 142 | 138 | 138 | 138 | 138 |
| azar_gramatica | 142 | 139 | 131 | 131 | 131 | 129 |
| piezas_b3 | 111 | 111 | 111 | 111 | 111 | 111 |
| sin_piezas | 142 | 142 | 142 | 142 | 142 | 142 |

Son fallos; menos es mejor. CRECE gana diez éxitos respecto a su inicio
(50→60/192). El daño agregado es 94 en todas las generaciones y brazos;
las sondas registran cero errores del enchufe.

La puerta escrita exige dos descensos estrictos consecutivos en la curva
**agregada**, que aparecen en g1→g2 y g2→g3. Las trayectorias individuales
son `73,73,67,67,67,67` y `69,69,69,65,65,65`: cada una mejora una sola vez.
No se observaron dos mejoras sucesivas dentro de una misma trayectoria.

CRECE termina con más fallos que gramática aleatoria (129), sin relevo
(131) y las cinco piezas humanas de B v3 (111). Estos datos descriptivos
no demuestran superioridad de CRECE ni significación estadística.

## Piezas y límites de interpretación

| Brazo generador | Candidaturas | Mecánica válida | Aceptadas |
|---|---:|---:|---:|
| crece | 10 | 6 | 2 |
| sin_fichas | 10 | 6 | 1 |
| sin_relevo | 10 | 10 | 3 |
| azar_gramatica | 10 | 10 | 4 |

Las dos aceptadas de CRECE son m1/g2 y m2/g3. La primera reproduce la regla
`no_repick` incluida en los ejemplos del prompt; la segunda es una variante
próxima que omite la igualdad del progreso anterior. No se demuestra
invención de un mecanismo nuevo. Ninguna se reescribió a mano para evaluarla.

El control sin fichas retira el conjunto de información de fallos; sin
relevo tampoco acumula piezas; acepta_azar sortea retrospectivamente dentro
de las candidaturas de CRECE. No aíslan todas las posibles causas de mejora.
V4 conserva su rojo; las diferencias entre versiones no se atribuyen solo
al modelo porque también cambió la presentación de la interfaz.

## Auditoría: defecto real de reanudación

El cierre automático archivó las doce fuentes exactas y los cinco protocolos,
verificó la base congelada y se detuvo en `attempt prompts identical`.
Se conservan el auditor y su fallo original. `results.json` mantiene su
`green=true` numérico; **no equivale a un cierre validado**.

Seis solicitudes cambian los bytes del prompt entre un 429 y su respuesta
200 posterior: m1/crece/g5, m1/sin_relevo/g4 y g5, m2/crece/g5,
m2/sin_relevo/g4 y g5. Las fichas recién construidas usaban el orden de
inserción de claves; al reanudar se cargaban del JSON guardado con claves
ordenadas. El prefijo, el sufijo y todos los datos observados son iguales.
La serialización final coincide exactamente con ordenar las claves de la
inicial. Sin embargo, el LLM recibe una secuencia de tokens diferente.

Una revisión independiente confirma ese alcance. El diagnóstico adicional
completa las otras comprobaciones de presupuestos, hashes, fichas, puertas,
campeones, sorteos y curvas, **manteniendo `audit_green=false`**. No se
flexibiliza la auditoría histórica para convertir el cierre en verde.
Los hashes de trazas tampoco permiten reconstruir trazas completas no guardadas.

## Servicio, persistencia y corrección posterior

30 propuestas con LLM: 30 respuestas HTTP 200/stop y once HTTP 429, en
41 intentos reservados de un máximo de 90. Cero cache hits y cero reservas
sin recibo. Uso registrado: 148492 tokens de llamadas nuevas. Se respetaron
los aplazamientos de cuota y se conservaron todos los intentos; no se
cambiaron modelo, permisos, límites de cuenta ni facturación.

La pieza aceptada m1/g2 se recargó previamente en dos procesos nuevos, sin
red ni acceso a claves, reproduciendo 288 pasos idénticos y cero errores
del enchufe en un mundo de desarrollo separado. Ambos episodios fallaron:
esto prueba persistencia, no éxito. No se incorporaron a las puntuaciones.

Después de archivar la corrida, se corrigió el código para futuras
ejecuciones: serialización determinista de fichas y recibos previos, e
identidad inmutable de modelo/prompt antes de cualquier envío. Una historia
sin esa identidad o un cambio de modelo/prompt bloquea la reanudación.
Los parámetros de API siguen protegidos por la congelación de fuentes del
experimento; no forman parte del nuevo documento de identidad.

Tres pruebas reprodujeron el defecto antes del arreglo; después pasan las
**64 pruebas técnicas** de CRECE y la revisión independiente pertinente.
Son pruebas de implementación: no reparan los prompts ya enviados, no
revalidan R1 y no constituyen un nuevo piloto ni un examen.

## Artefactos y cierre

- [Resultado crudo](../../lab/echo58/crece/f2-v5-r1-interface120b/results.json),
  [auditoría fallida y diagnóstico](../../lab/echo58/crece/f2-v5-r1-interface120b/audit.json).
- Figura revisada [PNG](../../lab/echo58/crece/f2-v5-r1-interface120b/reviewed-curves.png)
  y [SVG](../../lab/echo58/crece/f2-v5-r1-interface120b/reviewed-curves.svg),
  con ambos estados explícitos. Las figuras iniciales se preservan como
  historial; su título dependía solo de la puerta numérica y está sustituido
  por esta versión para presentar los resultados.
- En el mismo directorio: `source/`, `protocols/`, `audit-source/`,
  `post-close-review/`, `reload-check/`, recibos, candidaturas y snapshots.
- [Corrección prospectiva y pruebas](../../lab/echo58/crece/post-r1-request-identity/REPORT.md).

SHA-256 de `results.json`:
`9e40ba37b7d7c406a83190e47ae7b005a69f0ebd8ca86ba5688e432710ff0c8b`.

**Se entrega el piloto completo con su defecto registrado y se detiene.
No se inicia F3, no se repite R1 y no se abre el examen.**
