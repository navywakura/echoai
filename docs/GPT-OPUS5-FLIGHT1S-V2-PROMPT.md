# Prompt para Claude Opus 5 — FLIGHT-1S v2

**Tajo:** reparar el protocolo experimental de FLIGHT-1S sin borrar, editar ni
reinterpretar el resultado rojo de v1.  
**Resultado v1:** evidencia válida, `flight1s_green=false`; 22/24 episodios
perturbados superaron 400 mm y 24/24 recuperaron estabilidad.  
**Hipótesis v2:** la suficiencia del estímulo debe acreditarse por la entrada
física observada y por haber sacado al cuerpo de la banda de recuperación, no
por exigir un desplazamiento arbitrario de dos radios al controlador cerrado.  
**Hardware:** ausente. No hay AKD1000 ni AKD1500 en el laboratorio.

Copia desde aquí en Claude Code y ejecútalo desde
`/home/roger/REALRXOS/RXos/echoai`.

---

Implementa, calibra, congela y ejecuta **FLIGHT-1S v2**. No prometas verde. El
objetivo es corregir el defecto de medición que dejó v1 rojo y someter el
protocolo corregido al banco completo.

## 1. Lee antes de modificar

Lee enteros y en este orden:

1. `AGENTS.md` y `CLAUDE.md`.
2. `docs/05-NEXUS-0-SPEC.md` y `docs/02-INVARIANTS.md`.
3. `docs/ECHO-3-ACCEPTANCE.md`.
4. `docs/FLIGHT1S-DESIGN.md`, `docs/FLIGHT1S-RESULTS.md` y
   `docs/GPT-OPUS5-FLIGHT1S-PROMPT.md`.
5. `docs/examples/flight1s/protocol.json` y
   `docs/schemas/flight1s-protocol.schema.json`.
6. Todo `nexus0/flight1s/`, `tests/test_flight1s.py` y
   `tests/test_flight1s_backend.py`.
7. `docs/SIM3-DESIGN.md`, `docs/SIM3-RESULTS.md` y el código SIM-3 que
   FLIGHT-1S importa.

Antes de tocar código, ejecuta y conserva la salida de:

```bash
PYTHONPATH=.. python3 -m echoai.nexus0.flight1s validate
PYTHONPATH=.. python3 -m echoai.nexus0.flight1s audit lab/echo3_flight1s_report.json
PYTHONPATH=.. python3 tests/test_flight1s.py -q
PYTHONPATH=.. python3 tests/test_flight1s_backend.py -q
```

El auditor v1 debe devolver `evidence_valid=true`, 375 comprobaciones, cero
hallazgos y exit 1 porque el informe histórico es rojo. Eso es correcto.

## 2. Conservación obligatoria de v1

No sobrescribas ni regeneres:

- `docs/FLIGHT1S-DESIGN.md`;
- `docs/FLIGHT1S-RESULTS.md` en sus afirmaciones y hashes históricos;
- `docs/examples/flight1s/protocol.json`;
- `docs/schemas/flight1s-protocol.schema.json`;
- `lab/echo3_flight1s_report.json`;
- `lab/echo3_flight1s_audit.json`;
- `lab/flight1s/runtime-lock.json`;
- `lab/flight1s/sweep-round1-1to4N.json`;
- `lab/flight1s/sweep.json`;
- las 48 trazas y los 48 ULog de v1.

Calcula y registra sus hashes antes y después. El auditor histórico debe seguir
reconstruyendo v1 después de añadir v2. Si el despacho de versiones rompe v1,
es un fallo y no se ejecuta el banco v2.

Usa rutas nuevas y explícitas:

```text
docs/FLIGHT1S-V2-DESIGN.md
docs/FLIGHT1S-V2-RESULTS.md
docs/schemas/flight1s-protocol-v2.schema.json
docs/examples/flight1s-v2/protocol.json
lab/flight1s-v2/
lab/echo3_flight1s_v2_report.json
lab/echo3_flight1s_v2_audit.json
```

No hagas commit, push ni deploy. No añadas los ULog a Git.

## 3. Defecto exacto que corrige v2

V1 usa `min_disturb_excursion_mm=400` dentro del grupo `disturbance`. Esa
variable es un resultado del lazo cerrado: depende tanto de la fuerza como de
la rapidez con la que PX4 la rechaza. Dos vuelos recibieron una wrench real,
registraron cocientes de impulso 963 y 957 ppk, salieron de la banda de 200 mm
y recuperaron estabilidad, pero quedaron en 389,4 y 291,7 mm. El criterio los
rechazó por responder demasiado bien.

No soluciones esto bajando 400 hasta que los datos v1 pasen. No cambies el
informe, no filtres los dos episodios y no reutilices el hash de protocolo v1.
Tampoco declares que cualquier wrench solicitada es una perturbación válida.

V2 debe separar tres preguntas:

1. **Aplicación:** ¿el backend aplicó una entrada física no nula y una fuente
   distinta de la declaración observó su efecto?
2. **Desafío:** ¿esa entrada sacó al cuerpo de la banda preregistrada desde la
   que después se mide recuperación?
3. **Recuperación:** ¿PX4 volvió a entrar y permaneció dentro durante el tiempo
   preregistrado, sin cambiar la referencia?

Cada pregunta produce un grupo y un denominador visibles. Ninguna puede
compensar el fallo de otra.

## 4. Diseño v2 antes del código de cierre

Crea primero `docs/FLIGHT1S-V2-DESIGN.md` y el esquema v2. El protocolo debe
tener `schema_version=2` y un perfil nuevo, por ejemplo
`flight1s-x500-v2`. El hash de los bytes de la instancia v2 será el nuevo
freeze.

Mantén cuerpo, PX4, modelos, mundos, guion, fuerza de 5 N durante 600 ms,
condiciones y límites de seguridad de v1 salvo que la calibración A demuestre
que alguno es inviable. Cualquier cambio lleva justificación, barrido propio y
hash nuevo. No ajustes PID.

Sustituye `min_disturb_excursion_mm` como criterio de aplicación por campos que
expresen el contrato separado. Como mínimo:

```text
stimulus.min_impulse_ratio_ppk
stimulus.max_impulse_ratio_ppk
challenge.recovery_radius_mm
challenge.exit_margin_mm
recovery.radius_mm
recovery.hold_ms
recovery.timeout_ms
```

Punto de partida defendible para preregistro, que debes justificar antes de
volver a medir A:

- `min_impulse_ratio_ppk=500`: al menos la mitad del impulso esperado aparece
  en el cambio de momento calculado desde el flujo de poses;
- `max_impulse_ratio_ppk=1500`: límite simétrico amplio para detectar unidades,
  aplicación acumulada o ventanas incorrectas;
- el desafío exige `excursion_mm > recovery_radius_mm + exit_margin_mm`;
- `exit_margin_mm` procede de resolución, frecuencia y error de medición, no
  del mínimo observado en B/C; documenta el cálculo y usa un entero;
- recuperación conserva radio 200 mm, permanencia 3.000 ms y timeout 10.000 ms
  mientras A no obligue a un protocolo nuevo razonado.

La razón física de este contrato debe quedar escrita. El impulso mandado es
`F·dt`; con 5 N, 600 ms y masa fijada del X500, documenta también el impulso y
el cambio de velocidad libre equivalentes. No los confundas con el cambio de
momento neto que queda después de la reacción de PX4.

El éxito de `/wrench/persistent` y una publicación registrada son necesarios,
pero no suficientes. La medida independiente continúa viniendo del flujo de
poses del backend. Declara su limitación: la velocidad es una diferencia
finita, no un sensor independiente, y el controlador también influye en el
cambio de momento neto.

## 5. Calibración A más grande

No uses los mínimos de B/C v1 para elegir bandas v2. Esos resultados ya son
públicos y v2 debe rotularse como reparación de un banco rehearsal, no como un
nuevo examen ciego de generalización.

Antes de congelar v2, ejecuta en los cuatro mundos A al menos:

- 8 repeticiones frescas nominales por mundo;
- 8 repeticiones frescas perturbadas por mundo;
- controles `force_declared_without_wrench` repartidos por los cuatro mundos;
- procesos frescos, orden permutado por una seed nueva y un solo runtime lock.

Publica todas las rondas, también las fallidas. La calibración debe comprobar:

- separación entre el control sin fuerza y la fuerza real en cociente de
  impulso;
- que el cuerpo sale de la banda de recuperación con el margen definido;
- actitud dentro del límite;
- recuperación completa;
- dispersión por mundo y repetición, no sólo mediana agregada.

Los valores de 500 y 1500 ppk sólo pueden cambiar si el diseño fija de antemano
una regla matemática que usa exclusivamente A y controles negativos. No elijas
un umbral mirando el mínimo que deseas aceptar. Si la calibración no deja una
separación limpia o no reta la banda, conserva el rojo y detente antes de B/C.

Congela después de A:

- protocolo v2 y SHA-256;
- lock de runtime v2 y SHA-256 de código;
- seed de orden del banco;
- bandas y tolerancias;
- denominadores;
- lista exacta de mutantes.

## 6. Banco v2

Tras el freeze, ejecuta el mismo banco completo de 12 mundos × 2 condiciones ×
2 repeticiones = 48 episodios. No ramifiques por mundo, split, seed o resultado.
No reutilices procesos entre episodios y no descargues nada durante el banco.

El verde v2 exige como mínimo:

```text
48/48 episodios completos
24/24 perturbados con wrench exactamente una vez y retirada registrada
24/24 perturbados dentro de la banda de impulso v2
24/24 perturbados fuera de la banda de recuperación más su margen
24/24 perturbados recuperados dentro del timeout y estables durante 3 s
 0 teleports, replay, contacto no autorizado, NaN/Inf o regresión de reloj
 1 lock y 1 protocolo v2 en los 48 episodios
controles, mutantes, repetición y regresiones en verde
```

No uses la excursión como sustituto de fuerza aplicada. Sí úsala para demostrar
que hubo un desafío fuera de la banda desde la que se afirma recuperación.
Conserva y publica excursión, pico de velocidad, actitud y esfuerzo de
actuadores como resultados; no permitas que una mediana o un agregado oculten
un episodio fallido.

El banco usa los mundos rehearsal ya vistos. Describe el verde, si ocurre,
como reproducción con un protocolo reparado sobre esos doce mundos. No lo
presentes como evaluación reservada ni como sim-to-real.

## 7. Auditor y mutantes

El auditor v2 debe recalcular desde trazas y ULog, sin confiar en
`flight1s_green`:

- los 48 episodios y su orden;
- hashes de protocolo, lock, mundo, traza y ULog;
- publicación y retirada de wrench;
- impulso esperado y cociente observado;
- salida de la banda con margen;
- recuperación y permanencia;
- reloj, contactos, firma PX4 y ausencia de datos hacia echoAI.

Añade controles positivos y mutantes que demuestren cada frontera:

- fuerza declarada sin wrench;
- wrench publicada pero traza de pose inmóvil/reproducida;
- impulso alterado en informe;
- wrench acumulada varias veces;
- ventana o unidades de fuerza manipuladas;
- excursión que nunca sale de la banda pero se declara recuperada;
- recuperación calculada antes de finalizar la perturbación;
- `exit_margin_mm` o bandas relajadas sólo en el informe;
- episodio rojo omitido;
- mezcla de protocolo, lock o código v1/v2;
- teleport, controlador fixture, reloj congelado y descarga de red.

Los mutantes del informe parten de una copia positiva válida. Verificar que una
evidencia ya roja continúa roja no acredita el auditor.

## 8. Compatibilidad y pruebas

La CLI debe admitir versiones explícitas sin cambiar el significado de v1. Por
ejemplo:

```bash
PYTHONPATH=.. python3 -m echoai.nexus0.flight1s validate --protocol docs/examples/flight1s-v2/protocol.json
PYTHONPATH=.. python3 -m echoai.nexus0.flight1s preflight --protocol docs/examples/flight1s-v2/protocol.json --output lab/flight1s-v2/runtime-lock.json
PYTHONPATH=.. python3 -m echoai.nexus0.flight1s bench --protocol docs/examples/flight1s-v2/protocol.json --rehearsal --output lab/echo3_flight1s_v2_report.json
PYTHONPATH=.. python3 -m echoai.nexus0.flight1s audit lab/echo3_flight1s_v2_report.json
```

Si la interfaz actual no acepta `--protocol`, añádela con default v1 para no
romper comandos históricos. No dupliques el supervisor entero.

Ejecuta:

```bash
PYTHONPATH=.. python3 tests/test_flight1s.py -q
PYTHONPATH=.. python3 tests/test_flight1s_backend.py -q
PYTHONPATH=.. python3 tests/test_sim3.py -q
```

Añade pruebas v2 para esquema, despacho de versión, separación de grupos,
freeze, auditor, mutantes y compatibilidad v1. Ejecuta la regresión NEXUS-0
establecida por el repositorio. Un fallo de dependencia es `not_run`, nunca
`pass`.

No toques `loop.Agent`, WSP, CAM, T, Q, PATTERN, gate, GUI, kernel, ISO,
drivers ni userland. No actives un LLM. echoAI permanece desconectado y el
informe conserva `agent_in_gazebo=false`, `cortex_calls=0`, `wsp_writes=0`.

## 9. Entrega

Entrega:

1. diseño, esquema y protocolo v2;
2. implementación compatible con v1 y tests;
3. calibración A completa, incluidos intentos rojos;
4. freeze y lock v2;
5. informe de 48 episodios, trazas, ULog y auditoría;
6. `docs/FLIGHT1S-V2-RESULTS.md` con denominadores, intervalos, fallos y
   comandos exactos;
7. una nota al principio de `docs/FLIGHT1S-RESULTS.md` que enlace v2 sin
   alterar el resultado v1;
8. actualización mínima de `NOW.md` y `ROADMAP.md` según lo realmente medido.

Antes de terminar responde:

- ¿qué criterio concreto cambió entre v1 y v2 y por qué no es una relajación
  retrospectiva del rojo?
- ¿qué resultados de v1 permanecen intactos y auditables?
- ¿cómo separas aplicación, desafío y recuperación?
- ¿qué datos se usaron para calibrar y cuáles sólo para evaluar?
- ¿PX4 siguió siendo la autoridad de vuelo?
- ¿el mismo guion y binario corrieron en los doce mundos?
- ¿algún dato privado llegó a WSP o a echoAI?
- ¿qué capacidad exacta demuestra el resultado y qué queda fuera?

Si cualquier criterio falla, conserva el informe rojo. No muevas el umbral,
no repitas sólo los episodios fallidos y no declares cerrado FLIGHT-1S.
