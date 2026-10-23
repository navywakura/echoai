# W · control de JSON más compacto · plan previo, 23/10/2026

Add-on de ingeniería separado de WSPFILES y de C3. Los cuatro Archives y
sus resultados anteriores ya fueron vistos: esta comparación es **post hoc,
descriptiva**, no una muestra nueva ni un examen. El ahorro ~18% anterior
corresponde al JSON posicional con hex32 por paquete; no equivale a superar
el mejor JSON. No se cambia W/R2, su puerta, sus fuentes ni artefactos.

## Corpus fijo y representaciones antes de medir

Exactamente los cuatro `.wsp` de
`lab/echo58/wspfiles/20261023-r1/artifacts/`, en orden de nombre:
honesto-none-m1, memory-training-m01, oraculo-false_remote-m3,
prudente-false_safe-m1. También se conservan como controles los cuatro
`.wsp.zlib` originales. Sus hashes se fijan desde manifest.json antes de
cualquier codificación nueva. No añadir ni quitar casos según tamaños.

Tres JSON canónicos UTF-8, sin espacios, diccionarios con claves ordenadas;
los arrays posicionales evitan nombres repetidos. La versión es el entero1.
Se decodifica cada layout por su identificador de brazo explícito:

1. `b64-rows`: `[1,profile,provenance,metadata,[[base64(packet16),record_metadata],...]]`.
2. `b64-columns`: `[1,profile,provenance,metadata,base64(packet16_0||...||packet16_N),[record_metadata,...]]`.
3. Control adicional fijado ahora, `b85-columns`: idéntico al segundo,
   usando base85 estándar Python b85encode/b85decode sin padding por paquete.
   Se informa junto a los anteriores, sin seleccionar solo el que favorezca WSP.

Base64 RFC4648 estándar, con padding canónico; base85 debe recodificar a la
misma cadena exacta. El bloque columnar debe tener16N bytes y el array de
metadatos exactamenteN objetos. Se deriva N del bloque, sin inventar campos.
Se conservan exactamente perfil, provenance, metadata de archivo, cada uno
de los16 bytes por paquete y cada objeto de metadatos por registro, con tipos
JSON. No se suprimen cadenas, historial, campos repetidos ni información.

## Medidas simétricas y puerta técnica

Para cada uno de los cuatro casos, publicar todos los tamaños:

- Payload WSP original sin sus32 bytes SHA y payload JSON sin recibo.
- Archivo completo: payload + SHA256 binario de32 bytes en ambos formatos.
  El SHA detecta corrupción; no autentica al emisor.
- zlib nivel9 tanto del payload como del archivo completo, con mismo runtime.
  El archivo WSP completo comprimido se compara con el `.wsp.zlib` original;
  se exige igualdad de recomprimirlo con el runtime actual. Si no coincide,
  se publican ambos controles y la diferencia de runtime, sin descartar ninguno.

La ventaja WSP se define `100*(bytes_JSON-bytes_WSP)/bytes_JSON`; un número
negativo significa que gana JSON. Se muestran los cuatro casos completos y
la suma de tamaños; no se escoge media/mediana ni representación tras verlos.
No hay umbral de ahorro ni intento de recolorear una pista anterior.

Puerta técnica: cada decode devuelve exactamente el Archive original,
verificado también como igualdad byte a byte de `wspfiles.codec.encode` con
el `.wsp` original. Esto conserva tipos JSON, incluidos bool/int y float/int.
Se prueba rechazo de checksum alterado, truncación/sobrantes, versión/perfil,
esquema/tipos, JSON ambiguo/no finito/UTF-8, alfabetos/padding no canónicos,
longitudes de paquete/bloque y desajuste de metadatos, expansión zlib y
sobrescritura. Pruebas adversariales pequeñas, sin buffers enormes.

No se miden tiempos: no se infiere latencia, acceso selectivo ni superioridad
universal de formato a partir de tamaños. No modelos, red, APIs, mundos,
agentes, dependencias ni instalaciones. Se importa solo el codec stdlib
existente, sin modificarlo ni llamar a integración/Agent/Memory.

## Custodia, recursos y revisión

Implementación nueva `echo58/wspstrongjson/`, tests nuevos y esta agenda.
Fixtures se pueden implementar antes de revisión; el corpus real no se
recodifica ni mide hasta revisión del coordinador. Antes de medir se archivan
fuentes, tests, plan y hashes de los ocho controles originales + manifiesto.
Artefactos nuevos exclusivos: `lab/echo58/wspstrongjson/20261023-r1/`.
Se guardan tamaños, bytes generados, hashes y resultados íntegros. Auditoría
en proceso nuevo reconstruye representaciones y métricas, comprueba hashes,
igualdad exacta y los cuatro casos; no ejecuta un modelo ni el estudio W previo.

Cualquier ejecución potencialmente >1s (tests/medición/auditoría) va en su
unidad user: CPUQuota25%, MemoryMax256M, MemoryHigh192M, MemorySwapMax0,
TasksMax16, Nice10 y threads OMP/OpenBLAS/MKL/NumExpr=1. Es trabajo ligero,
separado de los vuelos pesados P y sin tomar su turno de simulación. No tocar
roadmap/handoff global ni los archivos/artefactos W originales. La utilidad
cuantitativa se decide por los resultados, incluyendo cualquier victoria JSON.
