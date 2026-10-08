# HARNESS-1.5 · integración de desarrollo de ECHO-4.5

Contrato de integración, 29 septiembre 2026. `echo-nexus` **1.5.0 beta** es
el arnés público. HARNESS-1.5 no sustituye NEXUS-0, no añade un segundo diario
de pensamiento y no convierte el motor en un LLM. El código del motor y el
adaptador privado permanecen fuera del repositorio público.

Como el panel de un vehículo, muestra lo que el motor registra. El asesor
lingüístico puede explicar esos registros, pero su respuesta no es una nueva
observación del motor ni una orden que éste ejecute.

## Submódulos y condiciones de verde

| Submódulo | Qué hace | Verde solamente cuando |
| --- | --- | --- |
| **N15.1 · conexión HTTPS** | Normaliza el endpoint OpenRouter, consulta su catálogo público y conserva referencias de credenciales | Una petición real gratuita devuelve texto por HTTPS; un modelo retirado falla antes de la inferencia con una alternativa útil; no se muestra ni publica la clave |
| **N15.2 · editor y portapapeles** | Editor multilínea, Ctrl+V, F3 y `/copy last\|why\|session` | Pegar un documento no ejecuta los comandos que contiene; copiar devuelve texto limpio; se comprueba el envío multilínea |
| **N15.3 · mundo de sesión** | Ejecuta un proceso de desarrollo mientras el usuario conversa | Una instancia del actor supera dos episodios y mantiene su memoria entre ellos; chat/editor siguen disponibles; detener o salir termina el proceso |
| **N15.4 · procedencia** | `/echo` devuelve registros; `/ask` consulta al asesor con esos registros | Las respuestas tienen etiquetas distintas; los datos exclusivos del visor no entran en el contexto; ninguna respuesta modifica el motor |
| **N15.5 · distribución y documentación** | Paquete público, instalador con hash, guía y página beta | Pruebas, instalación publicada, capturas reales y página escritorio/móvil pasan; sólo el arnés es público; fuentes protegidas intactas |

Los controles automáticos usan fixtures para errores, credenciales, editor,
concurrencia y cierre de procesos. La comprobación de integración añade
peticiones reales gratuitas y dos episodios del mundo privado de desarrollo.
Son pruebas de integración, **no exámenes ARC ni pruebas de automejora S6**.

Un mundo continuo significa una sesión que repite episodios con el mismo
actor. No demuestra vida autónoma ilimitada, persistencia entre reinicios,
conversación simbólica propia ni selección verificada de las sugerencias del
LLM. Esas capacidades requieren contratos y exámenes distintos.

## Dependencias y estado de ECHO-4.5

S6 B1–B5 permanece obligatorio: ECHO debe superar SEMILLA, FIJO y SIN FILTRO,
conservar las habilidades y pasar la auditoría. No se abren ni cambian sus
fuentes congeladas para mejorar el arnés. EGO-MEMORIA-3E ya pasa M1–M6 en su
aldea; su transferencia ARC sigue pendiente. La versión beta del arnés no
es una publicación final de ECHO-4.5.

[Roadmap](ECHO45-ECHO5-ROADMAP.md) · [Guía del arnés](ECHO-NEXUS-HARNESS.md).
