# ECHO-5.1-V2 — compuertas y calibración remota

Fuente de implementación: `cd772ce`, rama `research/echo-5.1-pcworld1`.
Estado: compuertas técnicas válidas; calibración funcional fallida. ECHO-5.1 sigue abierto.

## Alcance congelado

Una calibración reservada `sympy__sympy-19007`, brazo E, semilla 73.
Qwen2.5-Coder-32B-Instruct Q4_K_M, contexto 4096; límites 3200 tokens
entrada, 768 salida y 25000 por episodio. La interfaz V2 está disponible para
todos los brazos; este ensayo único no compara E con S, I2 ni F.
No se ejecuta la campaña primaria ni se consulta el oráculo final.

## Evidencia local

Raíz de artefactos: `ECHO-5.1/artifacts/repoworld-interface-v2-20261015/`.

- `software-final/`: 439 pruebas pasadas, 3 opcionales omitidas. Evidencia
  previa conservada, autenticada de nuevo contra el manifiesto actual.
- `smoke-final/`: proveedor programado, rollback observado, replay idéntico,
  127 recibos válidos. No representa rendimiento del modelo.
- `preflight/`: 36/36 instancias, 12/12 repositorios válidos; fuentes intactas.
- `official-controls/`: 36 controles válidos reatestados, 72 logs cotejados
  con SHA-256 y recibos originales autenticados. No se repitieron ejecuciones.
  `link-provenance.json` enumera los cambios de interfaz y prueba que el
  curador aislado, dataset, servicio Requests y harness permanecen iguales.
- `remote/`: helper y credenciales privadas nuevos; no se versionan secretos.

## Operación reproducible

```bash
G=ECHO-5.1/artifacts/repoworld-interface-v2-20261015
python3 "$G/remote/operate.py" check
python3 "$G/remote/operate.py" start
# Subir el bundle privado generado a Kaggle con 2 T4 y límite de 1800 s.
# watch_calibration.py espera al worker, ejecuta una sola calibración y pide stop.
python3 "$G/remote/watch_calibration.py"
python3 "$G/remote/operate.py" stop
```

El helper usa `software-final`, `smoke-final`, `preflight` y
`official-controls`; no reutiliza las compuertas v3 con otro manifiesto.
El watchdog limita la espera y solicita parada incluso si la calibración falla.
También se debe comprobar el estado terminal del cuaderno en Kaggle.

## Resultados remotos

Cuaderno privado `rogeernavarro/echo51-repoworld-interface-v2-20261015`, versión 1.
Estado final observado: **COMPLETE**. Dos Tesla T4, **65/65 capas** en GPU.
Modelo y binario coinciden con el contrato: revisión
`9d3053fce650fe1cdbdb75998c2a87add9d178ef`, SHA-256 del modelo
`4d64b316b5e6319d9613e0d97935d9ebd631fc7e334da400d00085eca749d085`, llama.cpp b11577.

| Medida | Resultado |
| --- | ---: |
| Preparación del worker | 404,605 s |
| Duración total del worker | 737,633 s |
| Episodio | 318,914 s |
| Llamadas LLM | 16 |
| Tokens entrada / salida / total | 23.145 / 1.010 / 24.155 |
| Máximo de entrada por llamada | 1.669, inferior al límite 3.200 |
| Herramientas / checks base / parches | 17 / 2 / 0 |
| Recibos auditados | 223 válidos |
| Reservas pendientes / desbordamientos | 0 / 0 |
| Resultado | `budget_stopped`, diff vacío |
| Cuota GPU antes / después | 22,15 / 21,94 h |

Consumo aproximado por la cuota redondeada: **0,21 h**. No se abrió una segunda
sesión. El worker informó `relay_result.stopped=true`, sin errores; Kaggle
terminó y los PID propios de relay/túnel dejaron de existir. El campo
`gpu_after` del worker aún muestra el servidor cargado porque se captura antes
de terminar el proceso; la confirmación de cierre es el estado COMPLETE de
Kaggle, no una interpretación de ese campo como VRAM liberada.

`require_gate(..., "remote-calibration")` pasa: acredita inferencia real,
identidad del proveedor y contabilidad cerrada. **No acredita solución del issue**.
No se evaluó el oráculo oficial y no se selló el lanzamiento de campaña.

## Diagnóstico respaldado por recibos

- Una ruta inicial con barra final fue rechazada por no ser canónica. El modelo
  la corrigió. El cursor de búsqueda reutilizado en outline fue reiniciado por
  la tolerancia existente; no abortó el episodio.
- El modelo llamó al outline y recibió `BlockMatrix._entry`, líneas **235–247**.
- Obtuvo cinco páginas: 247–256, 240–259, 230–249, 235–249, 235–249.
  Son 80 líneas devueltas, 30 únicas. Todas se cotejaron byte por byte con el
  archivo del commit base fijado: **cero líneas mutiladas**.
- A partir de la tercera página tenía el método completo. El último prompt
  seguía conteniendo `def _entry`; no faltaba contexto por expulsión del método.
- Solicitó doce `file_view` en total: cinco exitosos y siete rechazados por
  cuota de localización. También inventó cursores `current`/`source_evidence`.
- No llamó a `patch_apply`. Finalmente emitió `finish`, que hizo el traspaso
  locator→editor, pero solo quedaban **845 tokens**. El presupuesto impidió
  otra llamada. No se probó la capacidad del editor ni el formato nuevo con
  una propuesta real en este episodio.

La navegación y las líneas atómicas sí funcionaron. La política permite el
traspaso mediante `finish`, pero depende de que el modelo lo solicite; la
respuesta de cuota dice «finish if the target is unobserved» incluso cuando
el objetivo ya está observado. La combinación de lecturas repetidas,
feedback poco accionable y ausencia de reserva para edición es una hipótesis
concreta para la siguiente corrección. No demuestra incapacidad del modelo
para reparar, ni éxito del formato Search/Replace.

### Siguiente corrección propuesta (no aplicada en esta calibración)

1. Hacer explícito el traspaso del localizador al editor cuando el agente
   identifica un locus respaldado por lectura íntegra vigente; no inferir
   automáticamente que cualquier archivo leído sea el objetivo correcto.
2. Tras lecturas repetidas sin información nueva, devolver evidencia ya
   observada y opciones claras de traspaso/terminación; impedir el bucle de
   rechazos idénticos. Mantener cobro de llamadas realmente ejecutadas.
3. Reservar presupuesto para edición/verificación y registrar la decisión de
   abandono si la localización no está respaldada. No forzar código inventado.
4. Probar el recorrido con mock de lecturas repetidas y luego una calibración
   nueva. Cualquier cambio de código invalida estas compuertas para otro run.

## Checklist de cierre

- [x] Suite V2: 439 pruebas pasadas y 3 opcionales omitidas.
- [x] Smoke con rollback, replay y 127 recibos autenticados.
- [x] Preflight público renovado: 36/36, 12 repositorios.
- [x] Controles oficiales enlazados: 36/36, 72 logs y procedencia comprobados.
- [x] Helper y frontera del proveedor comprobados sin red antes de GPU.
- [x] Calibración real V2 en 2 T4; 223 recibos auditados, contabilidad completa.
- [x] Kaggle terminado y servicios locales apagados.
- [ ] Traspaso de localización robusto y reserva de presupuesto para editar.
- [ ] Parche útil generado por el 32B, aplicado y probado sin regresión pública.
- [ ] Evaluación oficial sellada; resultado de solución independiente del gate técnico.
- [ ] Comparación S/I2/F/E y ablaciones con presupuesto equivalente.
- [ ] Confirmación independiente de H1–H4/T20 y cierre científico de ECHO-5.1.

Contrato conservado en `design`, `launch_enabled:false`. Sin campaña primaria,
sin push y sin atribuir ventajas científicas a este ensayo único de desarrollo.

## Hashes de evidencia

- `software-final/report.json`: `641585fb14ff545e1c4dfd3b1e467acd540b4dc1676a402eab13e7b3d56630ec`.
- `smoke-final/report.json`: `51af02fe37cf43f5b94598d0623fd99854765d2045b5c2f121680cb108c689c8`.
- `preflight/report.json`: `2c76383ec49264f6ad539243f82c562e793aa95a44a58c0c8d87a0711fa4a33b`.
- `official-controls/report.json`: `f552d1825e6bd1d055be4543ffd35c1b577c261a96b9cce27dac81dbf2160e29`.
- `readiness.json`: `2ffc03646741379e5e8be7e26d0f789beb32e93c5db24d1f9f703c53b95f65ce`.
- `remote/calibration/report.json`: `6055b1d975e2371cc210273d004191497c0e9bf48ad852b78e99343a0660a1ac`.
- `remote/audit.json`: `2f9894c63f1b5d8f6394ee25b841e86a274ddb1cd1cf340021248ac284052125`.
- `remote/diagnostic-summary.json`: `0336e1955b883422f57f848235b94d4c0af3b7bdd0f83dc1cc6de4c7e530179c`.
- `remote/kaggle-output/gpu-proposer-results.json`: `2a9714155fbcae2bac95e0bab7868b274901aa02178c26a636e951b09e87b103`.
