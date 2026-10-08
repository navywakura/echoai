# Ver echoAI pensar (terminal)

Desde la raíz del repo `RXos`:

```bash
cd /path/to/RXos
export PYTHONPATH=.
```

## Un comando (MVP)

```bash
python3 -m echoai.nexus0.demo            # en vivo, 352 turnos, 5 fps
python3 -m echoai.nexus0.demo --short    # 48 turnos (~10 s a 5 fps)
python3 -m echoai.nexus0.demo --fps 8
python3 -m echoai.nexus0.demo --replay   # si ya existe echoai/lab/thought.jsonl
```

Eso **es** verlo pensar: cada fotograma es un turno del bucle rápido.
El córtex está apagado. No hay LLM. `Ctrl-C` para.

El banco entero dura ~70 s a 5 fps (256 turnos de entrenamiento + 64
después de que la trampa se mueve). `--short` basta para ver premio,
trampa y misterio.

## Dos pasos (lo mismo, a mano)

```bash
python3 -m echoai.nexus0.bench --thought
python3 -m echoai.nexus0.view echoai/lab/thought.jsonl --fps 5
```

Un fotograma estático (sin borrar pantalla): `echoai/lab/preview.txt`.

## La placa (navegador, sin servidor)

```bash
python3 -m echoai.nexus0.bench --thought
python3 -m echoai.nexus0.board echoai/lab/thought.jsonl
xdg-open echoai/lab/board.html      # o arrástralo al navegador
```

Un solo fichero, CSS y JS dentro, sin red: CAM, WSP, T, Q, GATE, ATTEND,
CORTEX y ORACLE encendiéndose turno a turno. Flechas ← → o `play`. Lee el
mismo jsonl que `view`; no habla con el bucle.

`--follow` en `view` hace `tail -f` del jsonl. El banco termina en
milisegundos, así que para un humano el modo útil es `demo` (pausa
entre turnos), no dos terminales compitiendo.

## La placa en vivo (GUI-2)

Una página abierta con `file://` no puede ver crecer un fichero. Por eso
el modo vivo levanta un servidor de la stdlib en el loopback y la página
le pregunta cada 200 ms por los turnos que aún no tiene.

```bash
# terminal 1 — la placa, antes incluso de que exista el log
python3 -m echoai.nexus0.board echoai/lab/thought.jsonl --follow
# http://127.0.0.1:8765/  poll 200 ms  route /turns.json
# --port N y --poll MS si hacen falta. Ctrl-C apaga.

# terminal 2 — el bucle escribiendo
python3 -m echoai.nexus0.demo --short --log echoai/lab/thought.jsonl
# o, de un tirón: python3 -m echoai.nexus0.bench --thought
```

Solo `127.0.0.1`, y no es una opción: una placa alcanzable desde otra
máquina sería un servicio, y esto es un instrumento de laboratorio. Dos
rutas y ningún fichero servido por URL. Sin WebSocket, sin segundo
protocolo, sin CDN, sin npm.

La página abre en el último turno y sigue la cola; si retrocedes con las
flechas o el slider, se queda donde la dejaste hasta que vuelvas al
final. Si el log todavía no existe, dice `waiting` y espera.

Sin `--follow` no cambia nada: `board.html` sigue siendo el mismo fichero
autónomo de GUI-1, byte a byte.

## Leyenda

```
G  premio (GOAL)     approach paga +16
T  trampa (THREAT)   approach paga −16, avoid +8
N  misterio (NOVEL)  approach −16 hasta preguntar, +16 después
·  vacío
@  el agente (fila propia: no tapa la N)
<  la acción que tomó
r  recompensa de este turno
```

Barras: `approach / avoid / wait` son los tres valores Q de la celda
donde está. `ATTEND OFF` casi siempre — el córtex solo despertaría 36
de 256 turnos, y en el demo por defecto ni siquiera está enchufado.

El teseracto de `./navi10 --tui` **no** es esto. Eso es otra cara.
