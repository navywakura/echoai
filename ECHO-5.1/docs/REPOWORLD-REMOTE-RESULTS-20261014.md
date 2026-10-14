# Calibración remota RepoWorld — 14 de octubre de 2026

## Intento 1: rechazo local anterior a inferencia

Directorio privado: `artifacts/repoworld-remote-calibration-20261014T115920Z`.
Kaggle: `rogeernavarro/echo51-repoworld-calibration32b-20261014`, versión 1.
Estado final comprobado: COMPLETE. Modelo 32B cargado en las dos T4;
`errors=[]`, `relay_result.requests=0`, `relay_result.stopped=true`.
Preparación remota: 401,135 segundos; worker completo: 409,333 segundos.
Cuota observada después: 22,83 h disponibles frente a 22,94 h antes
(valores de la API redondeados a centésimas).

El comando falló con `calibration environment changed after preflight`.
Comparar los manifiestos reveló 209 directorios con permisos 0700 frente a
0755. El lanzador privado heredaba `umask 077`; la extracción de repositorios
registra permisos en el hash. No se cambió el código candidato ni se llamó al
LLM. El rechazo protege la reproducibilidad: no es un resultado SWE-bench.

La corrección del lanzador fija `umask=0o022` para el subproceso, conservando
la carpeta privada 0700 y secretos 0600. No modifica las fuentes congeladas,
los tests, el contrato ni los resultados previos. La identidad completa de las 36 preparaciones se reprodujo correctamente
antes de autorizar el reintento.

## Intento 2: gate técnico válido, diff vacío

Directorio privado: `artifacts/repoworld-remote-calibration-20261014T121503Z`.
Mismo cuaderno privado, versión 2; instancia reservada `sympy__sympy-19007`.

- Preparaciones reproducidas: 36/36 (árbol, runtime y plan público).
- Modelo fijado: Qwen2.5-Coder-32B Q4_K_M; 65/65 capas en dos T4.
- Preparación del worker: 362,765 s; calibración: 364,736 s.
- Worker completo: 735,834 s; estado final Kaggle COMPLETE.
- 51 peticiones de relay (incluyen plantilla/tokenización), 17 generaciones LLM.
- 15.698 tokens totales; 18 herramientas; 8 intentos de parche; 2 tests.
- Auditoría: `valid=true`, 251 recibos, contabilidad completa, cero reservas
  pendientes y ningún exceso registrado.
- `errors=[]` y `relay_result.stopped=true`; relay/túnel propios detenidos.
- Cuota final observada: 22,62 h. Los dos intentos consumieron aproximadamente
  0,32 h según la cuota redondeada, incluida preparación remota.

El resultado del agente fue `budget_stopped`: agotó ocho intentos de parche.
No consiguió publicar un parche sintácticamente aceptado y entregó un diff
vacío (SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`).
Los registros muestran cursores reutilizados entre consultas incompatibles y
parches con contexto no observado. La auditoría cuenta cero parches propuestos
aceptados para staging; esto no contradice los ocho intentos facturados.
Los dos baselines públicos pasaron. No se ejecutó el oráculo final.

El gate de calibración definido comprueba inferencia real, identidad del worker
y contabilidad cerrada; no exige resolver el issue. Pasó ese alcance técnico.
No demuestra ventaja de E ni resolución oficial de SWE-bench.

## Sellado y siguiente alcance

Se generaron `sealed/SWE-CONTRACT.json` (`status=sealed`,
`launch_enabled=true`), `sealed/SWE-RUN-LOCK.json`, manifiesto de fuentes,
materiales y recibo de custodia en el directorio del intento 2. El contrato de
diseño en `docs/` se conserva; usar la copia sellada al ejecutar.
La plantilla del tokenizer procede de metadatos del GGUF fijado; el worker
comprobó el SHA-256 completo del modelo. Los materiales no incluyen secretos.

El calendario contiene 150 celdas: 96 primarias, 16 de calibración de brazos,
24 de ablación y 14 de memoria (dos donantes). Las 96 primarias por sí solas
no completan el calendario requerido para congelar y evaluar todo el estudio.
La campaña completa no se lanzó en esta entrega. Conviene revisar la usabilidad
de cursores, el feedback de errores y la generación de diffs antes de consumir
horas de campaña; cualquier cambio en fuentes exige renovar gates y sellado.
No modificar esta evidencia ni recalificar el episodio ya terminado.

## Checklist al terminar

- [x] Autenticación Kaggle sin exponer el token.
- [x] Reproducción local de 36/36 huellas con lanzador corregido.
- [x] Inferencia remota y gate técnico de calibración válido.
- [x] Auditoría del episodio: 251 recibos válidos.
- [x] Parada efectiva de Kaggle y procesos locales propios.
- [x] Cinco compuertas verificadas y contrato/run-lock sellados.
- [ ] Parche útil demostrado en esta calibración: diff vacío.
- [ ] Campaña de brazos, ablaciones y memoria ejecutada.
- [ ] Evaluación oficial sellada y gráficas.
- [ ] Ventaja científica y cierre de ECHO-5.1.

## Huellas de evidencia

- `calibration/report.json`: `7e5a76883060d7d151c16b965dd8ac4c61be886e8e1d936f2cc2625858df8f66`.
- `audit-episode.json`: `67a8dbf7290e1d0f500cb658b440cd641fe3fa3e62dfe96d13bb220ee26d7d2b`.
- `kaggle-output/gpu-proposer-results.json`: `03aedd0fc4275c735eb24a4d580a3fd71b6ea56703f6838369c57b0445c35ffb`.
- `sealed/SWE-CONTRACT.json`: `da71cf42265db5eef94ba0cb16a420ffb3ea390e42a4935a54df67f9ed44c0ae`.
- `sealed/SWE-RUN-LOCK.json`: `d3fc4bed28fc3554cd662d33fe39c10e37690696afce23f78ece60771f4551a7`.
