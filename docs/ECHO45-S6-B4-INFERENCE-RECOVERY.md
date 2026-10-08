# S6-B4 · adenda de recuperación de inferencia

2026-09-28. Adenda escrita antes de generar nuevas respuestas o abrir el examen.

Las rondas 0–2 terminaron. La ronda 3 falló dos veces por CUDA OOM en el
prefill de los prompts globales. Cada intento conservó dos respuestas locales
sin verificar; se archivan ambos intentos íntegros y **no se usa ninguna de
esas cuatro respuestas**. Se repite la ronda 3 completa con el mismo runtime
para sus cuatro brazos. La elección de descarte obedece al fallo técnico,
antes de medir utilidad. No se escoge entre respuestas por puntuación.

La única modificación de inferencia es `prefill_chunk_size=512` en
`model.generate`. Transformers 5.0.0 conserva todos los tokens en la caché y
procesa el contexto en bloques. No se recorta el prompt, se cuantiza el modelo
ni se cambia la revisión, FP16, gramática, semilla, temperatura, top-p o límite
de generación. La aritmética de GPU puede variar con el tamaño del bloque;
no se afirma que las respuestas sean idénticas. Rondas anteriores conservadas;
desde la ronda 3 todos los brazos utilizan el runtime declarado aquí.

El código y contrato B4 original permanecen intactos. La extensión tiene su
propio perfil congelado y archivo de fuentes en
`lab/kaggle/s6b4-runtime-20260928`. El perfil de cada nueva respuesta registra
además `runtime_digest`; `source_digest` identifica las fuentes nativas B4,
no pretende cubrir esta extensión. La auditoría adicional comprueba ambos,
las peticiones completas, wrappers, respuestas y procedencia de los diarios.
Se ejecuta antes de permitir el examen y al auditarlo.

No cambian filtros, criterios B1–B5, cohorte reservada ni promoción del piloto.
La campaña sigue siendo gratuita y espera si no dispone de 900 s de cuota.
Los intentos fallidos también consumen cuota y se conservan como fallos.

Referencia de implementación primaria:
[Transformers 5.0.0, `_prefill`](https://github.com/huggingface/transformers/blob/v5.0.0/src/transformers/generation/utils.py).
