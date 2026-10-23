# ECHO-4 — marca, novedades públicas y separación del legado

2026-09-22. Entrega de presentación y organización, **sin cambios al agente,
al núcleo ni a los archivos sellados de los experimentos**.

## Marca

Original aportado por el responsable, designado logo oficial del agente:
`echo-ai-agent-logo.png`, 2000 × 2000, SHA-256
`bdfcf084c25a33aa64dd66fc260513fc265d3962cb233b1dd076ded475338cbd`.
Original y copia web tienen el mismo hash.
Diez derivados PNG: 16/32/48/64/128/180/192/256/512/1024; ICO 16/32/48.
Redimensionado mecánico autorizado, sin IA generativa, recorte o rediseño.
[Fuente, tamaños y regeneración](../assets/brand/echoai/README.md).

## Web local

Repositorio correcto: `/home/user/rxlabs.org_local`, no la copia histórica
`echoai/ROGEX-LABORATORIES`.

- Logo visible en `/echoai` y en el artículo nuevo.
- `src/identity.js` comparte selección entre React y los HTML generados:
  ECHOAI, sus docs y artículos usan el logo del agente; las demás secciones
  conservan `/favicon.svg` (R). Incluye ES/EN/CA y apple-touch-icon.
- `Head.jsx` sustituye los iconos al navegar, sin duplicados ni iconos R
  residuales en ECHOAI. `postbuild.mjs` aplica lo mismo al primer HTML.
- Nuevo artículo destacado: `/articulos/echo4-continuidad-dream-a-identidad`,
  traducido a inglés y catalán, enlazado desde Inicio, Artículos y echoAI.
- Roadmap público v3: CONTINUITY cerrado en su dominio, DREAM-A primer
  incremento verificado, B/C/D pendientes, RELEASE-1 en PLAN.
- Resumen editorial público v3 con métricas y límites; v2 preservado.
- Exportaciones Markdown, sitemap y llms-full regenerados; no se publican
  checkpoints, secretos, conversaciones o modelos privados.

## Separación del proyecto legado

[Archivo Discord](ECHO-DISCORD-ARCHIVE.md), con recibo de movimiento íntegro.
No borrados. No referencia operativa a echo-discord en los módulos ECHO-4 ni
sus pruebas. AGENTS y README explicitan la separación. Las referencias
editoriales que describen el archivo no son dependencias ejecutables.
No se borra el enlace de la comunidad Discord del laboratorio.

## Verificaciones

1. `npm run build` pasa en la copia de preparación y en la web local.
2. `node scripts/test-identity.mjs`: 199 casos de rutas/HTML generado;
   tres exportaciones del artículo y un único artículo destacado. Incluye
   todas las páginas generadas y variantes lingüísticas, R fuera del ámbito,
   favicon en acceso directo y ficheros existentes. No testea producción.
3. Navegador sobre el preview local existente `127.0.0.1:4174`: logo cargado
   en escritorio, artículo destacado en móvil 390 × 844, sin desbordamiento;
   acceso directo catalán y docs inglesas correctos. ECHOAI → artículo →
   PRISMA cambia iconos sin reemplazar el documento; Inicio conserva la R.
4. Sin errores JavaScript detectados. El preview informa que el script de
   Vercel Analytics no está disponible localmente; no es un fallo del logo.
5. 31 tests DREAM-A pasan en 11,017 s con `python3` del sistema. Se conservan
   los hashes de las 66 fuentes y el vínculo de integridad CONT-D. No es una
   repetición de toda la campaña CONT-D ni de las 748 pruebas previas.
6. `git diff --check` sin errores en ambos repositorios. Revisión React:
   sin librería nueva, sin peticiones de datos, efecto dependiente de ruta,
   imágenes con dimensiones/alt y selección compartida cliente/build.

Aviso no bloqueante del build: bundle JS de aproximadamente 990 kB
minificado (339 kB gzip), por encima del umbral de 500 kB. La división del
bundle queda fuera de este cambio; no se presenta como un build sin avisos.

## Estado de entrega

**Preparado y verificado localmente; sin commit, push ni despliegue Vercel.**
La publicación real requerirá el paso de entrega correspondiente. La web
conserva `article-mobile.png` y `articles-desktop.png`, archivos previos ajenos
a este cambio. RXos ya tenía muchos cambios y experimentos sin seguimiento:
no se han borrado, ocultado con gitignore ni añadido masivamente a Git.
No se afirma que `git status` esté vacío o que todo el histórico esté auditado.
