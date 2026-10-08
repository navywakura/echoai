# S6-B4 · caché explícita para recuperar la inferencia

2026-09-28, antes de nuevas respuestas. Se conserva íntegra la primera
[adenda](ECHO45-S6-B4-INFERENCE-RECOVERY.md) y su perfil. Su intento falló
con `Cannot use prefill chunking without a cache`, antes de generar respuestas.
Se archiva como `rounds/3/gpu-attempt3`; no es un resultado experimental.

La segunda extensión conserva el cambio `prefill_chunk_size=512` y añade
`cache_implementation='dynamic', use_cache=True` a `generate`. En Transformers
5.0.0 `_prepare_cache_for_generation` solo construye esta caché cuando se
solicita explícitamente; `_prefill` la exige. Se mantiene FP16 y todos los
tokens. No se cambia modelo, revisión, muestreo, gramática, peticiones,
criterios, fuentes originales ni cohorte. Se repite completa la ronda 3;
los tres intentos anteriores se descartan por fallos técnicos antes de medir
su utilidad. Desde la ronda 3 todos los brazos usan esta segunda extensión.

El código nuevo se congela por separado en `lab/kaggle/s6b4-runtime2-20260928`.
Las respuestas tienen su `runtime_digest`, añadido al digest nativo, y una
auditoría extra comprueba wrappers y procedencia antes y después del examen.
No se afirma identidad numérica con inferencia sin bloques. Cuota gratis;
la espera por cuota no autoriza pago ni confirma que S6 vaya a ser verde.

[Implementación primaria fijada](https://github.com/huggingface/transformers/blob/v5.0.0/src/transformers/generation/utils.py).
