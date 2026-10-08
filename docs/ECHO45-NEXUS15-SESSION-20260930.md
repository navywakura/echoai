# ECHO-4.5 · integración de echo-nexus 1.5

Comprobación: 30 septiembre 2026, 00:32 CEST. Esta entrega cierra
HARNESS-1.5; no declara terminado S6 ni ECHO-4.5.

## Publicación verificada

- Arnés público: commit `b3d5840`, release beta
  [v1.5.0](https://github.com/navywakura/echo-nexus/releases/tag/v1.5.0).
- Web: commit `48f4b52`; Vercel confirma el despliegue. La copia de
  `rxlabs.org_local` coincide y conserva sus capturas locales previas.
- [Página](https://www.rxlabs.org/echo-nexus): herramienta beta para
  desarrolladores voluntarios, dos apartados principales, captura real.
  La imagen Open Graph aparece sólo en metadatos. Guías ES/EN/CA.
- Paquete instalado: `echo-nexus --version` devuelve `1.5.0`.
  Conexión inicial guardada: `openrouter`, HTTPS y `openrouter/free`.
  La respuesta real desde el paquete instalado tardó 3,37 segundos.
  Qwen local y el perfil `openrouter-fast` permanecen disponibles.
- Se verificaron 24 pruebas del arnés, editor/copia, chat concurrente con
  tres episodios de desarrollo y procedencia de los registros.
  [Criterios y evidencia](ECHO45-HARNESS15-RESULTS.md).

El 404 observado correspondía a `google/gemma-3-4b-it:free`, retirado del
catálogo. Se comprueba el catálogo antes de conectar. La API puede devolver
429 temporalmente; se muestra el plazo y no se cambia a un modelo de pago.
La clave queda referenciada por archivo, sin publicarse ni copiarse en perfiles.

## Estado científico

- HARNESS-1.5: **VERDE**, N15.1–N15.5; herramienta de integración beta.
- EGO-MEMORIA-3E: **VERDE en la aldea**, M1–M6; transferencia ARC pendiente.
- S6-B11: **pendiente**. Piloto ECHO 1129, FIJO 1108, tres mejoras ECHO
  aceptadas. Auditoría independiente en curso; reserva todavía sin abrir.
  El aumento de 21 niveles corresponde al desarrollo del piloto y no a una
  puntuación ARC oficial.
- Fuentes protegidas: 190 intactas; ningún candidato de comparación final
  disponible todavía. NEXUS-0 conserva su ejecución sin LLM.

La sesión del arnés usa un adaptador parcial de componentes; no certifica
la integración de todas las capacidades de ECHO-4.5. `/echo` informa de
registros reales sin modelo; `/ask` consulta al asesor y no devuelve su
respuesta al motor. No se fabrica un monólogo interno.

## Procesos que continúan

`echoai-s6b11.service` conserva el encadenamiento autorizado:
auditoría del piloto → campaña → auditoría de campaña → examen reservado
de cuatro brazos → auditoría final, avanzando sólo si pasa cada requisito.
La primera auditoría se reanudó tras crear un directorio de salida faltante;
se preservó el fallo y no se cambió el experimento congelado.

`echoai-s6b11-publication.service` espera el cierre y publica sus recibos.
Sólo declara S6 verde con promoción del piloto y campaña, B1–B5 completos,
auditoría válida y fuentes intactas. También publica un cierre negativo como
negativo. [Reglas de publicación](ECHO45-S6-B11-PUBLICATION.md).

Para cerrar ECHO-4.5 faltan S6, la transferencia/integración de memoria y
las comparaciones ARC con presupuestos iguales. Permanecen vigentes las
referencias históricas; no se han publicado nuevas puntuaciones oficiales.
