"""Readable summaries of received evidence, never a model's hidden reasoning."""
import json


def short(value, limit=180):
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return text[:limit]


class DecisionView:
    def __init__(self):
        self.clear()

    def clear(self):
        self.rows = {}
        self.origin = "sin fuente"
        self.wins = 0

    def consume(self, event, origin):
        kind = event.get("kind")
        if kind not in ("observation", "decision", "hypothesis", "result", "telemetry"):
            return
        self.origin = origin
        # Views retain only a bounded, latest record per type.
        self.rows[kind] = event
        if kind == "result" and event.get("level_up") is True:
            self.wins += 1

    def lines(self):
        if not self.rows:
            return ["Sin decisiones recibidas. /devtest o /watch conecta una fuente."]
        lines = []
        observation = self.rows.get("observation", self.rows.get("telemetry", {}))
        if observation:
            seen = observation.get("beliefs", observation.get("wsp", observation.get("state")))
            if isinstance(seen, dict) and "pos" in seen:
                seen = ("posición estimada " + short(seen['pos']) + " · destino activo "
                        + (short(seen['target']) if seen.get('target') is not None else 'ninguno')
                        + (" · reglas motoras " + str(len(seen['rule'])) if isinstance(seen.get('rule'), dict) else ''))
            if seen is not None:
                lines.append("Observó: " + short(seen))
            beliefs = observation.get("beliefs")
            if isinstance(beliefs, dict):
                for item in reversed(beliefs.get("recent_hypotheses", [])):
                    if (isinstance(item, list) and len(item) == 3 and
                            isinstance(item[1], list) and len(item[1]) == 2 and
                            item[1][0] == "near" and isinstance(item[1][1], int) and
                            item[2] in ("proposed", "confirmed")):
                        lines.append("Hipótesis visual de meta: color " + str(item[1][1])
                                     + " (" + ("confirmada" if item[2] == "confirmed" else "propuesta") + ")")
                        break
        if self.wins:
            lines.append("Metas alcanzadas en esta sesión: " + str(self.wins))
        decision = self.rows.get("decision", self.rows.get("telemetry", {}))
        hypotheses = self.rows.get("hypothesis", {})
        if hypotheses:
            lines.append("Hipótesis registrada: " + short(hypotheses.get("text", hypotheses)))
        branches = decision.get("branches", [])
        labels = [b["label"] for b in branches if isinstance(b, dict) and isinstance(b.get("label"), str)]
        reason = decision.get("reason", decision.get("rationale"))
        if labels or reason:
            lines.append("Criterio registrado: " + short("; ".join(labels[:2]) if labels else reason))
        elif decision:
            lines.append("Motivo: esta fuente no lo proporcionó.")
        for field, title in (("gate", "Verificación"), ("action_name", "Acción"), ("reward", "Recompensa")):
            if decision.get(field) is not None:
                lines.append(title + ": " + short(decision[field]))
        if "action_name" not in decision and "action" in decision:
            lines.append("Acción: " + short(decision["action"]))
        result = self.rows.get("result")
        if result:
            fields = {k: result[k] for k in ("step", "changed", "game_over", "level_up", "reward") if k in result}
            lines.append("Resultado registrado: " + short(result.get("text", fields or result)))
        return lines or ["Evento recibido sin campos de explicación compatibles."]

    def explain(self):
        return "Últimos registros · " + self.origin + "\n" + "\n".join(self.lines())
