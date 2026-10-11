# Ejecución local de ECHO-5

Se conserva el entorno base `.venv` con CPython 3.12.13. MiniGrid/BabyAI utiliza
`.venv-sandbox` y las ruedas fijadas por hash en `requirements-sandbox.lock`.
El núcleo no necesita un LLM ni conectividad de red para estas pruebas.

```sh
cd ECHO-5
python3.12 -I scripts/setup_sandbox.py
.venv/bin/python -I scripts/background.py checks
.venv/bin/python -I scripts/background.py panel
```

Cada lanzamiento imprime PID, comando, directorio de salida y log. El trabajo
queda en segundo plano y se conserva al cerrar el terminal; suspender o apagar
la máquina detiene el cómputo. Los recibos sólo declaran `valid` al terminar.
No se sobrescriben campañas existentes. Cuatro procesos de evaluación como
máximo, sin servicios cloud ni gasto de GPU.

El panel se abre en **http://127.0.0.1:8765**. También acepta
**http://echoai.localhost:8765** en navegadores que resuelven `*.localhost`.
`echoai.internal` necesitaría una entrada DNS o de hosts del equipo; el
programa no cambia su configuración global. Sólo escucha en loopback.

En el panel, elegir mundo, política y semilla crea un episodio de demostración.
La misión usa el verificador nativo del entorno. `Paso` ejecuta una acción;
`Continuar` ejecuta pasos hasta terminar, y `Pausa` detiene el bucle. Un resultado
de demostración no entra en la campaña de confirmación. `thought.jsonl`
conserva los hechos registrados por el actor y el evaluador. La interfaz no
construye un monólogo ni realimenta sus textos al agente.

El mapa representa celdas vistas y recordadas con posición relativa estimada.
Las celdas ocultas siguen desconocidas. El resultado del evaluador aparece al
terminar; no se entrega al actor para decidir. Las hipótesis son estructuras
del programa y deben leerse junto a su evidencia, no como verdades.

La vista neuronal muestra 16 pasos reales de la red histórica `Layer256`.
Su estímulo procede de un hash reproducible de la observación pública. El
hash no codifica semánticamente los objetos. Es un diagnóstico del sustrato,
separado de la política simbólica que actúa en MiniGrid; su tiempo se contabiliza
como observación de la interfaz. El banco asociativo de 500.000 contadores
no se dibuja como si fueran neuronas LIF. No se infiere gasto energético.

El diagnóstico neuronal se puede desactivar antes de crear una misión. Si
falla, se conserva el error real en el diario y la misión puede continuar;
un resultado terminal se persiste antes de intentar dibujar su diagnóstico.
No se sustituyen las mediciones ausentes por animaciones inventadas.

El panel fija su identidad de fuentes al arrancar (`/api/identity`). Una
modificación del runtime, de los módulos históricos o del contrato detiene
las acciones y exige reiniciar el servidor. Restaurar los bytes no borra esa
alerta. Las sesiones conservan identificadores de arranque y sus recibos.
Esto evita mezclar una interfaz antigua con una campaña nueva; no constituye
atestación contra un administrador hostil del equipo.

Cuando los tests e instrumentos de desarrollo pasan:

```sh
.venv/bin/python -I scripts/background.py development --workers 4
.venv/bin/python -I scripts/background.py confirmation --workers 4
.venv/bin/python -I scripts/background.py audit --output /ruta/absoluta/ECHO-5/artifacts/closure-confirmation-FECHA
```

Cada campaña congela contratos y fuentes, archiva los bytes y comprueba que
no cambian. La confirmación tiene semillas reservadas y configuraciones
fijas. Una auditoría válida acredita el resultado registrado, incluidos sus
fallos; la superioridad depende de las puertas científicas de cada contrato.
No modificar las fuentes durante campaña o auditoría. Las pruebas de
transferencia y los episodios nativos se reejecutan en procesos nuevos.

La simulación robótica se lanza por separado, siempre en un directorio nuevo:

```sh
.venv/bin/python -I -B scripts/run_sitl.py availability
.venv/bin/python -I -B scripts/run_sitl.py run --phase confirmation --out artifacts/sitl-confirmation-FECHA
.venv/bin/python -I -B scripts/run_sitl.py audit artifacts/sitl-confirmation-FECHA
```

Estos dos últimos comandos también deben lanzarse en segundo plano, con log
y PID registrados. Usan la imagen local fijada por identidad, contenedores
sin red externa y límites de recursos. La confirmación necesita ULog, poses
privadas de Gazebo, ACK, supervisor y parada; las fixtures sintéticas no
sustituyen esos recibos. No hay comunicación con un dron físico. La física
numérica se juzga con tolerancias declaradas; no se promete replay binario.

`scripts/finalize.py` requiere `--campaign`, `--checks`, `--browser`, `--sitl`
y `--output`, todos bajo `artifacts/`. Comprueba que la auditoría, los tests,
la prueba de navegador y la simulación corresponden a las fuentes medidas.
Sólo emite `release_eligible: true` cuando todas las puertas obligatorias
son verdaderas. S6 permanece fuera del alcance hasta después de ECHO-5.5.
