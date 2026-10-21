# ECHO-5.8 · poner en verde lo que falló

Abierto el 20 de octubre de 2026. **Estado (21/10/2026): pistas A, B y C en
verde en examen**, cada una con contrato escrito antes de medir, examen
congelado de una sola pasada y verificación independiente. Los rojos
históricos se conservan como rojos.

| Pista | Resultado | Documento |
|---|---|---|
| **A · MEMORIA-X**: memoria entera de roles entre mundos | **VERDE** | [`docs/MEMORIAX-RESULTS.md`](docs/MEMORIAX-RESULTS.md) |
| B v1 · ACUMULA | roja en examen | [`docs/ACUMULA-RESULTS.md`](docs/ACUMULA-RESULTS.md) |
| B v2 · ACUMULA-2 | cerrada roja en desarrollo | [`docs/ACUMULA2-DEV-NOTE.md`](docs/ACUMULA2-DEV-NOTE.md) |
| **B v3 · ACUMULA-3**: ECHO elige y encadena ediciones de memoria y piezas de política desde sus fallos | **VERDE** (las piezas no las inventó ECHO) | [`docs/ACUMULA3-RESULTS.md`](docs/ACUMULA3-RESULTS.md) |
| C v1, primer diseño | cerrado en desarrollo | [`docs/ENJAMBRE1-DEV-NOTE.md`](docs/ENJAMBRE1-DEV-NOTE.md) |
| **C v1 · ENJAMBRE-1**: 4 ECHO con memoria privada + global por postales WSP, que se ayudan | **VERDE** (la ayuda solo cuenta donde hace falta) | [`docs/ENJAMBRE1-RESULTS.md`](docs/ENJAMBRE1-RESULTS.md) |

Roadmap: [`docs/ROADMAP.md`](docs/ROADMAP.md). Contratos: `docs/*-DESIGN.md`
y sus enmiendas. Siguiente: C v2 (con mentiroso, sobre LINK-3) y la propuesta
de que el córtex invente las piezas ([`docs/B4-LLM-PIEZAS-PROPUESTA.md`](docs/B4-LLM-PIEZAS-PROPUESTA.md)).

## Código y datos

- Código: [`../echo58/`](../echo58/) (`memx`, `acumula`, `acumula2`, `b3`,
  `acumula3`, `enjambre`). Enteros en el agente y la memoria; córtex apagado.
- Tests: `../tests/test_echo58_*.py`.
- Datos de examen y desarrollo: [`results/`](results/) (`preflight.json` =
  congelación, `exam/` = trabajos crudos, `results.json` = informe).
- `../navi10_qn.py` y `../navi10_wsp.py`: el paquete WSP de 16 bytes del que
  dependen las postales (copia sin cambios del árbol de investigación).

## Reproducir

El código espera la disposición del árbol de investigación: el paquete
`echoai` dentro de una carpeta que también contiene los módulos `navi10_*`, y
los datos en `echoai/lab/echo58/`.

```bash
mkdir work && cd work
git clone https://github.com/navywakura/echoai.git
cp echoai/navi10_qn.py echoai/navi10_wsp.py .
mkdir -p echoai/lab && cp -r echoai/ECHO-5.8/results echoai/lab/echo58
python3.12 -m venv venv && venv/bin/pip install gymnasium "minigrid==3.0.0" numpy
PYTHONPATH=. venv/bin/python -m echoai.tests.test_echo58_enjambre
PYTHONPATH=. venv/bin/python -m echoai.echo58.enjambre.report      # recalcula E1–E4 desde exam/
```

La pista A usa además AI Safety Gridworlds en un intérprete aparte
(`~/.venvs/asg`, ver `echo58/memx/world.py`). La comprobación de congelación
(`frozen_state()`) recalcula los hashes del código, del contrato y de los
tests: en esta copia coincide con la del examen de C.
