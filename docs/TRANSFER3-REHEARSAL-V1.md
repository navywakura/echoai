# TRANSFER-3 — primer ensayo conductual público

2026-09-18. **Desarrollo funcional; no confirmación. TRANSFER-3 abierto.**

## Resultado observado

24 misiones cinemáticas, ocho casos emparejados para tres condiciones de
aprendizaje. Se reutilizan sin modificaciones el controlador, percepción
funcional, entorno y aislamiento de COMPOSE-1 v3. No hay vuelos nuevos.

| Condición | Metas | Movimientos | Colisiones | Violaciones de reserva |
|---|---:|---:|---:|---:|
| Efectos aprendidos transferidos | 4/8 | 136 | 0 | 0 |
| Scratch: T y Q vacías | 0/8 | 0 | 0 | 0 |
| Efectos programados, mismo controlador | 4/8 | 136 | 0 | 0 |

Cero hechos falsos según el adjudicador de COMPOSE y parámetros sin cambios
durante las 24 misiones. Las ocho semillas públicas se distribuyen entre
`static`, `dynamic`, `closed` y `low_energy`, dos por condición. Los casos
cerrados o con energía baja no se eliminan del denominador.

Entrenamiento público: cuatro salas, 24 movimientos por sala; **96 movimientos,
384 unidades simuladas**. Profesor supervisado que conoce la interfaz de
acciones y elige movimientos con paso libre observado. No se afirma que el
agente descubra autónomamente qué acción probar. La T aprende de la diferencia
entre odometrías antes/después de ejecutar, no del destino solicitado.

## Qué se transfiere

`transfer3/model.py` admite únicamente `schema` y hasta cuatro filas ordenadas
`action, delta, count`. `delta` es desplazamiento relativo horizontal unitario,
no posición absoluta. Se exporta sólo la fila abstracta de T para acción con
paso libre y al menos dos observaciones. Conteos limitados a 255. Un modelo
con contradicciones se rechaza en esta versión; no se ocultan sus conflictos.

No se exportan CAM, Q, slots originales, mapas, episodios, nombres, semillas,
trayectorias ni procedencia privada. Al importar se construyen ranuras
abstractas nuevas con `has_fact=0`, reutilizando `Effects` y `World`. Es una
reconstrucción del estadístico aprendido, **no observaciones nuevas**. Q queda
a cero. Cada misión crea otro controlador con mapas/visitas vacíos. El
objetivo de misión se proporciona a todos por igual, como en COMPOSE; no se
afirma búsqueda autónoma de una estación cuya posición sea desconocida.

El consumidor aislado es el de COMPOSE v3: sólo recibe la reconstrucción
permitida, objetivo y observaciones; no recibe seed, nombre, mundo ni mapa.
Las trazas, geometría y metadatos viven en el examinador externo.

## Por qué todavía no permite congelar la campaña

1. **Scratch se abstiene porque desconoce todos los efectos de movimiento.**
   El resultado es una ablación de disponibilidad del modelo cinemático, no
   prueba de una política transferible superior a una cinemática conocida.
   El control programado iguala exactamente metas y movimientos. No se
   presenta una ventaja frente a ese control ni significación estadística.
2. **Se repite una geometría entre escuela y examen público**, tras normalizar
   traslación, rotaciones y reflexión. No se corrige el informe ni se oculta
   esa repetición. La pequeña familia COMPOSE no basta como generador de
   confirmación de mundos nuevos. La huella actual considera celdas, sólidos,
   salida y meta; no sustituye el auditor final de SDF/materiales.
3. El protocolo sigue siendo público y de desarrollo, sin N/potencia ni
   umbrales de cierre final. No existen compromisos privados B/C.

Antes de pedir custodia a Roger falta un generador conductual con exclusión
geométrica entre particiones, verificar el alcance de la comparación scratch
y fijar los criterios de aceptación. La pregunta abierta no se resuelve
renombrando este ensayo ni aumentando sólo el número de semillas.

## Verificación y reproducción

Informe completo: `lab/transfer3/rehearsal-v1.json`. Contiene protocolo,
inventario de fuentes Python, escuela, parámetros exportados y todas las
observaciones, decisiones y consecuencias de las 24 misiones. No se
sobrescriben informes existentes. No es un freeze de campaña.

La auditoría reconstruyó escuela y misiones en un proceso nuevo, otra vez
con consumidor aislado: `replay_valid=true`, exit 0. Excluye únicamente
la sección de tiempos de ejecución del runner original de la comparación
determinista; no excluye observaciones, decisiones ni consecuencias.

SHA-256 canónico del informe:
`a994449b36a8bfe9c4a4fed268c7c7af0142cbee7109182e5dd762a4d6d5ee55`.
Este hash no es un certificado de TRANSFER-3.

Desde `echoai/`:

```sh
PYTHONPATH=.. python3 -m echoai.nexus0.transfer3.rehearsal audit lab/transfer3/rehearsal-v1.json
PYTHONPATH=.. python3 -m unittest echoai.tests.test_transfer3 echoai.tests.test_transfer3_custody echoai.tests.test_compose1_v3 echoai.tests.test_compose1_v4 -q
```

Pruebas: 13 nuevas de transferencia, 10 de custodia y 13 de regresión
COMPOSE v3/v4. El primer intento aislado dentro del sandbox fue rechazado
por permisos NETLINK; la ejecución y auditoría completas se hicieron con
permiso para los namespaces de Bubblewrap. No se desactivó su aislamiento.

**C final no generado ni abierto. ECHO-3 continúa en 13/15.**
