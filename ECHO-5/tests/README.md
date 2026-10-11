# Pruebas de ECHO-5

`make test` ejecuta la suite `test_*.py` con unittest en la `.venv` propia.
Las integraciones nativas opcionales de MiniGrid se omiten en ese entorno y
se ejecutan con `.venv-sandbox/bin/python -I scripts/closure.py test-external`.
`test_distribution.py` comprueba imports remapeados, custodia del núcleo y
preparación de helpers SITL en un proceso aislado; no lanza simuladores ni vuelos.

Las pruebas ordinarias deben funcionar sin GPU, red, LLM ni credenciales.
Los ensayos científicos tendrán contratos, presupuestos y recibos separados.
