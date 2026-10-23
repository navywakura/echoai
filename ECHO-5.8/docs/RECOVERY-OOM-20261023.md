# Recuperación tras reinicio del equipo · 23/10/2026

Nav comunica caída del PC y autoriza continuar vigilando recursos. El
journal del arranque anterior registra OOM global a las03:16 y03:18: Python
invocó el cierre por falta de memoria y el kernel mató freenet. No se atribuye
el incidente sólo a CPU ni se afirma que se aislara un único proceso causal.
Había cuatro trabajadores E y cuatro C, más el inicio del vuelo P. La
concurrencia elegida fue excesiva para los13GiB de RAM del equipo.

## Política nueva de recursos

Un único trabajo pesado global, en orden C → E → P, protegido mediante
`flock /tmp/echo58-heavy.lock`. C y E: un trabajador, proceso nuevo por caso,
CPUQuota100%, MemoryHigh1536M, MemoryMax2G, MemorySwapMax0, TasksMax96,
prioridad nice10 y sin reinicio automático. OpenBLAS/MKL/OMP/NumExpr a un
hilo. Se utilizan unidades systemd de usuario; una prueba confirmó que los
límites se aplican. Mantener unidades hasta guardar consumo máximo.

P necesita además límites explícitos en Podman, porque sus contenedores
pueden crear cgroups fuera del supervisor. Un solo vuelo; jaula pequeña y
vuelo limitado, hilos de render/BLAS a uno. Nada de cambiar configuración
global del sistema, matar servicios del usuario o usar PID del arranque
anterior. Los PID siempre se vinculan al boot_id y unidad actuales.

El coordinador registra CPU/memoria de la unidad y memoria disponible del
host. Si el límite resulta insuficiente se conserva el fallo y se diagnostica;
no se elimina el límite para completar deprisa. No habrá E/C/P simultáneos.

## Custodia al reanudar

Antes de cambiar rutas o lanzar trabajos se guardaron hashes de los artefactos
existentes y un informe del incidente en
`lab/echo58/closure-20261023/recovery-oom/`. No se modifica ninguna política,
candidato, semilla, control, número de casos, selección ni puerta científica.
No se vuelve a ejecutar un recibo completo. W y D estaban terminados y se
conservan; no se repiten llamadas API ni partidas de integración.

C:158/210 recibos de validación completos;160 carpetas de rondas. Dos trabajos
interrumpidos tienen15 y5 rondas guardadas. Preservar sus bytes/hashes;
al reconstruir el mismo trabajo exigir cada ronda antigua exactamente igual
al prefijo reconstruido. Un desacuerdo bloquea validez, sin reemplazarlo por
un resultado más favorable. Completar los otros50 pendientes una sola vez.

E:232 recibos completos (80 aprendizajes y152 validaciones),236 trazas. Cuatro
trazas huérfanas de433–436 bytes conservan cabecera, sin transiciones válidas
recuperadas en la inspección inicial. No se fingirá haber comparado estados
que no llegaron a disco. Conservar bytes y error de truncamiento, reconstruir
sólo las cuatro semillas sin resultado y terminar las pendientes. Las tablas
de aprendizaje y los232 recibos completos no se repiten. El protocolo original
quedó interrumpido; el informe distingue datos recuperados y cumplimiento de
las puertas de la pretensión de una ejecución sin interrupciones.

P:primer dev inició pero no dejó resultado de vuelo, sensores ni bridge.
El directorio temporal desapareció y no hay contenedores vivos tras reinicio.
Preservar plan, bundles, meta y evento de inicio; clasificar el intento como
`INTERRUPTED_OOM_NO_RESULT`, sin asignarle éxito, daño cero ni puntuación.
La recuperación no selecciona un mundo distinto por resultados.

Cada pista tendrá recuperador nuevo separado de sus fuentes congeladas y
anexo de incidente previo a reanudar. El dictamen hará explícita la
interrupción; no cambiar umbrales para recolorear resultados. El permiso de
Nav cubre recuperar la ejecución, no inventar datos ni ocultar fallos.

## Resultado de la recuperación

C completó los 210 recibos con los 158 anteriores intactos y 20 prefijos
idénticos; su auditoría pasa y el resultado científico queda rojo. E completó
380 episodios, conservó los 232 previos y cerró roja por pérdida de progreso:
«deuda residual, autopsiada». No hay otro intento autorizado de E.

P terminó dos desarrollos recuperados y seis validaciones, con auditoría final
verde para su alcance estrecho. El intento interrumpido cuenta en su máximo
de tres. Antes de medir se corrigió el actor yaw relativo y se preservaron
ambos bundles; no cambió el consumidor ni el aprendizaje activo. La adenda
y sus hashes están en los documentos PERCIBEX. La caché simple iguala o mejora
sus inspecciones; no se afirma ventaja exclusiva del motor.

Todos los trabajos pesados posteriores se ejecutaron por turnos con los
límites fijados. P añadió límites reales de contenedor CPU1,5/RAM3GiB/swap0;
los del supervisor no se confunden con los del contenedor. Los contadores
y sus límites de cobertura permanecen archivados. El cierre global está en
[CIERRE-58-582-RESULTS-20261023.md](CIERRE-58-582-RESULTS-20261023.md).
