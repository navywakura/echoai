# Copia de investigación del 10 de octubre de 2026

Esta carpeta conserva los avances de B24 y la calibración ARC previos a
ECHO-5. Es una copia de los archivos existentes; no ejecuta experimentos,
no abre reservas y no acredita un pase de S6.

`MANIFEST.json` describe 725 archivos de origen almacenados en 465 archivos
únicos (223.596.138 bytes). Las 260 repeticiones apuntan a la misma copia
mediante `stored_as`. Cada entrada registra su ruta original, tamaño y
SHA-256. La verificación de la distribución también cubre esta carpeta.

Se incluyen los scripts operativos, contratos y fuentes de los paquetes,
recibos de formato, recuperación, checkpoint, salidas de Kaggle, diarios y
logs existentes; también las pruebas y salidas de la calibración ARC. Los
archivos comprimidos de evidencias se conservan con sus bytes originales.
Su presencia permite conservar la historia, no implica que todos los
ensayos hayan terminado o superado sus criterios.

Se conserva también una extracción de un intento anterior fallido,
`checks/isolated-r1-77iw342v/seed/s6b24.py`, con un error de indentación.
Es un artefacto histórico, no el módulo activo. Su hash se conserva y no se
reescribe para hacer pasar una comprobación de sintaxis de código vigente.

Las cinco copias del binario externo de llama.cpp/CUDA quedan enumeradas
con hash y tamaño como material reconstruible. No se incluyen entornos
virtuales, cachés de Python, archivos de bloqueo, pesos LLM o credenciales.
La copia es secuencial: los gestores activos pueden actualizar sus logs y
estado después de la captura, sin cambiar esta fotografía.

Para localizar una evidencia se busca su ruta del laboratorio en `source`
y se lee el archivo indicado en `stored_as`, relativo a esta carpeta. Las
rutas pueden reconstruirse en una carpeta independiente usando ese mapa,
verificando previamente cada hash. Los scripts guardan rutas y perfiles del
laboratorio original; son evidencia histórica, no comandos listos para
ejecutar desde esta carpeta. No restaurar sobre una campaña activa.

El código distribuido actual está en `seed/`, `echo_arc/`, `tests/` y los
demás módulos de la raíz. Las copias dentro de este archivo conservan las
condiciones que rigieron los ensayos; no deben importarse automáticamente
al agente ni introducirse en los prompts.

[Estado general y decisiones](../../docs/PROJECT-CHECKPOINT-20261010.md)
— ruta desde la raíz: `docs/PROJECT-CHECKPOINT-20261010.md`.
