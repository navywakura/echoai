# SWE-bench Lite V8 · resultados de ECHO-5.1

Esta copia conserva datos agregados, gráficas PNG/PDF y los contratos usados.
El [informe completo](../../REPOWORLD-SWE-RESULTS-20261016.md) explica los límites.

- 115 episodios ejecutados y 35 no iniciados; 150 registros evaluados.
- Principal: S 2/17; I2, F y E 1/17. Denominador registrado: 24 por brazo.
- No es la ejecución de las 300 tareas completas de SWE-bench Lite.
- Cero lecciones transferidas. Menos tokens no acredita una ventaja de resolución.
- `public_regressions` / `regressions_blocked` conservan los contadores originales.
  Los campos `valid_public_regressions`, `guard_blocked_valid_regressions` e
  `invalid_public_observation_rejections` distinguen fallos de import/colección.

## Regenerar las imágenes

Desde este directorio, dentro del worktree original:

```bash
python3 regenerate_figures.py --output /tmp/echo51-v8-figures
```

Si se usa el ZIP fuera del repositorio, añadir `--repository /ruta/a/echoai`
con el plotter original de la revisión congelada. Se requieren Python,
matplotlib y jsonschema. No se usa LLM, GPU, túnel ni el oráculo.

`MANIFEST.json` lista SHA-256 de los archivos de esta copia. La regeneración
comprueba esos hashes y el plotter. **No autentica HMAC** ni repite el benchmark;
la auditoría completa necesita los diarios y autoridades locales originales.
Se excluyen claves, configuraciones de relay/proveedor y el dataset privado
de evaluación. El manifiesto no constituye una firma de un tercero.
