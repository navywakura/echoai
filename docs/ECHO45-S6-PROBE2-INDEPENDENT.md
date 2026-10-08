# PROBE2 — reejecución independiente

3 de octubre de 2026. Contrato fijado antes de jugar. Esta auditoría ejecuta
la base y los dos supervivientes 28/33 en las mismas 80 partidas A, con
cuatro procesos Python 3.12 y caché nueva. Son 240 partidas; el límite de
320 incluye trabajo reservado que pudiera quedar interrumpido. Se exige
identidad del digest completo con PROBE2 y se recalcula V3 (+2 niveles y
ninguna pérdida individual de nivel o score). Cualquier discrepancia detiene
la auditoría como fallo del instrumento, conservando los registros.

Reutiliza el ejecutor congelado. Guarda cada resultado con digest antes de
borrar su diario efímero, como PROBE1. Archiva sus propias fuentes y verifica
el perfil original de PROBE2. No mide B ni el examen y no llama al modelo.
Las reglas auditadas son controles encontrados mediante búsqueda dirigida
humana; nunca cuentan como descubrimiento autónomo ni se pasan al LLM.

Recibo: `lab/seed/s6probe2-independent-20261003/audit.json`.
S6 necesita además piloto/campaña autónomos, conservación V4 y examen B1–B5.
