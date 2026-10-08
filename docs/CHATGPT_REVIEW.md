# ChatGPT researcher vs laboratorio (2026-09-03)

Respuesta a la lectura de `docs/ECHOAI_FOR_CHATGPT.md`.
Método: cada propuesta se marca **ya está** / **sí, siguiente** / **más tarde** / **no**.

## Tesis de ChatGPT — se acepta

EchoAI no se investiga como “SNN + LLM”. Se investiga como agente situado:

WSP/QN espacio · CAM memoria · T dinámica · Q política · ATTEND gasto · córtex hipótesis vetable.

El resultado que importa no es T=0.9964 en el anillo uniforme. Es **JUMP: T aprende una estructura que i±1 no conoce**, y **preguntar cambia el valor (+80/−80)**, y **no pensar siempre (36/256)**.

La prueba seria de generalización: cambiar la topología y ver qué se reaprende. Eso es más AGI-relevante que enchufar un LLM o Akida.

## Ya está en el código (no reinventar)

| Propuesta ChatGPT | Dónde |
|---|---|
| T(s,a)→s' + conteo | `world.py`: `n`, `alt`, `conflicts` |
| Surprise ≈ d_H(ŝ',s') | `loop.py` `surprise` / `pred_ham_sum` |
| Novelty ≈ miss / kind NOVEL | CAM + KIND_NOVEL |
| δ reward error | `qtable.update` |
| PREGUNTAR ≠ 4ª marcha | `_ask()` antes del gate, no `env.step` |
| Córtex no inventa s' | stub no predice estado; T lo hace |
| parse_reply tira prosa | `cortex.parse_reply` |
| Córtex off por defecto | `cortex_calls=0` |
| Akida no es T/Q/VERIFY | `docs/AKIDA.md`, `07-AKIDA.md` |
| Tres relojes (reflejo / modelo / córtex) | Q+gate · T+plan+ask · ATTEND+stub |
| Planner no siempre | `plan_depth=0` default; ATTEND ≠ planner |

## Sí — siguiente experimento (cuando se reanude)

1–8 **cerrados.** Incluido el pasillo (A→B→C→D vs A→B→X→D): el
transferido conoce B al entrar (T=C, conf 3); el control no. Programa
situado cerrado. `plan.py` se queda. `RingEnv.ask()` no existe.

6. **CortexROI** — más tarde, cuando el córtex no sea el stub (ROI≈0 hoy).
   No es deuda de este MVP.

## Más tarde (no ahora)

- Sleep / consolidación (NEXUS-5). ChatGPT está de acuerdo.
- Ciclo de vida 1 / 100 / 1000 observaciones como umbrales mágicos — primero T_CONF.
- LLM que proponga acciones (solo tras escalada y parse_reply).
- Akida en sensing, nunca en VERIFY.
- IG(question) como fórmula; el +80/−80 **ya es** IG medido en recompensa. No inventar un float IG_q.

## No

- Publicar T=0.9964 como world model (el lab ya no lo hace).
- Planner siempre on.
- Córtex que predice s'.
- Portar T/Q/CAM a AKD1000.
- Cerebro reptiliano / NEXUS de directorios biológicos.
- AGI como KPI de un slice.

## Hipótesis que ChatGPT deja y el lab puede firmar

> Intelligence ≈ representation + memory + prediction + action + learning + information acquisition.

Y la prueba que pide, que el lab ya casi formuló:

> echoAI cambia su comportamiento **correctamente** después de descubrir que su modelo del mundo estaba equivocado — en un mundo que **no** sea solo el anillo de 32, conservando preguntar / planificar-si-hace-falta / córtex-caro.

El primer sitio donde eso **ya pasó** en miniatura: JUMP (T se equivoca vs i±1 y gana) y fase F (una transición rancia, conflicts=1). El siguiente sitio serio: **cambiar el pasillo**.
