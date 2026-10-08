# 03 — Hipótesis y arquitectura

## Hipótesis científica

echoAI es un agente cognitivo híbrido de dos escalas temporales en el
que una representación discreta compartida (WSP / Q_N) conecta
percepción, memoria, predicción y acción; un sistema rápido entero
mantiene el estado, aprende de consecuencias y ejerce control; un
sistema cortical lento genera hipótesis y planes; y un mecanismo de
verificación y veto impide que las hipótesis del córtex se conviertan
directamente en hechos o acciones.

Núcleo (córtex fuera salvo incertidumbre / novedad / complejidad):

```
S_t → A_t → Ŝ_{t+1} → S_{t+1} → δ_t → learning
```

## Por qué no “LLM más grande”

El salto no viene de parámetros. Viene de que el ciclo de arriba
**siga vivo con la LLM apagada**. Eso ataca huecos reales de agentes
actuales: reactividad, memoria persistente, predicción, aprendizaje
online, selección de acción, incertidumbre, planificación, adquisición
activa de información — sin un `AGI_SCORE`.

## Diagrama fundacional

```
          PERCEPCIÓN
              ↓
        REPRESENTACIÓN          (WSP + Q_N vertex)
              ↓
         ┌────┴────┐
         │         │
    ¿QUÉ ES?   ¿LO SÉ?          epistemología
         │         │
         │      VERIFY
         │         │
         └────┬────┘
              ↓
          PREDICCIÓN            T(s,a) → ŝ'
              ↓
          PROPUESTA             Q(s,·)  [córtex OFF en NEXUS-0]
              ↓
           GATE                 OK | MODIFY | BLOCK
              ↓
            ACTO                UNIR | TEMER | OBSERVAR
              ↓
          RESULTADO
              ↓
          APRENDIZAJE           δ → Q ; episodio → CAM
```

## Firewall epistémico (regla de primer nivel)

```
FACT CHANNEL:        WSP → CAM → VERIFY | DESCONOCIDO
HYPOTHESIS CHANNEL:  WSP → cortex → proposal (también WSP)
```

No se cruzan sin comprobación. La prosa más convincente no convierte
UNKNOWN en FACT.

## Fast Control Substrate

Nombre que sustituye a “cerebro reptiliano”:

```
Q6/Q_N , CAM , E[6] , STDP , Q-table , GATE , WSP
```

AKD1000 = acelerador de **algunas** poblaciones de ese sustrato, no
el sustrato.

## E[6] como neuromodulación (ya existe)

No hay dict float `internal_state`.

| Eje | Letra | Control |
|---|---|---|
| valence | V | no se sobrecarga con δ |
| arousal | A | extra I_STIM (`A // 20`) |
| dominance | D | reservado |
| certainty | C | C < 20 plasticidad ON |
| urgency | U | U ≥ 60 geodésica Hamming |
| bond | B | reservado |

Curiosidad **sin** un 7º float:

```
surprise = d_H(ŝ', s')
novelty  = CAM miss
```

novedad alta + surprise alto → almacenar / (más tarde) despertar córtex.
novedad baja + surprise bajo → no molestar al córtex.

## Atención al córtex (NEXUS-4, no 0)

```
ATTEND = MISS ∨ UNCERTAIN ∨ NOVEL ∨ CONFLICT ∨ GOAL_COMPLEX ∨ HUMAN
```

CAM hit ∧ VERIFY ∧ C alta ∧ acción conocida → **NO LLM**.

## WSP + Q_N como espacio cognitivo (no solo ECC)

Hoy Q6 demuestra atractor + codebook → corrección 48/48. Eso no es
inteligencia. NEXUS-0 empieza a usarlo como **mapa discreto**:

```
WSP  YO → DESEAR → OBJETO
        ↓
Q_N  vertex = 0x39AF
        ↓
CAM  state, action=UNIR, reward, next=0x1A20
Q    Q(slot, UNIR) = …
T    T(slot, UNIR) → next
```

Las experiencias quedan conectadas por acciones. El hipercubo pasa de
corrector de errores a **espacio de estados navegable** (NEXUS-1/2
terminan eso: search over cognitive states).

## World model entero (no transformer)

```
T(s, a) → ŝ'
e_t = d_H(ŝ', s')
```

s = ranura CAM / estado discreto, a ∈ {0,1,2}. Interpretable. 12 KiB
de Q + 24 KiB de T (uint16 × 4096 × 3). Si no gana a “predecir el
mismo vértice”, no se publica como world model.

Contrafactuales (NEXUS-2): evaluar T(S,A), T(S,B), T(S,C) y elegir.
**Sin LLM.**

## δ y separación memoria / valor

No meter δ en E[V]. Tabla estática:

```
int8_t Q[4096][3];   /* 12288 B */
```

```
δ = r + γ max_a Q(s',a) − Q(s,a)
γ = 7/8
Q ← clip_i8(Q + α δ)
```

CAM = what happened. Q = what should I do.

## UNKNOWN → PREGUNTAR (NEXUS-3, no 0)

DESCONOCIDO deja de ser solo un fallo: puede emitir `rel=PREGUNTAR`
sobre la variable que bloquea el goal. Adquisición activa de
información. Fuera de NEXUS-0.

## Sueño / consolidación (NEXUS-5, no 0)

```
WAKE:  perceive, act, learn
SLEEP: chat.jsonl / episodios → reglas T(s,a) estables → CAM/Q
```

experiencia repetida S,A → S' se comprime a regla semántica. No en 0.

## Riesgo mayor

No es Akida. No es la LLM. Es **sedimentación** (navi5→10). Si un
componente no participa en

```
state → prediction → action → outcome → learning
```

no entra al núcleo.

## Yo / self-model

No se implementa. Puede emerger del registro
(STATE, GOAL, ACTION, RESULT, PREDICTION, ERROR, HISTORY).
Prohibido `I_AM_A_PERSON` en NEXUS-0.
