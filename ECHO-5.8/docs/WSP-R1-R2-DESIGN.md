# W · compatibilidad y compresión justa, R1/R2

21/10/2026. **APROBADO por Nav en esta sesión: «Si apruebo todo ejecutar
W r1/r2».** Desarrolla
el roadmap WSP del 17/10 sin cambiar su objetivo ni abrir una campaña ARC.
La autorización de trabajar W existe; este documento concreta qué se medirá.

## Pregunta y alcance

¿Un adaptador textual de WSP conserva exactamente la observación pública y
ahorra al menos 15 % de tokens frente al mejor control JSON equivalente?
Se estudia coste de representación, no inteligencia, score ni decisiones.
R3 (ARC pareado) no se activa por este contrato, aunque R2 pase.

Se conserva el WSP legacy de 16 bytes y sus IDs. No se cambia navi10_wsp,
NEXUS-0, CAM, gate, el paquete RogexWSP ni un experimento congelado. El
adaptador vive en echo58/wspstudy y no ejecuta acciones ni escribe hechos.
El payload geométrico adicional es un contenedor de observaciones, no un
segundo bus cognitivo ni una afirmación de que un frame cabe en 16 bytes.

## Corpus y separación

Solo copias locales de tres grabaciones **públicas de terceros**, conservadas
desde el 17/10 en el worktree histórico echoai-pcworld1/ECHO-5.5/artifacts/replays.
No se juega ningún entorno ni se leen soluciones privadas del motor.

- Calibración del formato: primeras 64 filas de bp35-recording.jsonl.
- Evaluación separada por juego: primeras 64 filas de s5i5-recording.jsonl
  y primeras 64 de sp80-recording.jsonl. Ningún ajuste tras sus mediciones.
- Antes de implementar solo se inspeccionaron nombres de campos y forma
  de los dos primeros registros de cada archivo. No se midieron codecs ni
  tokens. Son observaciones históricas conocidas, no juegos ciegos nuevos.
- Fijar hashes de las tres grabaciones y del corpus seleccionado antes del
  benchmark. Los archivos de origen solo se leen.

Cada registro conserva: game_id, índice, state, levels_completed, win_levels,
full_reset, available_actions, action_input.id y action_input.data, y **todos
los píxeles de todas las capas** de frame. Se excluyen por igual en todos los
brazos timestamp, guid y action_input.reasoning (prosa del modelo, no una
observación del mundo); sus fuentes permanecen en el manifiesto histórico.
Ausencia, null, false y cero son distintos. No se borran HUD ni objetos finos.

No se mezclan extracción de objetos, percepción semántica ni reducción de
resolución con la comparación de codecs. No se mide el segundo estudio de
percepción del roadmap mediante este contrato.

## Formatos congelados antes de evaluar

Un registro normalizado tiene una postal WSP legacy y el payload público
anterior. La postal identifica una observación con src=YO, rel=OBSERVAR,
dst=AQUI, time=AHORA; E y extensiones a cero salvo seq=índice (0…63).
Estos son IDs existentes, no categorías nuevas. La postal completa también
viaja en los controles; un bit recibido nunca concede autoridad.

Se admite exactamente la misma geometría en todos los formatos: valores
planos, RLE de pares (valor, longitud), y delta de pares (índice, valor) sobre
el frame anterior del mismo juego/forma. Tamaños se transmiten; un delta
incluye el SHA-256 canónico de su base. Ante reset, cambio de dimensiones o
ausencia de base se usa un frame completo. Cada emisor puede elegir el modo
de menor coste tokenizado entre esos tres, contando su etiqueta de modo.
La elección algorítmica por registro es idéntica para ambos lenguajes.

Controles JSON, todos compactos y lossless:

1. Objeto con nombres de campos.
2. Array posicional con el mismo orden compartido.
3. Los anteriores con RLE/delta y los mismos datos de base.
4. Envoltura JSON de la cadena WSP completa como control fuerte de coste de
   sintaxis. Comparte el parser del payload y cuenta su leyenda: no se
   presenta como un decodificador JSON sin adaptador.

Candidato WSP textual: versión `W1`, postal representada por sus 16 valores
enteros en orden legacy, feedback posicional JSON y geometría con etiqueta,
dimensiones y payload JSON compacto; separadores exteriores `|`. El parser
lee versión y postal hasta sus delimitadores, después consume un valor JSON
completo de feedback, exige un `|` y consume la geometría JSON completa,
sin aceptar sobrantes. Un `|` dentro de una cadena JSON no es separador.
El esquema
versionado se cobra como leyenda. No se usa el parser permisivo de RogexWSP
para ignorar geometría desconocida ni se redondean valores.

La comparación principal elige por juego el control JSON de menor coste
total entre **los controles fijados**, con su leyenda. No se combinan
gratuitamente controles distintos por mensaje; los modos raw/RLE/delta
sí llevan su selector y se permiten en todos. No se afirma optimalidad sobre
todas las codificaciones JSON concebibles. El control de envoltura puede
ganar; si impide el 15 %, se conserva el rojo sin retirarlo después.

## R1 · compatibilidad y validación

Validar roundtrip exacto de registros y bytes de postal, incluidos ±100,
0/255, ausencia/null/0/false, geometría multicapa y cambios de forma. Rechazar
bool como entero, valores fuera de rango, NaN/inf, tamaños inconsistentes,
RLE o deltas inválidos, namespaces/versiones desconocidos, claves JSON
duplicadas y contenido sobrante. Límites: 64 capas/imágenes, 128×128 por capa,
colores enteros 0…255, mensaje de hasta 4 MiB.

Usar los pack/unpack existentes solo después de validar: su comportamiento
legacy de clamp/wrap no es una validación de entrada. No se modifica.
La identidad de base/índice/contexto se comprueba al aplicar delta; replay,
cambio de contexto o checksum falso se rechazan. Una postal que se declare
verificada sigue siendo datos sin autoridad; el adaptador no contiene una
operación de actuar o de incorporar un hecho.

## R2 · medidas, coste y puerta

Tokenizador local Qwen2.5-Coder-32B-Instruct ya usado en R0, tokenizer.json
SHA-256 c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539.
Fijar versión instalada de tokenizers, sin inferencia, chat template ni API.
Se carga solo el tokenizador, no los pesos de un LLM.

Cada juego empieza sin estado de geometría. Se cobra su leyenda completa
una vez y la primera transmisión completa. Totales incluyen todas las
leyendas, datos de base, cabeceras, delimitadores y contenido. Para mediana
por registro se amortiza la leyenda por igual entre sus 64 mensajes; informar
también sin amortizar, totales y peor primer mensaje.

Medidas: tokens exactos totales/mediana/p95, bytes UTF-8, tiempo CPU de
codificar/decodificar (descriptivo, cinco repeticiones locales), fallos de
parseo, porcentaje de feedback y frame reconstruidos. Guardar cada mensaje,
SHA-256 de registro, tamaño y score; verificador separado recalcula tokens
y roundtrips desde los mensajes guardados, sin volver a ejecutar un juego.

Puerta R2: R1 completa, 100 % de roundtrips sin pérdida ni fallos de custodia;
ahorro mediano **≥15 %** y ahorro de tokens total **≥15 %** frente al mejor
control JSON, sin aumento de tokens totales en ninguno de los dos juegos
de evaluación. Los cocientes se deciden con enteros, sin redondear.
Precisamente: para cada registro i del juego g, n=64, W_i y J_i son tokens
de mensaje y L_W/L_J los de sus respectivas leyendas. Se calcula
`s_i = ((64*J_i + L_J) - (64*W_i + L_W)) / (64*J_i + L_J)`.
La mediana es la de esos **128 ahorros relativos** de ambos juegos juntos;
para número par es la media exacta de los dos centrales. Se exige ≥3/20.
El ahorro total usa la suma conjunta de tokens de los dos juegos, cada uno
con su leyenda una vez, y exige igualmente ≥3/20. Además W_total≤J_total
en cada juego. No se usa el cociente de medianas de tamaños de mensajes.
El 15 % es umbral de utilidad previo, no una predicción. No se exige una
prueba estadística: hay solo dos juegos de evaluación y se reportan ambos.

Si no pasa, W R2 queda roja y se recomienda el formato más simple/económico.
No se prueban nuevos alfabetos ni se quitan controles buscando verde; no
se abre R3 ni se repite el estudio con cambios no registrados.

## Entrega y custodia

Código/fixtures/tests independientes, contrato y fuentes congelados antes
de evaluar; manifiesto de corpus y dependencias, mensajes, resultados,
auditoría y figuras en lab/echo58/wspstudy. Desarrollo visible mediante
registros de hechos; la evaluación del codec solo lee el corpus fijado.
No publicación, HF, GPU ni uso de claves. La publicación de todo 5.8 sigue
aplazada por Nav.

## Enmienda técnica previa a cualquier medición de tokens

La preparación inicial encontró en BP35, índice 10, 25 imágenes; el prefijo
fijo completo contiene hasta 47. La cota inicial de ocho era una suposición
incorrecta del adaptador. Se amplía a 64 imágenes en todos los formatos y
sus leyendas, conservando íntegros los registros y sus píxeles. No cambian
corpus, modos, controles, umbral del 15 % ni separación por juego. La primera
preparación fallida se conserva en `w-r1r2-20261021-r1`, con cero mediciones
de tokens y sin preflight completado; la preparación corregida será `r2`.
Se añade una prueba de 64 imágenes lossless y rechazo de 65 antes de medir.
Esta corrección de cobertura no se presenta como mejora de compresión.
