# W+ · archivos WSP v1 · contrato 23/10/2026

Autorización: Nav pide completar 5.8/5.8.2, archivos `.wsp` que ECHO use y
ventajas medidas frente a JSON. Trabajo local independiente de W R1 verde / R2
tokens roja; esos resultados y R3 siguen cerrados. No API, LLM, instalaciones,
publicación, segundo bus ni modificación de módulos certificados.

## Formato fijado antes de medir

`ECHOWSP\0` (8 bytes), versión uint16 LE (=1), flags uint16 (=0), número de
postales uint32, longitud del descriptor uint32, longitud de metadatos uint32:
24 bytes de cabecera. A continuación descriptor JSON canónico UTF-8, tabla
contigua de paquetes originales (16*n bytes), lista JSON canónica de metadatos
de cada registro, SHA-256 binario de todo lo anterior (32 bytes). No padding,
sobrantes, compresión interna ni índices implícitos. `archivo.wsp.zlib` es una
compresión externa opcional del archivo completo, con límites al expandir.

Descriptor con exactamente `profile`, `provenance`, `metadata`. Perfiles v1:
`wsp16-session-v1` (postales opacas), `memx-replay-v1` (historial de Memory y
postales de reglas). El lector genérico no interpreta IDs como autoridad.
No validar E como int8 semántico en perfil opaco: algunos protocolos existentes
reutilizan campos; se conservan todos los bytes, también 0/255. Interpretación
de protocolo pertenece a su lector existente.

Orden = posición en tabla, nunca una marca temporal inventada. Metadatos JSON
preservan ausencia/null/false/0, cadenas, listas y números finitos; claves
duplicadas, NaN/inf, claves no string y profundidad >32 se rechazan.
Procedencia incluye ruta, hash de origen, clave del array y papel
original/enviado cuando existan. No se inventan emisores ni tiempos históricos.
SHA-256 detecta daño accidental, no autentica al emisor ni autoriza acciones.

Límites previos: archivo y expansión <=64 MiB, descriptor <=8 MiB,
metadatos <=32 MiB, registros <=100000, cada colección JSON <=100000 entradas,
cadenas UTF-8 válidas, tiempo/memoria acotados por esos límites. Escritura
exclusiva: no sobreescribir destinos. Error de magic/versión/flags/tamaño/hash,
truncamiento, estructura, perfil o cadena de Memory = rechazo.

## API e inspección

`Record(packet: bytes, metadata: dict)`, `Archive(profile, provenance, records,
metadata={})`, `encode/decode`, `write/read`, `to_json/from_json` y
`packet_at(blob,index)` (lectura selectiva: valida envoltura/hash/descriptor,
no interpreta el payload JSON de los registros). `verify` siempre decodifica
el archivo entero. JSON equivalente posicional:
`[1,profile,provenance,metadata,[[packet_hex,record_metadata],...]]`.
Hex es más compacto que la lista de 16 enteros para este control.

`export_memory` preserva límites, historial y hash de Memory y las postales
exactas que produce su API actual; `load_memory` reconstruye con `observe` y
comprueba historial/head/postales. No se atribuye origen histórico a postales
que se generan al exportar. `Agent(source=load_memory(path))` usa esa memoria.
Las reglas no adquieren autoridad externa por estar en disco.

CLI: `python3 -m echoai.echo58.wspfiles inspect|verify|import-json|export-json|
export-memory|use-memory`. `inspect` devuelve JSON para herramientas locales o
web; no se modifica la web existente en este estudio.

## Corpus y medidas fijados

Fuentes conocidas de desarrollo: todas las publicaciones de ronda 9 en
`lab/echo58/enjambre2/dev-20261022-r1/rounds/{honesto-none-m1,
prudente-false_safe-m1,oraculo-false_remote-m3}/r09.json`. Dos registros por
publicación, original y enviado, con todos sus demás campos intactos. No se
examina ningún examen ni se vuelve a ejecutar una campaña. Además memoria
de entrenamiento `lab/echo58/memx/memories/aprendida-m01.jsonl` completa.

Cuatro brazos equivalentes: WSP binario, JSON posicional compacto, ambos
comprimidos externamente con zlib nivel 9. Cada brazo transporta la misma
información; todas las cabeceras y hashes se cuentan. JSON añade un SHA-256
binario final para custodia equivalente; no se cobra un esquema externo a
ninguno. Informar también tamaño JSON sin recibo. No selección posterior de
codificación ni cambio del corpus buscando verde.

Medir bytes, encode, decode completo, lectura desde archivo+decode y lectura
selectiva desde archivo+hash de una postal. Nueve réplicas en orden rotado,
warm-up separado; guardar cada muestra wall/process ns y mediana/p95. Archivos
en caché del SO, sin afirmar cold I/O. Selectiva requiere para JSON parsear el
documento; no compara acceso a objetos ya decodificados. Acceso residente se
mide separado. No afirmar ventaja general de CPU por una sola operación.

Verde técnico = igualdad exacta 100%, rechazo adversarial, historial y
decisiones iguales. Utilidad: informar ahorro de bytes y tiempos por brazo;
considerar ventaja concreta si >=10% en al menos una métrica, conservando
todas las pérdidas frente al mejor control, sin reclamar tokens/inteligencia.
Integración: decisiones deterministas de Agent._decide sobre todas las claves
reales de la memoria, en observaciones de sonda construidas explícitamente;
no se llama a un mundo/examen ni se interpreta esto como score nuevo.

Auditor offline verifica fuentes archivadas/hashes, cuatro formatos,
igualdad, custodia, cálculos/todas las muestras y reconstrucción de Memory.
Diario factual propio observable; nunca se alimenta su texto al agente.

## Corrección de disponibilidad anterior a medir

La inspección de nombres reveló que honesto-m1 termina en r06 y prudente-
false_safe-m1 en r07: r09 no existe en ambos. Se fija **r01.json en los tres
casos** antes de generar corpus, tamaños o tiempos. Ninguna fuente de examen
se abre. No se seleccionan rondas por rendimiento; r01 existe para los tres.
