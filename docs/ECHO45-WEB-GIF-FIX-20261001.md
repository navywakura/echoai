# Corrección de rutas de la galería de GIFs

2026-10-01. Repositorio oficial local: `/home/user/rxlabs.org_local`.
Sitio oficial: `https://www.rxlabs.org`.

Se reproduce un fallo en la galería de capacidad al abrir su ruta sin barra
final, como puede ocurrir con `cleanUrls` de Vercel. Un enlace relativo
`operations/sym_h.gif` se resuelve como
`/media/echoai/operations/sym_h.gif`, fuera de la carpeta de la galería.
Los enlaces de imágenes, animaciones y descargas estaban afectados.

El commit preparado `8e7292c033dc777eeec2f1b54b046530a59916e1`, sobre
`6787d0e4526da558f0f51d0e65ebc6702c9aa051`, fija una etiqueta `base` con la
ruta pública de la galería durante la sincronización previa a la compilación.
Así se conserva la ruta correcta al abrir `index.html`, `index`, la carpeta
sin barra o con barra. Esta preparación vuelve a aplicarse al regenerar
la galería y mantiene correcto el SHA-256 de su HTML en el manifiesto.
Los bytes de los GIFs y los resultados experimentales se conservan.

Las pruebas reprodujeron dos fallos antes de la corrección. Después pasan
6/6: cuatro variantes de URL, controles reales de reproducción/pausa y
selección ejecutados con un DOM simulado, y el manifiesto completo. La
compilación pasa y genera 114 rutas. Se decodificaron los 92 GIFs y sus
2.576 fotogramas completos, sin corrupción. Un fotograma se inspeccionó
visualmente. La comprobación en un navegador real y en producción queda
pendiente por las restricciones de acceso de esta sesión.

La reparación se preparó en `/tmp/rxlabs-capacity-publication-20261001`.
El repositorio original permanece intacto: esta sesión solo permite escribir
en ECHO y `/tmp`, y las escrituras del conector GitHub requieren aprobación
con una política `never`. Las consultas al sitio tampoco han permitido
verificar la versión pública: la terminal no resuelve su dominio, el lector
web no accede a estas páginas y Vercel no reconoce la URL en su conexión.
Por ello no se declara que el cambio esté desplegado.

El [paquete Git](../lab/publication/rxlabs-gif-fix-20261001.bundle) conserva
el commit; su [recibo](../lab/publication/rxlabs-gif-fix-20261001.json)
contiene las comprobaciones y SHA-256. Ejecutar desde la terminal del dueño:

```bash
bash /home/user/REALRXOS/RXos/echoai/lab/publication/publish-rxlabs-gif-fix-20261001.sh
```

El script comprueba hashes, remoto y estado de las ramas, aplica el commit
por fast-forward, compila, ejecuta `npm run test:gallery` y hace un push
normal. El despliegue posterior corresponde a la integración GitHub–Vercel.
Si la rama ha avanzado, se detiene para preservar ese trabajo.
