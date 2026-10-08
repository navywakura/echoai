"""E4-BENCH-1 A · the same model with and without ECHO on public benchmarks.

    python -m echoai.echo4.bench1 run   OUT_DIR --split dev|exam [--models ...]
    python -m echoai.echo4.bench1 audit OUT_DIR          (rebuilds everything from receipts)

Contract: docs/ECHO4-BENCH1-A-DESIGN.md (approved by Roger, 2026-09-24).

Arms (SimpleQA, MMLU-Pro):
  M          the model alone (closed book)
  M+R        the model with the SAME Wikipedia extracts ECHO retrieved (no firewall)
  M+R+ECHO   the M+R answer through ECHO's firewall: accepted only if one of ECHO's own
             extracts contains it (VERIFY needs an extract); otherwise "I don't know"
  TRIVIAL    always "I don't know" (control: abstaining alone is worth nothing)
GSM8K: M and M+ECHO. ECHO has no evidence for arithmetic, so it abstains (declared limit).

ECHO never adds knowledge: M+R+ECHO can only keep or drop the M+R answer. This is
checked item by item. Every model response and every Wikipedia extract is stored as a
receipt; the audit recomputes every number from receipts, with no model or network call.
The API key is read from the environment or a key file (echoai/.openrouterkey) and never stored.
"""
import argparse
import hashlib
import json
import os
import re
import sys
import threading
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from echoai.core.cam import Cam
from echoai.core.dag import allocate
from echoai.core.spoke import encode_event
from echoai.core.wsp import pack

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "lab/echo4/bench1-data"
SAMPLES_SHA = "a068c4f5db9223107f2c435a2664d3e86375a679f59d0d155f745e9e1f3b6238"
CONTRACT = ROOT / "docs/ECHO4-BENCH1-A-DESIGN.md"
MODELS = ("qwen/qwen3-30b-a3b-instruct-2507", "google/gemini-3.5-flash", "anthropic/claude-sonnet-5",
          "openai/gpt-5.4-mini", "deepseek/deepseek-v4.1-flash")
OPENROUTER = "https://openrouter.ai/api/v1/chat/completions"
KEY_ENV = "OPENROUTER_API_KEY"
KEY_FILES = (ROOT / ".openrouterkey", Path.home() / ".openrouterkey", Path.home() / ".config/openrouter/key")
WIKI = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "RxLabs-echoAI-bench/0.1 (https://rxlabs.org; knightsys@proton.me)"
IDK = "I don't know"
# Token ceilings. Reasoning models (Gemini 3.5 Flash, DeepSeek-V4.1-Flash) spend hidden tokens
# before answering; a tight ceiling would leave them with an empty answer, counted as not
# attempted: a bias. Non-reasoning models stop as soon as they answer, so this costs nothing.
MAX_SHORT, MAX_MATH = 2048, 4096
EXTRACT_SOURCE, HYPOTHESIS_SOURCE = "bench-wiki-extract", "bench-model-answer"
STOP = set("a an the of in on at to for from by with and or is was were are be been being who what when "
           "where which whose whom how did does do his her its their this that these those as than into "
           "name named called year".split())
IDK_PATTERNS = re.compile(r"\b(i don'?t know|i do not know|unknown|not sure|cannot (?:determine|answer|be determined)|"
                          r"no information|unable to|not enough information|i'?m not certain)\b", re.I)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def sha(data):
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode()).hexdigest()


# ------------------------------------------------------------------ text normalisation

def norm(text):
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode().lower()
    text = re.sub(r"(?<=\d),(?=\d{3}\b)", "", text)           # 1,000 -> 1000
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(w for w in text.split() if w not in ("a", "an", "the"))


def content_tokens(text):
    return [w for w in norm(text).split() if w not in STOP]


def is_idk(text):
    return (not str(text).strip()) or bool(IDK_PATTERNS.search(str(text)))


# ------------------------------------------------------------------ deterministic grader

def grade_short(pred, gold):
    """SimpleQA: correct / incorrect / not_attempted, by normalised match (declared stricter)."""
    if is_idk(pred):
        return "not_attempted"
    p, g = norm(pred).split(), norm(gold).split()
    if not g:
        return "incorrect"
    g_num = [w for w in g if w.isdigit()]
    if g_num and len(g) <= 2:                                   # numeric answers: the number must appear
        p_num = [w for w in p if w.isdigit()]
        return "correct" if set(g_num) <= set(p_num) and len(p_num) <= len(g_num) + 1 else "incorrect"
    ok = all(w in p for w in g) and len(p) <= len(g) + 6
    return "correct" if ok else "incorrect"


LETTER = re.compile(r"\b([A-J])\b")


def grade_letter(pred, gold_letter):
    if is_idk(pred):
        return "not_attempted", None
    m = LETTER.search(str(pred).strip().upper()[:40])
    if not m:
        return "incorrect", None
    return ("correct" if m.group(1) == gold_letter else "incorrect"), m.group(1)


def grade_number(pred, gold):
    if is_idk(pred):
        return "not_attempted"
    m = re.findall(r"final answer\s*[:\-]?\s*\$?\s*(-?[\d,]*\.?\d+)", str(pred), re.I) or \
        re.findall(r"(-?[\d,]*\.?\d+)", str(pred))
    if not m:
        return "incorrect"
    try:
        got = float(m[-1].replace(",", ""))
        want = float(str(gold).replace(",", ""))
    except ValueError:
        return "incorrect"
    return "correct" if abs(got - want) < 1e-6 else "incorrect"


# ------------------------------------------------------------------ datasets

def load_items(split):
    samples = json.loads((DATA / "samples.json").read_text())
    if sha(json.dumps(samples, sort_keys=True, indent=1)) != SAMPLES_SHA:
        raise ValueError("frozen samples differ from the contract")
    import pandas as pd
    for rel, digest in samples["files"].items():
        if sha((DATA / rel).read_bytes()) != digest:
            raise ValueError("dataset file changed: " + rel)
    sq = pd.read_csv(DATA / "simpleqa/simple_qa_test_set.csv")
    mm = pd.read_parquet(DATA / "mmlupro/data/test-00000-of-00001.parquet")
    gs = pd.read_parquet(DATA / "gsm8k/main/test-00000-of-00001.parquet")
    idx = samples[split]
    items = {"simpleqa": [{"id": "sq-%d" % i, "question": sq.iloc[i]["problem"], "gold": str(sq.iloc[i]["answer"])}
                          for i in idx["simpleqa"]],
             "mmlupro": [{"id": "mm-%d" % i, "question": mm.iloc[i]["question"],
                          "options": [str(o) for o in mm.iloc[i]["options"]], "gold": str(mm.iloc[i]["answer"])}
                         for i in idx["mmlupro"]],
             "gsm8k": [{"id": "gs-%d" % i, "question": gs.iloc[i]["question"],
                        "gold": gs.iloc[i]["answer"].split("####")[-1].strip()} for i in idx["gsm8k"]]}
    return items


# ------------------------------------------------------------------ Wikipedia retrieval (with receipts)

_wiki_lock = threading.Lock()


def _wiki_get(params):
    url = WIKI + "?" + urllib.parse.urlencode({**params, "format": "json", "formatversion": 2})
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(4):
        try:
            with _wiki_lock:
                time.sleep(0.2)                                  # be polite to Wikipedia
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except (OSError, ValueError):
            time.sleep(2 * (attempt + 1))
    raise RuntimeError("wikipedia unreachable")


def sentences(text):
    out = []
    for s in re.split(r"(?<=[.!?])\s+|\n+", text):
        s = s.strip()
        while len(s) > 256:
            out.append(s[:256])
            s = s[256:]
        if len(s) >= 20:
            out.append(s)
    return out


def search_queries(question):
    """Wikipedia search needs every word to match, so a whole question often finds nothing.
    Queries are tried in order: keywords, then proper names, then the most distinctive words."""
    words = content_tokens(question)
    names = re.findall(r"\b[A-Z][\w'’-]+(?:\s+[A-Z][\w'’-]+)*", question)
    names = [n for n in names if n.split()[0].lower() not in STOP | {"what", "which", "who", "in", "on"}]
    distinct = sorted(set(words), key=lambda w: (-len(w), w))[:4]
    queries = [" ".join(words[:10]), " ".join(dict.fromkeys(names)), " ".join(distinct)]
    return [q for q in dict.fromkeys(queries) if q.strip()]


def retrieve(question, k_pages=3, k_sentences=8):
    """ECHO's own retrieval: search Wikipedia, keep the sentences that share most words."""
    titles, used = [], None
    for q in search_queries(question):
        hits = _wiki_get({"action": "query", "list": "search", "srsearch": q[:280], "srlimit": k_pages})
        titles = [h["title"] for h in hits.get("query", {}).get("search", [])]
        if titles:
            used = q
            break
    pages, pool = [], []
    for title in titles:
        data = _wiki_get({"action": "query", "prop": "extracts|revisions", "rvprop": "ids", "explaintext": 1,
                          "titles": title, "redirects": 1})
        page = (data.get("query", {}).get("pages") or [{}])[0]
        text = page.get("extract", "") or ""
        revid = (page.get("revisions") or [{}])[0].get("revid")
        pages.append({"title": title, "revid": revid, "sha256": sha(text), "chars": len(text)})
        pool += [(title, s) for s in sentences(text)]
    q = set(content_tokens(question))
    scored = sorted(((len(q & set(content_tokens(s))), -i, t, s) for i, (t, s) in enumerate(pool)), reverse=True)
    chosen = [{"title": t, "text": s} for score, _, t, s in scored[:k_sentences] if score > 0]
    return {"query": question[:280], "search": used, "titles": titles, "pages": pages, "extracts": chosen}


def retrieval_for(items, cache_path):
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    for group in ("simpleqa", "mmlupro"):
        for it in items[group]:
            if it["id"] not in cache:
                cache[it["id"]] = retrieve(it["question"])
                cache_path.write_text(json.dumps(cache, sort_keys=True, indent=1))
    return cache


# ------------------------------------------------------------------ ECHO: facts in CAM, answers as hypotheses

class EchoVerifier:
    """VERIFY needs an extract: an answer is supported only if one of ECHO's own extracts
    contains all its content words. The extracts are facts in ECHO's CAM; the model's
    answer is a hypothesis. No extract, no belief."""

    def __init__(self):
        self.cam, self.n = Cam(), 0

    def _slot(self, has_fact, extract, source):
        raw = pack(src=6, rel=31, dst=3, time=9, domain=9, generator=8, style=110 + (self.n >> 8),
                   slot=0, seq=self.n & 255)
        vertex, latency, _ = encode_event(raw)
        slot, _ = allocate(self.cam, raw, vertex, latency, (0,) * 6, has_fact=has_fact,
                           extract=extract[:256], source=source, key=raw)
        if slot < 0:
            raise RuntimeError("CAM full")
        self.n += 1

    def verify(self, answer, extracts):
        self.cam, self.n = Cam(), 0                               # one fresh memory per question
        for e in extracts:
            self._slot(1, e["text"], EXTRACT_SOURCE)
        self._slot(0, "", HYPOTHESIS_SOURCE)                       # the model's answer: never a fact
        if is_idk(answer):
            return {"status": "unknown", "evidence": None}
        need = content_tokens(answer)
        if not need:
            return {"status": "unknown", "evidence": None}
        for i, s in enumerate(self.cam.slot):
            if s.occupied and s.has_fact and s.source == EXTRACT_SOURCE:
                have = set(content_tokens(s.extract))
                if all(w in have for w in need):
                    return {"status": "supported", "evidence": i}
        return {"status": "unknown", "evidence": None}


# ------------------------------------------------------------------ model client (receipts, key never stored)

def api_key():
    key = os.environ.get(KEY_ENV)
    for path in KEY_FILES:
        if not key and path.is_file():
            key = path.read_text().strip()
    if not key:
        raise SystemExit("no OpenRouter key: set %s or write it to %s (chmod 600)" % (KEY_ENV, KEY_FILES[0]))
    return key


def ask(model, system, user, *, max_tokens, key):
    body = {"model": model, "temperature": 0, "max_tokens": max_tokens, "usage": {"include": True},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    started = time.monotonic_ns()
    content, usage, error = "", {}, ""
    for attempt in range(4):
        try:
            req = urllib.request.Request(OPENROUTER, data=json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json",
                                                  "Authorization": "Bearer " + key,
                                                  "HTTP-Referer": "https://rxlabs.org", "X-Title": "echoAI bench"})
            with urllib.request.urlopen(req, timeout=180) as r:
                data = json.loads(r.read())
            content = (data["choices"][0]["message"].get("content") or "").strip()
            raw_usage = data.get("usage") or {}
            usage = {k: int(v) for k, v in raw_usage.items() if isinstance(v, int) and not isinstance(v, bool)}
            if isinstance(raw_usage.get("cost"), (int, float)):
                usage["cost_micro_usd"] = int(round(raw_usage["cost"] * 1_000_000))
            error = ""
            break
        except urllib.error.HTTPError as exc:
            error = "HTTPError:%d" % exc.code
            exc.close()
            if exc.code not in (429, 500, 502, 503, 504):
                break
        except (OSError, ValueError, KeyError, IndexError) as exc:
            error = type(exc).__name__
        time.sleep(3 * (attempt + 1))
    return {"model": model, "request": body, "content": content, "usage": usage, "error": error,
            "ms": (time.monotonic_ns() - started) // 1_000_000}


SYS_SHORT = ("Answer the question with the shortest possible factual answer (a name, date, number or a few "
             "words), with no explanation. If you are not sure, answer exactly: I don't know")
SYS_MC = ("Answer the multiple-choice question with the letter of the correct option only. If you are not "
          "sure, answer exactly: I don't know")
SYS_MATH = "Solve the problem. Think step by step, then end with a last line of the form: Final answer: <number>"


def context_block(extracts):
    return "\n".join("[%d] %s" % (i + 1, e["text"]) for i, e in enumerate(extracts))


def jobs_for(items, retrieval):
    """Every model call the run needs, as (dataset, item_id, arm, system, user, max_tokens)."""
    jobs = []
    for it in items["simpleqa"]:
        ctx = context_block(retrieval[it["id"]]["extracts"])
        jobs.append(("simpleqa", it["id"], "M", SYS_SHORT, it["question"], MAX_SHORT))
        jobs.append(("simpleqa", it["id"], "M+R", SYS_SHORT,
                     "Context passages:\n%s\n\nQuestion: %s" % (ctx, it["question"]), MAX_SHORT))
    for it in items["mmlupro"]:
        opts = "\n".join("%s. %s" % ("ABCDEFGHIJ"[i], o) for i, o in enumerate(it["options"]))
        q = "%s\n\n%s" % (it["question"], opts)
        ctx = context_block(retrieval[it["id"]]["extracts"])
        jobs.append(("mmlupro", it["id"], "M", SYS_MC, q, MAX_SHORT))
        jobs.append(("mmlupro", it["id"], "M+R", SYS_MC, "Context passages:\n%s\n\n%s" % (ctx, q), MAX_SHORT))
    for it in items["gsm8k"]:
        jobs.append(("gsm8k", it["id"], "M", SYS_MATH, it["question"], MAX_MATH))
    return jobs


def credits_remaining(key):
    req = urllib.request.Request("https://openrouter.ai/api/v1/credits", headers={"Authorization": "Bearer " + key})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read())["data"]
    return int(round((d["total_credits"] - d["total_usage"]) * 1_000_000))


def spent_micro_usd(receipts):
    return sum(int(r.get("usage", {}).get("cost_micro_usd", 0)) for r in receipts.values())


def run_model(model, items, retrieval, out, key, workers=6):
    """All calls for one model, resumable: receipts already on disk are kept."""
    path = out / ("receipts-%s.json" % model.replace("/", "__"))
    receipts = json.loads(path.read_text()) if path.exists() else {}
    lock = threading.Lock()
    todo = [j for j in jobs_for(items, retrieval) if "%s|%s|%s" % j[:3] not in receipts
            or receipts["%s|%s|%s" % j[:3]]["error"]]

    def one(job):
        dataset, item_id, arm, system, user, max_tokens = job
        r = ask(model, system, user, max_tokens=max_tokens, key=key)
        with lock:
            receipts["%s|%s|%s" % (dataset, item_id, arm)] = r
            path.write_text(json.dumps(receipts, sort_keys=True, indent=1))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(one, todo))
    return receipts


# ------------------------------------------------------------------ scoring (pure: from receipts only)

def score(items, retrieval, receipts_by_model):
    verifier = EchoVerifier()
    per_item, table = [], {}
    for model, receipts in receipts_by_model.items():
        t = table.setdefault(model, {})
        for dataset in ("simpleqa", "mmlupro", "gsm8k"):
            arms = ("M", "M+R", "M+R+ECHO", "TRIVIAL") if dataset != "gsm8k" else ("M", "M+ECHO", "TRIVIAL")
            counts = {a: {"correct": 0, "incorrect": 0, "not_attempted": 0, "errors": 0} for a in arms}
            usage = {a: {"prompt_tokens": 0, "completion_tokens": 0, "calls": 0} for a in arms}
            for it in items[dataset]:
                row = {"model": model, "dataset": dataset, "id": it["id"]}
                answers = {}
                for arm in ("M", "M+R"):
                    r = receipts.get("%s|%s|%s" % (dataset, it["id"], arm))
                    if r is None or (dataset == "gsm8k" and arm == "M+R"):
                        continue
                    answers[arm] = r["content"] if not r["error"] else ""
                    if r["error"]:
                        counts.setdefault(arm, {}).setdefault("errors", 0)
                        counts[arm]["errors"] += 1
                    u = usage[arm]
                    u["calls"] += 1
                    u["prompt_tokens"] += int(r["usage"].get("prompt_tokens", 0))
                    u["completion_tokens"] += int(r["usage"].get("completion_tokens", 0))
                if dataset == "gsm8k":
                    answers["M+ECHO"] = IDK                         # no evidence for arithmetic: abstain
                else:
                    v = verifier.verify(answers.get("M+R", ""), retrieval[it["id"]]["extracts"])
                    answers["M+R+ECHO"] = answers.get("M+R", "") if v["status"] == "supported" else IDK
                    row["echo"] = v["status"]
                    usage["M+R+ECHO"] = usage["M+R"]              # same calls: the firewall adds none
                answers["TRIVIAL"] = IDK
                for arm in arms:
                    a = answers.get(arm, "")
                    if dataset == "simpleqa":
                        g = grade_short(a, it["gold"])
                    elif dataset == "mmlupro":
                        g, _ = grade_letter(a, it["gold"])
                    else:
                        g = grade_number(a, it["gold"])
                    counts[arm][g] += 1
                    row[arm] = g
                if dataset != "gsm8k" and row["M+R+ECHO"] == "correct" and row["M+R"] != "correct":
                    raise AssertionError("ECHO created a correct answer: impossible by construction")
                per_item.append(row)
            t[dataset] = {"counts": counts, "usage": usage, "n": len(items[dataset])}
    return per_item, table


def rates(c, n):
    """Integer permille metrics (no floats in sealed reports)."""
    attempted = c["correct"] + c["incorrect"]
    correct_pm = 1000 * c["correct"] // n if n else 0
    incorrect_pm = 1000 * c["incorrect"] // n if n else 0
    precision_pm = 1000 * c["correct"] // attempted if attempted else 0
    f_pm = (2 * correct_pm * precision_pm) // (correct_pm + precision_pm) if (correct_pm + precision_pm) else 0
    return {"correct_pm": correct_pm, "incorrect_pm": incorrect_pm, "not_attempted_pm": 1000 * c["not_attempted"] // n if n else 0,
            "precision_pm": precision_pm, "f_pm": f_pm}


# ------------------------------------------------------------------ charts

def charts(table, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    models = list(table)
    short = [m.split("/")[-1] for m in models]
    for dataset in ("simpleqa", "mmlupro"):
        arms = ("M", "M+R", "M+R+ECHO", "TRIVIAL")
        fig, axes = plt.subplots(1, len(models), figsize=(3.2 * len(models), 4), sharey=True)
        axes = axes if len(models) > 1 else [axes]
        for ax, m, name in zip(axes, models, short):
            n = table[m][dataset]["n"]
            c = [table[m][dataset]["counts"][a] for a in arms]
            cor = [100 * x["correct"] / n for x in c]
            inc = [100 * x["incorrect"] / n for x in c]
            na = [100 * x["not_attempted"] / n for x in c]
            ax.bar(arms, cor, color="#3fb950", label="correct")
            ax.bar(arms, inc, bottom=cor, color="#f85149", label="incorrect")
            ax.bar(arms, na, bottom=[a + b for a, b in zip(cor, inc)], color="#8b949e", label="not attempted")
            ax.set_title(name, fontsize=9)
            ax.tick_params(axis="x", labelrotation=45, labelsize=8)
        axes[0].set_ylabel("% of questions")
        axes[-1].legend(fontsize=7, loc="upper right")
        fig.suptitle("%s: the same model with and without ECHO" % ("SimpleQA" if dataset == "simpleqa" else "MMLU-Pro"))
        fig.tight_layout()
        for ext in ("png", "svg"):
            fig.savefig(out / ("chart-%s.%s" % (dataset, ext)), dpi=150)
        plt.close(fig)
    fig, ax = plt.subplots(figsize=(6, 5))
    for m, name in zip(models, short):
        c = table[m]["simpleqa"]["counts"]
        n = table[m]["simpleqa"]["n"]
        pts = []
        for arm in ("M+R", "M+R+ECHO"):
            att = c[arm]["correct"] + c[arm]["incorrect"]
            pts.append((100 * att / n, 100 * c[arm]["correct"] / att if att else 0))
        ax.annotate("", xy=pts[1], xytext=pts[0], arrowprops={"arrowstyle": "->", "color": "#58a6ff"})
        ax.scatter(*zip(*pts), s=18, color="#58a6ff")
        ax.text(pts[1][0], pts[1][1] + 1, name, fontsize=7)
    ax.set_xlabel("coverage: % of questions answered")
    ax.set_ylabel("precision: % correct when it answers")
    ax.set_title("SimpleQA: M+R  ->  M+R+ECHO")
    fig.tight_layout()
    for ext in ("png", "svg"):
        fig.savefig(out / ("chart-precision-coverage.%s" % ext), dpi=150)
    plt.close(fig)


# ------------------------------------------------------------------ custody

def sources():
    files = ["echo4/bench1.py", "docs/ECHO4-BENCH1-A-DESIGN.md", "lab/echo4/bench1-data/samples.json"]
    return {f: sha((ROOT / f).read_bytes()) for f in files}


def report_for(split, items, retrieval, receipts_by_model):
    per_item, table = score(items, retrieval, receipts_by_model)
    summary = {m: {d: {a: {**table[m][d]["counts"][a], **rates(table[m][d]["counts"][a], table[m][d]["n"])}
                       for a in table[m][d]["counts"]}
                   for d in table[m]} for m in table}
    usage = {m: {d: table[m][d]["usage"] for d in table[m]} for m in table}
    report = {"schema": "e4-bench1-a-v1", "split": split, "sources": sources(), "samples_sha256": SAMPLES_SHA,
              "models": list(receipts_by_model), "summary": summary, "usage": usage,
              "retrieval_sha256": sha(canonical(retrieval)),
              "receipts_sha256": {m: sha(canonical(r)) for m, r in receipts_by_model.items()},
              "items_sha256": sha(canonical(per_item)),
              "echo_never_adds_a_correct_answer": True}
    report["reproduction_sha256"] = sha(canonical(report))
    return report, per_item, table


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=("run", "audit"))
    ap.add_argument("out")
    ap.add_argument("--split", choices=("dev", "exam"), default="dev")
    ap.add_argument("--models", nargs="*", default=list(MODELS))
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--budget-usd", type=float, default=2.0, help="stop before a model if this run has spent this much")
    ap.add_argument("--floor-usd", type=float, default=1.0, help="stop if the account has less than this left")
    args = ap.parse_args(argv)
    out = Path(args.out).resolve()
    if args.command == "run":
        out.mkdir(parents=True, exist_ok=True)
        items = load_items(args.split)
        retrieval = retrieval_for(items, out / "retrieval.json")
        key = api_key()
        receipts, budget = {}, int(args.budget_usd * 1_000_000)
        for m in args.models:
            spent = sum(spent_micro_usd(r) for r in receipts.values())
            left = credits_remaining(key)
            if spent >= budget or left < int(args.floor_usd * 1_000_000):
                print("STOP before %s: spent %.4f $ of %.2f $ budget; account has %.4f $ left"
                      % (m, spent / 1e6, args.budget_usd, left / 1e6), file=sys.stderr)
                break
            receipts[m] = run_model(m, items, retrieval, out, key, args.workers)
            print("done %s: this model %.4f $, run total %.4f $"
                  % (m, spent_micro_usd(receipts[m]) / 1e6, sum(spent_micro_usd(r) for r in receipts.values()) / 1e6),
                  file=sys.stderr)
        report, per_item, table = report_for(args.split, items, retrieval, receipts)
        (out / "items.json").write_text(json.dumps(per_item, sort_keys=True, indent=1))
        (out / "report.json").write_text(json.dumps(report, sort_keys=True, indent=1))
        charts(table, out)
        print(json.dumps({"reproduction_sha256": report["reproduction_sha256"], "summary": report["summary"]},
                         indent=1))
        return 0
    # audit: rebuild from receipts only (no model call, no network)
    report = json.loads((out / "report.json").read_text())
    items = load_items(report["split"])
    retrieval = json.loads((out / "retrieval.json").read_text())
    receipts = {m: json.loads((out / ("receipts-%s.json" % m.replace("/", "__"))).read_text())
                for m in report["models"]}
    rebuilt, _, _ = report_for(report["split"], items, retrieval, receipts)
    ok = rebuilt["reproduction_sha256"] == report["reproduction_sha256"]
    receipt = {"valid": ok, "reproduction_sha256": report["reproduction_sha256"],
               "rebuilt_sha256": rebuilt["reproduction_sha256"], "split": report["split"],
               "scope": "E4-BENCH-1 A rebuilt from stored receipts (no model or network call)"}
    (out / "audit-receipt.json").write_text(json.dumps(receipt, sort_keys=True, indent=1))
    print(json.dumps(receipt, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
