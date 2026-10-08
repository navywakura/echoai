"""Passive ARC decision recorder. Original agent and runner sources stay frozen.

Development only: tracing adds wall time, so this is not a scored campaign.
python -m echo_arc.observe gym --seeds 0 1 --budget 240
python -m echo_arc.observe offline ENV_DIR --games GAME --budget 500
"""
import argparse
from collections import deque
from datetime import datetime, timezone
import hashlib
import json
import linecache
from pathlib import Path
import sys
import time
from types import FunctionType
import uuid


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "echo45-arc-decisions-v1"


def branch_label(method, text):
    """Spanish labels for executed action assignments, not inferred intentions."""
    if 'act = ("K", fresh_keys[0], None)' in text:
        return "Explora una tecla poco probada"
    if 'act = ("K", plan[0], None)' in text:
        return "Ejecuta el primer paso de una ruta calculada"
    if 'act = ("K", alt, None)' in text:
        return "Sustituye una tecla de reinicio costosa por una alternativa"
    if 'return ("C", 6, xy)' in text:
        return "Ejecuta el siguiente clic del plan"
    if 'return self.path.popleft()' in text:
        return "Ejecuta el siguiente paso de una ruta almacenada"
    if 'return path[0]' in text:
        return "Ejecuta el primer paso de una ruta de exploración"
    if 'return self.rng.choice' in text:
        return "Elige al azar entre acciones permitidas"
    if 'return act' in text and method == "Arc3Echo.choose":
        return "Prueba una acción pendiente que no figura como mortal"
    if 'return ("K", k, None)' in text and method == "Arc3EchoV57.choose":
        return "Prueba deliberadamente una tecla de modo"
    if 'return ("K", k, None)' in text and method == "Arc3EchoV5.choose":
        return "Usa el paso calculado para explorar o probar una causa"
    return None


def plain(value):
    """Copy existing values to JSON; never ask the agent to recompute a belief."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, deque)):
        return [plain(v) for v in value]
    if isinstance(value, set):
        return [plain(v) for v in sorted(value, key=repr)]
    if hasattr(value, "item"):
        return plain(value.item())
    raise TypeError(f"unrecordable value: {type(value).__name__}")


def snapshot(agent):
    data = vars(agent)
    names = ("me", "pos", "target", "rule", "pred", "hold", "reset_keys",
             "useful_colours", "events", "level", "pending", "to_try", "temporal_state")
    out = {k: plain(data[k]) for k in names if k in data}
    out["path_remaining"] = len(data.get("path", ()))
    out["clicks_remaining"] = len(data.get("click_plan", ()))
    out["hypotheses_count"] = len(data.get("hypotheses", ()))
    out["recent_hypotheses"] = plain(data.get("hypotheses", [])[-6:])
    return out


class Journal:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Each session owns a new file. Never append to a sealed experiment.
        self.file = self.path.open("x", encoding="utf-8")
        self.prev = "0" * 64
        self.index = 0

    def write(self, **event):
        row = dict(schema=SCHEMA, index=self.index, time=datetime.now(timezone.utc).isoformat(),
                   prev=self.prev, **event)
        raw = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        self.prev = hashlib.sha256(raw.encode()).hexdigest()
        row["hash"] = self.prev
        self.file.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        self.file.flush()
        self.index += 1

    def close(self):
        self.file.close()


class ObservedAgent:
    """Forward every read/write to the real actor; keep observation outside it."""
    def __init__(self, actor, journal, delay=0):
        object.__setattr__(self, "_actor", actor)
        object.__setattr__(self, "_journal", journal)
        object.__setattr__(self, "_delay", delay)
        object.__setattr__(self, "_step", 0)

    def __getattr__(self, name):
        return getattr(self._actor, name)

    def __setattr__(self, name, value):
        # Runner assignments, including level_start and level_actions, matter.
        setattr(self._actor, name, value)

    def observe_state(self, frame):
        from echo_arc.agent import frame_hash
        state = self._actor.observe_state(frame)
        self._journal.write(kind="observation", step=self._step, state=state,
                            frame=frame_hash(frame), beliefs=snapshot(self._actor))
        return state

    def choose(self, state):
        before = snapshot(self._actor)
        returns = []
        branches = []
        actor = self._actor
        sources = {str(ROOT / "echo_arc" / name): linecache.getlines(str(ROOT / "echo_arc" / name))
                   for name in ("agent.py", "temporal_agent.py")}
        previous = sys.gettrace()
        if previous is not None:
            raise RuntimeError("decision tracing requires a process without another Python tracer")

        def trace(frame, event, arg):
            source = frame.f_code.co_filename
            if source not in sources or frame.f_locals.get("self") is not actor:
                return None
            # Returns give the actual selected branch, including inherited choose().
            frame.f_trace_lines = frame.f_code.co_name == "choose"
            if event == "line" and frame.f_code.co_name == "choose":
                label = branch_label(frame.f_code.co_qualname, sources[source][frame.f_lineno - 1])
                if label:
                    branches.append(dict(label=label, method=frame.f_code.co_qualname, line=frame.f_lineno))
            if event == "return" and frame.f_code.co_name in (
                    "choose", "_plan", "_plan_clicks", "_frontier_step", "_cause_step", "_goal",
                    "_walk_exact", "_temporal_step"):
                returns.append(dict(method=frame.f_code.co_qualname, line=frame.f_lineno,
                                    value=plain(arg)))
            return trace

        try:
            sys.settrace(trace)
            act = actor.choose(state)
        finally:
            sys.settrace(previous)
        object.__setattr__(self, "_step", self._step + 1)
        self._journal.write(kind="decision", step=self._step, state=state,
                            action=plain(act), before=before, after=snapshot(actor),
                            returns=returns, branches=branches)
        if self._delay:
            time.sleep(self._delay)
        return act

    def learn(self, state, act, next_state, game_over, level_up):
        before = snapshot(self._actor)
        result = self._actor.learn(state, act, next_state, game_over, level_up)
        self._journal.write(kind="result", step=self._step, action=plain(act),
                            changed=next_state != state, game_over=bool(game_over),
                            level_up=bool(level_up), before=before, after=snapshot(self._actor))
        return result


def observed_play(env, budget, seed, journal, *, agent_name="v5.7", delay=0, deadline=None):
    """Use the original play bytecode with a private factory, no global patch."""
    from echo_arc import runner

    def factory(name):
        if name.startswith("v5.8"):
            from echo_arc.temporal_runner import agent_class
            cls = agent_class(name)
        else:
            cls = runner.agent_class(name)
        return lambda *a, **kw: ObservedAgent(cls(*a, **kw), journal, delay)

    namespace = dict(runner.play.__globals__, agent_class=factory)
    play = FunctionType(runner.play.__code__, namespace, runner.play.__name__,
                        runner.play.__defaults__, runner.play.__closure__)
    return play(env, budget, seed, deadline=deadline, agent_name=agent_name)


def run(args):
    from echo_arc import agent, runner
    root = Path(args.out or ROOT / "lab" / "observability" /
                (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]))
    journal = Journal(root / "arc-decisions.jsonl")
    sources = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
               for p in (ROOT / "echo_arc/agent.py", ROOT / "echo_arc/runner.py",
                         ROOT / "echo_arc/observe.py")}
    journal.write(kind="start", origin="DEVELOPMENT", agent=args.agent, budget=args.budget,
                  mission="Completar niveles mediante acciones y resultados observables.", sources=sources)
    print(str(journal.path), flush=True)
    try:
        if args.mode == "gym":
            from seed import arc3gym as gym
            gym.VERSION = args.version
            games = ((f"gym-v{args.version}-train-{s}", lambda s=s: gym.GymEnv(s)) for s in args.seeds)
        else:
            import arc_agi
            arc = arc_agi.Arcade(operation_mode=arc_agi.OperationMode.OFFLINE,
                                 environments_dir=args.env_dir)
            ids = args.games or sorted(e.game_id for e in arc.get_environments())
            games = ((g, lambda g=g: arc.make(g)) for g in ids)
        for game, make in games:
            agent._COMP_CACHE.clear()
            journal.write(kind="game", game=game)
            rec = observed_play(make(), args.budget, runner.seed_for(game), journal,
                                agent_name=args.agent, delay=args.delay)
            journal.write(kind="game_end", game=game, levels=rec["levels_completed"],
                          actions=len(rec["actions"]), resets=rec["resets"])
            (root / (game + ".json")).write_text(json.dumps(rec), encoding="utf-8")
        journal.write(kind="end", status="complete")
    except BaseException as exc:
        journal.write(kind="end", status="failed", error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        journal.close()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mode", choices=("gym", "offline"))
    ap.add_argument("env_dir", nargs="?")
    ap.add_argument("--agent", default="v5.7")
    ap.add_argument("--budget", type=int, default=240)
    ap.add_argument("--seeds", nargs="+", type=int, default=[0, 1, 2, 3])
    ap.add_argument("--version", type=int, choices=(2, 3), default=3)
    ap.add_argument("--games", nargs="+")
    ap.add_argument("--delay", type=float, default=0)
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    if args.budget < 1 or args.delay < 0:
        ap.error("budget must be positive and delay nonnegative")
    if args.mode == "gym" and any(s not in range(40) for s in args.seeds):
        ap.error("observer demo uses training seeds 0..39 only")
    if args.mode == "offline" and not args.env_dir:
        ap.error("offline requires ENV_DIR")
    run(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
