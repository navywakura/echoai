# S6-B4 · auditoría semántica del payload de inferencia

2026-09-28. Antes del cierre del piloto y de cualquier examen B4.

La adenda de inferencia conserva sus fuentes congeladas. Su auditor compara
el wrapper contra un payload JSON reconstruido desde disco, pero los recibos
se guardan con claves ordenadas y el wrapper original usa el orden de creación.
JSON equivalente puede tener distintos bytes al codificarse en base64.
Esa reconstrucción no debe producir un falso fallo de custodia.

`lab/kaggle/s6b4-runtime2-20260928/closure.py` extrae por AST la constante
base64 del wrapper guardado, exige que su JSON sea exactamente igual al
payload guardado y reconstruye el wrapper usando **esa misma constante**.
Comprueba el hash de envío, todos los demás bytes del wrapper, las respuestas,
peticiones y perfiles, y su vínculo con los diarios. No cambia generación,
propuestas, filtros, criterios, contratos, cohortes ni fuentes anteriores.
Las extensiones siguen declaradas; no se atribuyen al digest nativo original.

Su código, test y esta adenda se congelan aparte antes de auditar. El supervisor
espera a que termine el anterior, conserva su salida y realiza esta comprobación
antes de dar paso al examen o al cierre final. Un fallo técnico no se transforma
en una aceptación científica. No se repiten inferencias para esta corrección.
