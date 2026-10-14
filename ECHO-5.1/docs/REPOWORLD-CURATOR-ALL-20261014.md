# RepoWorld · controles oficiales completos · 14 de octubre de 2026

## Alcance y estado

Entrega parcial, bloqueada por almacenamiento local. El objetivo es validar las 36 instancias mediante
controles vacío/referencia con SWE-bench v4.1.0 en Podman rootless. **No hay
calibración remota ni nueva puntuación científica.** Kaggle no se ha iniciado y
no se han efectuado llamadas LLM. El contrato permanece en `design`.

## Cambios

- `calibrate-remote` es alias de `calibrate`, sin eludir gates, registro ni modelo.
- Adquisición secuencial de imágenes con descarte opcional: solo se retiran IDs
  que no existían antes de descargar. Una etiqueta nueva no otorga propiedad
  sobre una imagen anterior. No se poda el almacén global de Podman.
- La evaluación final puede recuperar imágenes retiradas, comprueba el digest
  fijado y ejecuta el harness por instancia. Su plazo agregado de 6.900 segundos
  queda por debajo del supervisor de 7.200 segundos.
- Manifiesto HTTP local multiperfil: Requests-2148 usa certifi; Requests-2674 usa
  su CA vendorizada. Se conserva la CA pública de cada imagen y se agrega el
  certificado local. Solo se admiten esas rutas de certificados, no archivos de
  implementación ni tests. El bundle y la imagen quedan fijados por hash.
- Se conserva el perfil de presentación de Pytest-7168 y los mismos criterios
  estrictos del curador: el parche vacío debe fallar, el de referencia pasar y
  los estados obligatorios deben estar presentes.

## Incidencia de almacenamiento

Las primeras tandas encontraron `ENOSPC` en Btrfs pese a mostrar unos 57 GiB
libres de datos. El dispositivo estaba completamente asignado y los metadatos
DUP rondaban 6,49/7 GiB. Django-11179 pasó primero y falló durante esa incidencia
con errores de espacio tanto en vacío como en referencia; no se atribuye ese
resultado a una regresión del repositorio.

Se conservaron logs/recibos y se retiraron únicamente cachés BASE regenerables
de las ejecuciones abortadas y las imágenes de un almacén VFS temporal aislado
creado durante la preparación anterior. Dicho almacén no tenía contenedores ni
referencias en el registro activo. No se borraron runtimes, suplementos,
repositorios ni imágenes del usuario. No se ejecutó balance con privilegios.
Después pasaron 1.000 escrituras atómicas de prueba. Las repeticiones públicas
y de software usan `/tmp` para reducir presión sobre Btrfs.

Las tandas `controls-r1` y `controls-r2` son diagnósticos interrumpidos, no gates
válidos. No se mezclan sus éxitos para declarar 36/36.

## Verificación

- Software: 419 pruebas pasadas; dos integraciones omitidas explícitamente en
  esa ejecución y después ejecutadas aparte con pase 2/2.
- Smoke simulado con fuentes actuales: gate válido, regresión, rollback y replay;
  no es resolución científica de SymPy.
- Preflight público actualizado: 36/36, gate autenticado y fuentes coincidentes.
- Curador `controls-r3`: 11/36 intentados, 7 válidos; tanda interrumpida por ENOSPC. No existe un gate `official-controls` completo válido.
- Revisión independiente: corregidas propiedad de imágenes y recuperación
  después de su descarte; añadido límite agregado de evaluación.

Evidencia privada local: `ECHO-5.1/artifacts/repoworld-curator-all-20261014/`.
No publicar certificados privados, autoridades HMAC, tests reservados o parches
oficiales de referencia. El manifiesto público final debe contener solo hashes,
identidades y veredictos agregados.

## Siguiente gate

[Procedimiento de calibración remota](REPOWORLD-REMOTE-CALIBRATION.md): relay con
IDs duraderos, worker 32B fijado y un solo episodio `sympy__sympy-19007`.
No iniciarlo hasta disponer de los tres gates válidos con las mismas fuentes.
Diez minutos es un objetivo de inferencia, no una garantía de cuota total: la
carga y descarga del modelo también consumen tiempo de GPU.

- [x] Alias y procedimiento de Gate 3 preparados.
- [x] Suite de software y dos integraciones verificadas.
- [x] 0 GPU y 0 llamadas LLM durante esta entrega.
- [ ] Gate `official-controls` válido 36/36.
- [x] Preflight público actualizado 36/36.
- [ ] Calibración remota, confirmación de parada y lock científico.
- [ ] Campaña y evaluación científica independiente.

## Punto de recuperación tras la interrupción

Los cambios siguen en la rama `research/echo-5.1-pcworld1`; los tres gates
locales se han vuelto a autenticar y sus archivos completos se han comprobado
con `tar -tzf`. [Manifiesto público de progreso](swebench/REPOWORLD-CURATOR-PROGRESS-20261014.json)
contiene los hashes de los archivos, sin claves ni contenido reservado.
Las autoridades no se pueden trasladar: restaurar los archivos en sus rutas
originales `/tmp/echo-curator-{software,smoke,preflight}-r2` cuando haga falta.
Las copias de consulta bajo `artifacts/` no sustituyen esos gates.

La limpieza de cachés permitió reanudar temporalmente, pero no resolvió la
asignación de espacio de Btrfs: Seaborn y Flask volvieron a fallar con ENOSPC.
Quedan aproximadamente 54 GiB libres dentro de bloques ya asignados, solo 1 MiB
sin asignar y 6,49/7 GiB de metadatos DUP usados. No relanzar la tanda hasta
verificar que vuelve a ser posible extraer y crear contenedores de forma estable.
Se solicitó al usuario el primer mantenimiento con privilegios:
`sudo btrfs balance start -dusage=0 /home`, seguido de
`sudo btrfs filesystem usage /home`. El primer comando recupera grupos de datos
vacíos, pero puede resultar insuficiente; revisar la salida antes de continuar.
La [documentación de Btrfs](https://btrfs.readthedocs.io/en/latest/btrfs-balance.html)
describe ese filtro para casos ENOSPC. Aquí `sudo` requiere contraseña y no se
ha ejecutado dicho mantenimiento.

Matplotlib-18869 y Matplotlib-26011 fallaron al extraer archivos de qhull con
UID/GID 197609:197121, fuera de los 65.536 IDs subordinados disponibles.
La opción de descarga `--storage-opt overlay.ignore_chown_errors=true` permitió
extraer 18869; la descarga de 26011 volvió a fallar por ENOSPC. No se cambió la
configuración global. Esta opción puede cambiar propietarios y **no cuenta como
validación de los controles**; su alcance está registrado en
`rootless-unpack-policy.json` de la evidencia privada. Véase la
[documentación de Podman](https://docs.podman.io/en/latest/markdown/podman.1.html).

Próximo trabajo: resolver almacenamiento, completar y fijar el perfil rootless,
repetir los controles de las 36 instancias y autenticar el gate completo. Después
podrá ejecutarse la calibración remota; no se ha autorizado automáticamente una
campaña completa por estos resultados parciales.
