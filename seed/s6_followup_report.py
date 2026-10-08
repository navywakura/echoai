"""Publish bounded B6/B7 closures only after their independent audits finish."""
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import time

from seed.game_selfimprove import atomic

REPO = Path(__file__).resolve().parents[1]
ROOTS = (("B6", "s6b6-20260928"), ("B7", "s6b7-20260929"))


def report():
    results = {}
    for label, directory in ROOTS:
        root = REPO / "lab/seed" / directory
        pilot = json.loads((root / "pilot.json").read_text())
        audit = json.loads((root / "audit.json").read_text())
        inference = json.loads((root / "inference-audit.json").read_text())
        assert audit["valid"] and inference["valid"]
        assert pilot["profile_sha256"] == audit["profile_sha256"] == inference["profile_sha256"]
        outcome = "PROMOVIDO" if pilot["promote"] else "SIN PROMOCIÓN"
        lines = [f"# S6-{label} · piloto {outcome}", "",
                 "Medición y auditoría independiente completas. **S6 todavía no está VERDE**: este piloto no abre examen ni sustituye B1–B5.", "",
                 "| Brazo | Suma A de las tres parejas |", "|---|---:|",
                 f"| FIJO | {pilot['paired_A']['fijo']} |", f"| ECHO | {pilot['paired_A']['echo']} |", "",
                 f"Aceptaciones ECHO en la historia de esta condición: **{pilot['accepted_echo']}**. Promoción: **{outcome}**.", "",
                 "| Brazo | Nuevas propuestas de esta etapa | Veredictos |", "|---|---:|---|"]
        for arm in ("fijo", "echo"):
            rows = [r for r in pilot["verdicts"] if r["arm"] == arm]
            lines.append(f"| {arm.upper()} | {len(rows)} | {dict(Counter(r['verdict'] for r in rows))} |")
        lines += ["", "A tiene 40 partidas por pareja y 200 niveles posibles; las sumas anteriores agregan tres réplicas de políticas sobre A. No son resultados ARC oficiales ni un examen nuevo.", "",
                  "B de desarrollo se conserva protegido: los prompts solo reciben la señal de rechazo, sin partidas, índices ni resultados B. Las propuestas humanas de controles anteriores no entraron en los prompts.", "",
                  "La auditoría reconstruye las peticiones, las respuestas y los veredictos en procesos nuevos; valida fuentes, replay y composición de las políticas. La comprobación adicional de inferencia compara el JSON decodificado y reconstruye exactamente el wrapper original, conservando su serialización y hash.", "",
                  "No se redujeron umbrales ni se transformó un rechazo en aceptación. GPU gratuita, pago desactivado; no se reabre B5 ni se consume un examen final para escoger una política.", "",
                  f"[Contrato](ECHO45-S6-{label}-DESIGN.md) · [Piloto](../lab/seed/{directory}/pilot.json) · [Auditoría](../lab/seed/{directory}/audit.json) · [Inferencia](../lab/seed/{directory}/inference-audit.json).", ""]
        if label == "B6":
            lines[2:2] = ["FIJO consiguió una reparación +3 A sin regresión protegida. ECHO consiguió +8 A, pero falló conservación B; se rechazó. Ocho de las doce propuestas conservaron HOLD=40, el valor nativo.", ""]
        else:
            lines[2:2] = ["B7 añade un paso real de refinamiento por pareja, con su propio feedback después de B6. Ocho llamadas nuevas (seis propuestas y dos calibraciones); historia total de 22 llamadas. La condición B6 se conserva cerrada por separado.", ""]
        (REPO / "docs" / f"ECHO45-S6-{label}-RESULTS.md").write_text("\n".join(lines))
        atomic(root / "status.json", {"at": datetime.now(timezone.utc).isoformat(), "stage": "CLOSED",
               "pilot_promoted": pilot["promote"], "accepted_echo": pilot["accepted_echo"],
               "paired_A": pilot["paired_A"], "audit_valid": True, "exam_opened": False, "s6_green": False})
        results[label] = {"promote": pilot["promote"], "accepted_echo": pilot["accepted_echo"], "paired_A": pilot["paired_A"]}
    final = results["B7"]
    notice = (f"S6-B6/B7 cerrados y auditados; B7 ECHO {final['paired_A']['echo']} frente a FIJO {final['paired_A']['fijo']}, "
              f"aceptaciones ECHO {final['accepted_echo']}; " + ("piloto promovido, examen final pendiente." if final["promote"] else "sin promoción; examen final sin abrir."))
    for filename in ("NOW.md", "STATUS.md", "ECHO45-ECHO5-ROADMAP.md"):
        p = REPO / "docs" / filename
        value = p.read_text().replace("S6-B6 cerrado sin promoción (auditoría en curso); S6-B7 ejecutando un refinamiento limitado desde feedback real.", notice)
        p.write_text(value)
    p = REPO / "docs/ECHO45-RECOVERY-20260929.md"
    p.write_text(p.read_text() + "\n## Cierre de S6 de esta sesión\n\n" + notice +
                 " [B6](ECHO45-S6-B6-RESULTS.md) · [B7](ECHO45-S6-B7-RESULTS.md).\n")
    atomic(REPO / "lab/seed/recovery-20260929-closure.json", {"at": datetime.now(timezone.utc).isoformat(),
           "memory_green": True, "memory_audit": "lab/seed/village3-receipts-20260929/audit.json",
           "s6": results, "s6_green": False, "all_echo45_green": False})
    print(json.dumps(results), flush=True)


if __name__ == "__main__":
    while not all((REPO / "lab/seed" / name / "audit.json").exists() for _, name in ROOTS):
        time.sleep(10)
    memory = json.loads((REPO / "lab/seed/village3-receipts-20260929/audit.json").read_text())
    assert memory["green"] and memory["M6"]
    report()
