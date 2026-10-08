# echo-discord — legado archivado, fuera de ECHO-4

2026-09-22. Por indicación del responsable del proyecto, `echo-discord`
queda congelado y fuera del desarrollo activo del agente.

- Origen: `/home/roger/REALRXOS/RXos/echo-discord`.
- Archivo: `/home/roger/archivos-laboratorio/echo-discord-2026-09-22`.
- Movimiento autorizado dentro del mismo filesystem, sin copiar sobre otro
  proyecto, sin borrados, sin cambios al contenido y sin symlink de retorno.
- 4.205 entradas conservadas: mismos inodos, permisos, tamaños, fechas de
  modificación y destinos de enlaces. Incluye modelos y archivos ocultos.
- Comprobación previa de procesos del usuario (argumentos, cwd, ficheros
  abiertos y mapas) y referencias systemd: ninguna referencia activa hallada.
- Carpeta contenedora privada, fuera del repositorio y de la publicación web.

[Recibo del movimiento](ECHO-DISCORD-ARCHIVE-RECEIPT.json).
La comprobación de inodos confirma el mismo árbol tras el rename; no es una
auditoría histórica de cambios ni un nuevo backup independiente.

En DREAM-A se invocó el binario Ruff instalado en su `.venv` para analizar
archivos de ECHO-4. No se modificó entonces el código Discord; reutilizar ese
entorno queda prohibido de ahora en adelante. No activar servicios, reparar
el venv trasladado, importar módulos ni usar sus modelos desde ECHO-4.
Los scripts del venv pueden conservar rutas absolutas antiguas: un archivo
histórico no es una instalación activa. El propietario deberá autorizar
cualquier recuperación futura; no se recreará silenciosamente la ruta vieja.

Las pruebas stdlib de ECHO-4 usan `python3` del sistema. Herramientas opcionales
de desarrollo requieren instalación independiente explícita, no una
dependencia accidental del bot. La comunidad Discord de RxLabs es otra cosa
y no se elimina de la web.

El árbol RXos ya tenía numerosos cambios y artefactos sin commit antes de
esta operación. Se preservan: «separado y verificado» no significa que
`git status` esté vacío, que exista una copia de seguridad remota o que se
haya auditado todo el histórico.
