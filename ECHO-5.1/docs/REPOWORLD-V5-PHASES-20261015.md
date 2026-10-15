# ECHO-5.1 — V5: corrección de búsqueda y compuertas de lanzamiento

Estado: fase 1 completa. V5 pendiente; no hay resultados de campaña.
Raíz privada: `ECHO-5.1/artifacts/repoworld-gates-v5-20261015/`.

## Fase 1: búsqueda y verificación offline

Se reproduce el fallo de V4 con búsqueda real en un snapshot y un proveedor
programado que repite la búsqueda si recibe error. Antes de la corrección no
puede editar. Después busca, observa, entrega el control y aplica un parche que
pasa los checks del fixture. El fixture es una prueba del protocolo, no capacidad LLM.

La normalización está limitada a `repo_search`: espacios exteriores y barras
finales; vacío y `./` representan la raíz del repo. Las rutas absolutas se
rechazan **antes** de quitar barras. Se conservan las prohibiciones de `..`,
componentes internos vacíos/dot, NUL, backslashes y objetivos symlink. Una ruta
con barra final debe ser directorio, no archivo. No se cambia `_parts`, el
validador de snapshots ni las reglas de paths de parches/lectura.

Un recibo `repoworld.search-path` firma argumento original, canónico, snapshot
y hashes de consulta. Los cursores quedan ligados a la consulta canónica.
El feedback de rutas inválidas explica el formato y muestra un ejemplo de
búsqueda relativa; los intentos fallidos siguen consumiendo herramientas.

Seis pruebas nuevas; 27 pruebas de herramientas/workspace pasan. El verify
completo pasa con **449 pruebas y 3 omitidas** (182 RepoWorld incluyendo tres
omisiones, 257 PCWorld y 13 de diseño). Se preserva el primer intento fallido:
`software-first-attempt/pcworld.log`, donde una cancelación de arranque produjo
CPU observada cero y la prueba exigía CPU positiva. El recheck aislado y la
repetición completa pasan sin modificar código ni aserciones de esa prueba.
Es una sensibilidad temporal pendiente de estabilizar, no un fallo ocultado.

Gates en `repoworld-gates-v5-20261015`: `software/`, `smoke/`, `preflight/`
y `official-controls/`. Smoke: replay idéntico, rollback comprobado y 127
recibos válidos. Preflight: 36/36 baselines reatestados mediante hashes completos
de snapshots/runtime y recibos originales; no se volvieron a ejecutar esos
tests. Curador: 36/36 controles y 72 logs revalidados, sin nueva ejecución del
harness. `check_ready.py` alcanza la frontera del proveedor con red bloqueada;
`remote/operate.py check` valida las cuatro compuertas. GPU/LLM: cero en fase 1.

## Fase 2: calibración reservada

Una ejecución `sympy__sympy-19007`, E, semilla 73, 32B Q4_K_M en 2 T4,
tras gates locales válidos. Se medirán búsqueda, lectura íntegra de `_entry`,
traspaso con al menos 15.000 tokens, propuesta exacta, retención/checks públicos
y auditoría. Parada del worker y servicios al terminar. Un gate técnico válido
no sustituye estos criterios funcionales.

## Fase 3: contrato y campaña

Se conserva la separación registrada: 24 issues × S/I2/F/E = 96 episodios
principales; 24 adicionales de E_no_guard; calibración y memoria por separado.
I2 son dos candidatos independientes (11k + 11k) con selector (3k), no un bucle
de refutación con rollback. Los 36 IDs no forman una muestra principal homogénea.

El sellado real solo procederá con el ciclo funcional V5 comprobado. Las
salidas se congelan antes del harness oficial; los tests ocultos nunca entran
al proponente. El límite global registrado es 18 horas, con topes por fase y
preservación de las celdas no iniciadas en el denominador. No es una promesa
de completar todos los episodios dentro de ese tiempo.

## Fase 4: cierre y transición

El porcentaje resuelto requiere el harness y la auditoría final, no basta con
checks públicos. Se informarán regresiones públicas observadas/bloqueadas;
no se llamarán reducción de alucinaciones sin una métrica definida.
Un release/tag de ECHO-5.1 queda condicionado a sus criterios de cierre y a
resultados independientes. ECHO-5.5 requiere un alcance multi-lenguaje y
contratos propios; no se declara iniciado ni completado por este arreglo.

## Checklist operativo

- [x] Verify completo nuevo y smoke hermético.
- [x] Preflight y controles oficiales reatestados, frontera del proveedor válida.
- [ ] V5 funcional completa y auditoría con apagado confirmado.
- [ ] Contrato/lock sellados y material de lanzamiento validado.
- [ ] Campaña, oráculo reservado, export y gráficas medidos.
- [ ] Cierre de ECHO-5.1 y decisión de alcance para ECHO-5.5.
