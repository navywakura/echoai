"""Named connection references. Never persist or inspect a credential's contents."""
from pathlib import Path
import re

from .transport import Cortex


def name(value):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,47}", value):
        raise ValueError("Nombre: 1–48 letras, números, guiones o guiones bajos")
    return value


def profile(value):
    mode = value.get("mode")
    if mode == "local":
        result = {"mode": mode, "path": str(Path(value["path"]).expanduser().resolve())}
        if value.get("server"):
            result["server"] = value["server"]
        return result
    if mode == "opencode":
        model=value.get("model", "")
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[^\s]+", model):raise ValueError("OpenCode model: provider/model")
        return {"mode":mode,"model":model}
    if mode not in ("api", "anthropic"):
        raise ValueError("Tipo de conexión desconocido")
    c = Cortex(value["url"], value["model"], value.get("key_env"),
               "anthropic" if mode == "anthropic" else "openai", key_file=value.get("key_file"))
    return {"mode": mode, "url": c.url, "model": c.model, "key_env": c.key_env, "key_file": c.key_file}


def parse(args):
    if not args:raise ValueError("/connect api|anthropic|openrouter|local|opencode …")
    if args[0] == "opencode" and len(args)==2:
        value={"mode":"opencode","model":args[1]}
    elif args[0] == "openrouter" and len(args) in (1, 2, 3):
        model = args[1] if len(args) >= 2 else "openrouter/free"
        if model == "free": model = "openrouter/free"
        value = {"mode": "api", "url": "https://openrouter.ai/api/v1", "model": model}
        if len(args) == 3:
            ref = args[2]
            value["key_file" if ref.startswith("@") else "key_env"] = ref[1:] if ref.startswith("@") else ref
    elif args[0] == "local" and len(args) in (2, 4):
        value = {"mode": "local", "path": args[1]}
        if len(args) == 4:
            if args[2] != "--server":
                raise ValueError("/connect local PATH [--server EXECUTABLE]")
            value["server"] = args[3]
    elif args[0] in ("api", "anthropic") and len(args) in (3, 4):
        value = {"mode": args[0], "url": args[1], "model": args[2]}
        if len(args) == 4:
            credential = args[3]
            value["key_file" if credential.startswith("@") else "key_env"] = (
                credential[1:] if credential.startswith("@") else credential)
    else:
        raise ValueError("/connect local PATH [--server EXE] | api URL MODEL [KEY_ENV|@KEY_FILE]")
    return profile(value)


def describe(value):
    p = profile(value)
    if p["mode"] == "local":
        return "GGUF · " + p["path"]
    if p["mode"]=="opencode":return "OpenCode · "+p["model"]+" · asesor sin herramientas"
    auth = "archivo vinculado" if p.get("key_file") else "variable de entorno" if p.get("key_env") else "sin clave"
    return f"{p['model']} · {p['url']} · {auth}"
