"""Opt-in local Qwen proposer with fixed weights and recorded HTTP receipts."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import time
import urllib.error
import urllib.request

from echoai.echo4.continuity import canonical
from echoai.echo4.continuity_final_audit import file_hash
from echoai.echo4.dream_history import sha
from echoai.echo4.dream_policy import parse_candidates
from echoai.echo4.self_attribution import CATALOG

SYSTEM = """You propose bounded experiment schedules for echoAI research.
Return only a JSON object with a candidates array (1 to 4 policies).
Each policy has version:1, order:a permutation of [0,1,2,3,4,5],
enabled:six integer 0/1 quotas indexed by experiment, step_budget:an integer 4..12.
Maximize resolved diagnoses within 12 physical steps, then minimize steps.
Experiments restore the same context. The fixed SELF interpreter filters
unsafe experiments, intersects hypotheses and stops when their labels agree.
An unknown diagnosis is not success. Use observed historical results when
provided. Propose diverse orders; do not output code, explanations or claims
about unobserved cases. You cannot alter the interpreter, evaluator or gate.
"""

# Format constraint only. Semantic validation (permutation, limits, fields)
# remains a separate fail-closed step after the real inference.
GRAMMAR = r'''root ::= "{" ws "\"candidates\"" ws ":" ws "[" ws policy (ws "," ws policy)? (ws "," ws policy)? (ws "," ws policy)? ws "]" ws "}"
policy ::= "{" ws "\"version\"" ws ":" ws "1" ws "," ws "\"order\"" ws ":" ws array ws "," ws "\"enabled\"" ws ":" ws array ws "," ws "\"step_budget\"" ws ":" ws number ws "}"
array ::= "[" ws number ws "," ws number ws "," ws number ws "," ws number ws "," ws number ws "," ws number ws "]"
number ::= "0" | [1-9] [0-9]?
ws ::= [ \t\n]*
'''


def prompt(history):
    context = {"catalog": [{"index": i, "actions": list(a), "cost": len(a)}
                           for i, a in enumerate(CATALOG)],
               "observed_history": history}
    return ("<|im_start|>system\n" + SYSTEM + "<|im_end|>\n<|im_start|>user\n"
            + canonical(context).decode() + "<|im_end|>\n<|im_start|>assistant\n")


def payload(history, cycle):
    return {"prompt": prompt(history), "n_predict": 512, "temperature": 0,
            "seed": 260922 + cycle, "grammar": GRAMMAR,
            "cache_prompt": False, "stop": ["<|im_end|>"]}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("local model redirect refused")


class LocalQwen:
    """Owns only its explicitly started child process, never an existing service."""
    def __init__(self, server, model, directory, *, port=8094, threads=4):
        self.server, self.model = Path(server).resolve(), Path(model).resolve()
        if any("echo-discord" in str(p).lower() for p in (self.server, self.model)):
            raise ValueError("legacy Discord assets are outside this project")
        if not self.server.is_file() or not self.model.is_file():
            raise ValueError("local inference binary/model missing")
        if "qwen" not in self.model.name.lower() or self.model.suffix.lower() != ".gguf":
            raise ValueError("this contract requires a local Qwen GGUF")
        if type(port) is not int or not 1024 <= port <= 65535:
            raise ValueError("invalid local port")
        if type(threads) is not int or not 1 <= threads <= 16:
            raise ValueError("invalid thread limit")
        self.directory, self.port, self.threads = Path(directory), port, threads
        self.base_url = "http://127.0.0.1:" + str(port)
        self.http = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        self.process = self.log = None
        self.calls = 0
        self.metadata = None

    def _request(self, endpoint, body=None, timeout=120):
        req = urllib.request.Request(self.base_url + endpoint, data=body,
                                     headers={"Content-Type": "application/json"})
        with self.http.open(req, timeout=timeout) as response:
            raw = response.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise ValueError("oversized model response")
        return raw

    def __enter__(self):
        version = subprocess.run([str(self.server), "--version"], capture_output=True,
                                 timeout=30, check=True)
        args = [str(self.server), "-m", str(self.model), "--host", "127.0.0.1",
                "--port", str(self.port), "-c", "8192", "-np", "1", "-t",
                str(self.threads), "-ngl", "0", "--alias", "echo4-dream-qwen"]
        self.metadata = {"server": str(self.server), "server_sha256": file_hash(self.server),
                         "model": str(self.model), "model_sha256": file_hash(self.model),
                         "model_bytes": self.model.stat().st_size,
                         "version": (version.stdout + version.stderr).decode(errors="replace"),
                         "argv": args, "weights_updated": False}
        self.log = (self.directory / "llama-server.log").open("xb")
        started = time.monotonic_ns()
        try:
            self.process = subprocess.Popen(args, stdout=self.log, stderr=subprocess.STDOUT)
            # Poll only the server we launched; port collisions fail closed.
            for _ in range(120):
                if self.process.poll() is not None:
                    raise RuntimeError("local model failed to start; inspect llama-server.log")
                try:
                    if json.loads(self._request("/health", timeout=1)).get("status") == "ok":
                        props = json.loads(self._request("/props", timeout=2))
                        if props.get("model_path") != str(self.model):
                            raise ValueError("serving model path mismatch")
                        self.metadata["startup_ms"] = (time.monotonic_ns() - started) // 1000000
                        return self
                except (urllib.error.URLError, TimeoutError):
                    pass
                time.sleep(1)
            raise TimeoutError("local model startup timed out")
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, *_):
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        if self.log is not None:
            self.log.close()

    def propose(self, history, cycle):
        if self.calls >= 6:
            raise RuntimeError("campaign model-call budget exhausted")
        self.calls += 1
        request = payload(history, cycle)
        started = time.monotonic_ns()
        raw, error = "", ""
        try:
            raw = self._request("/completion", canonical(request)).decode()
        except (OSError, ValueError) as exc:
            error = type(exc).__name__
        receipt = {"request": request, "raw_response": raw, "transport_error": error,
                   "elapsed_ms": (time.monotonic_ns() - started) // 1000000,
                   "model_sha256": self.metadata["model_sha256"]}
        receipt["sha256"] = sha(canonical(receipt))
        return receipt


def read_proposal(receipt, history, cycle, model_sha256):
    unsigned = dict(receipt)
    claimed = unsigned.pop("sha256")
    if sha(canonical(unsigned)) != claimed or receipt["request"] != payload(history, cycle):
        raise ValueError("proposal receipt/request mismatch")
    if receipt["model_sha256"] != model_sha256 or type(receipt["elapsed_ms"]) is not int or receipt["elapsed_ms"] < 0:
        raise ValueError("model identity or elapsed time mismatch")
    cost = {"calls": 1, "prompt_tokens": 0, "generated_tokens": 0,
            "elapsed_ms": receipt["elapsed_ms"]}
    if receipt["transport_error"]:
        return (), cost, receipt["transport_error"]
    try:
        response = json.loads(receipt["raw_response"])
        for key, target in (("tokens_evaluated", "prompt_tokens"), ("tokens_predicted", "generated_tokens")):
            value = response[key]
            if type(value) is not int or value < 0:
                raise ValueError("missing token accounting")
            cost[target] = value
        if not 0 < cost["generated_tokens"] <= 512 or cost["prompt_tokens"] + cost["generated_tokens"] > 8192:
            raise ValueError("model token budget violated")
        if response.get("truncated") or response.get("stopped_limit"):
            return (), cost, "truncated_generation"
        return parse_candidates(response["content"]), cost, ""
    except (ValueError, TypeError, KeyError) as exc:
        return (), cost, "rejected:" + str(exc)
