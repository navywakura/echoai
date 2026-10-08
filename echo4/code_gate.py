"""E4-CODE-1 A · gate for a coding agent's shell commands: OK | MODIFY | BLOCK.

Deny by default. The agent proposes a command; ECHO allows it only when every
part is on a published allowlist of safe programs and every path it touches stays
inside the project. Anything else — an unknown program, a shell/eval wrapper, a
path outside the project, a command that came from a testimony (text the agent
read, never an order) — is BLOCK until the operator approves it.

This design lists what is safe, not what is dangerous: the allowlist is complete
by construction, so it also stops tricks nobody enumerated. The operator stays on
top through `.echoai/policy.json` (`stopped`, and exact `allow` / `deny` lines).
"""
import os
import re
import shlex
from pathlib import Path

OK, MODIFY, BLOCK = "OK", "MODIFY", "BLOCK"

# Programs that never touch files or the outside world: always allowed.
READ_ONLY = {
    "ls", "pwd", "cat", "head", "tail", "less", "wc", "grep", "egrep", "fgrep", "rg",
    "echo", "printf", "date", "whoami", "id", "hostname", "uname", "printenv", "which",
    "type", "file", "stat", "du", "df", "tree", "sort", "uniq", "cut", "tr", "sed", "awk", "jq",
    "diff", "cmp", "sha256sum", "md5sum", "basename", "dirname", "realpath", "readlink", "true",
    "false", "test", "seq", "yes", "sleep", "tee", "column", "nl", "tac", "xxd", "od", "strings",
    "ps", "top", "free", "uptime", "nproc", "lscpu", "man", "help", "history", "curl", "wget",
}
# Shell builtins that change only the shell's own environment, never files.
BUILTINS = {"cd", "export", "set", "unset", "pushd", "popd", "umask", "alias", "unalias", ":"}
# Programs that take an inline program or query string the gate cannot read.
# Deny by default: the operator decides. (`python file.py` is fine; `python -c "..."` is not.)
INLINE_CODE = {
    "python": "-c", "python3": "-c", "perl": "-e", "node": "-e", "ruby": "-e", "deno": "eval",
    "php": "-r", "Rscript": "-e", "sqlite3": None, "psql": "-c", "mysql": "-e", "mariadb": "-e",
}
# Programs that modify files or state but only inside the project: allowed when
# their path arguments resolve inside the project root.
SCOPED = {
    "rm", "rmdir", "mv", "cp", "mkdir", "touch", "ln", "chmod", "install", "truncate",
    "tar", "unzip", "zip", "gzip", "gunzip", "mktemp", "patch",
}
# Build, test, format and language tools: allowed (they run project code, not the shell).
TOOLING = {
    "python", "python3", "pip", "pip3", "pytest", "py.test", "tox", "nox", "coverage", "ruff",
    "black", "isort", "flake8", "mypy", "pyright", "pylint", "uv", "hatch", "poetry", "pre-commit",
    "node", "npm", "npx", "yarn", "pnpm", "deno", "bun", "tsc", "eslint", "prettier", "vitest", "jest",
    "cargo", "rustc", "rustup", "clippy-driver", "go", "gofmt", "make", "cmake", "ctest", "ninja",
    "gcc", "g++", "clang", "clang++", "ld", "ar", "pkg-config", "meson", "bazel", "buck2",
    "mvn", "gradle", "dotnet", "swift", "javac", "java", "kotlin", "scala", "ruby", "bundle", "rake",
    "rspec", "php", "composer", "perl", "Rscript", "julia", "dart", "flutter", "elixir", "mix",
    "gdb", "lldb", "valgrind", "strace", "ltrace", "hyperfine", "time",
    "docker", "docker-compose", "uvicorn", "gunicorn", "hypercorn", "flask", "celery", "alembic",
}
# git subcommands that stay local (no push, no network write, no history rewrite).
GIT_LOCAL = {
    "status", "diff", "log", "show", "add", "commit", "restore", "switch", "checkout", "branch",
    "stash", "tag", "reset", "rm", "mv", "config", "blame", "cat-file", "ls-files", "rev-parse",
    "describe", "merge", "rebase", "cherry-pick", "revert", "fetch", "pull", "remote", "shortlog",
    "clean", "bisect", "worktree", "grep", "apply", "format-patch", "reflog", "init", "clone",
}
# git subcommands that write outside the repo or to a remote: need the operator.
GIT_OUTWARD = {"push", "send-email", "request-pull", "svn", "p4", "daemon"}
# (git subcommand, flag) pairs that are destructive even though the subcommand is local.
GIT_DANGER_FLAGS = {("reset", "--hard"), ("branch", "-D"), ("branch", "--delete")}
GIT_DANGER_SUB = {"clean"}
# Package/registry subcommands that publish or deploy outward.
OUTWARD_SUB = {
    "npm": {"publish"}, "yarn": {"publish"}, "pnpm": {"publish"}, "cargo": {"publish"},
    "gem": {"push"}, "docker": {"push", "system", "login"}, "kubectl": {"delete", "apply"},
}
# Runners we wrap around another command whose real program we still want to see.
PASSTHROUGH = {"time", "nice", "ionice", "chrt", "stdbuf", "nohup", "command", "builtin",
               "caffeinate", "env"}


class Verdict:
    def __init__(self):
        self.decision, self.reasons, self.suggestion = OK, [], None

    def _raise(self, level):
        order = {OK: 0, MODIFY: 1, BLOCK: 2}
        if order[level] > order[self.decision]:
            self.decision = level

    def block(self, reason):
        self._raise(BLOCK)
        self.reasons.append(reason)

    def modify(self, reason, suggestion):
        self._raise(MODIFY)
        self.reasons.append(reason)
        self.suggestion = suggestion

    def as_dict(self):
        return {"decision": self.decision, "reasons": list(self.reasons), "suggestion": self.suggestion}


def _project_root(root):
    return Path(root).resolve()


def _inside(root, word):
    """True when a path argument stays inside the project root.

    Options and flag values return True (not paths). A glob is judged by its fixed
    prefix. A variable, a home shortcut or a parent that escapes the root is False.
    """
    if not word or word.startswith("-") or word.startswith("+"):
        return True
    if "$" in word or "`" in word or word.startswith("~"):
        return False
    fixed = re.split(r"[*?\[{]", word, 1)[0]           # the part before any glob metachar
    if not fixed:
        return False
    p = Path(fixed if fixed.endswith("/") or "/" in fixed else fixed)
    p = (root / p) if not p.is_absolute() else p
    try:
        Path(os.path.normpath(str(p))).relative_to(root)
        return True
    except ValueError:
        return False


def _path_args(words):
    return [w for w in words[1:] if not (w.startswith("-") or w.startswith("+"))]


CONTROL = {";", "&", "&&", "|", "||", "|&", "\n", "(", ")", "{", "}"}
WRITE_REDIRECT = {">", ">>", "&>", ">|", "1>", "2>", "2>>", "&>>"}
REDIRECT = WRITE_REDIRECT | {"<", "<<", "<<<", "0<"}


def _substitutions(text):
    """Inner command strings of $(...), <(...), >(...) and backticks (one level)."""
    inner, i = [], 0
    while i < len(text):
        two = text[i:i + 2]
        if two in ("$(", "<(", ">("):
            depth, j = 1, i + 2
            while j < len(text) and depth:
                depth += {"(": 1, ")": -1}.get(text[j], 0)
                j += 1
            inner.append(text[i + 2:j - 1])
            i = j
        elif text[i] == "`":
            j = text.find("`", i + 1)
            if j < 0:
                break
            inner.append(text[i + 1:j])
            i = j + 1
        else:
            i += 1
    return inner


def _blank_substitutions(text):
    """Replace substitutions with a harmless token so the outer line can tokenize."""
    out, i = [], 0
    while i < len(text):
        two = text[i:i + 2]
        if two in ("$(", "<(", ">("):
            depth, j = 1, i + 2
            while j < len(text) and depth:
                depth += {"(": 1, ")": -1}.get(text[j], 0)
                j += 1
            out.append("_sub_")
            i = j
        elif text[i] == "`":
            j = text.find("`", i + 1)
            if j < 0:
                out.append(text[i:])
                break
            out.append("_sub_")
            i = j + 1
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def _simple_commands(tokens, root, v):
    """Yield each simple command (list of words) from a token stream, validating
    redirection targets as we go. Grouping operators make it unparseable."""
    commands, current, i = [], [], 0
    while i < len(tokens):
        tok = tokens[i]
        if tok in ("(", ")", "{", "}"):
            v.block("shell grouping is not analysed; the operator decides")
            return []
        if tok in REDIRECT:
            target = tokens[i + 1] if i + 1 < len(tokens) else ""
            if tok in WRITE_REDIRECT and not _inside(root, target):
                v.block("redirection writes outside the project: %s %s" % (tok, target))
            i += 2
            continue
        if tok in CONTROL:
            if current:
                commands.append(current)
                current = []
            i += 1
            continue
        current.append(tok)
        i += 1
    if current:
        commands.append(current)
    return commands


def _strip_wrappers(words):
    """Drop leading VAR=value assignments and passthrough runners (time, nice, env …)."""
    words = list(words)
    while words:
        head = words[0]
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", head):
            words.pop(0)
            continue
        name = os.path.basename(head)
        if name in PASSTHROUGH:
            words.pop(0)
            while words and (words[0].startswith("-") or re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", words[0])):
                words.pop(0)
            continue
        if name == "timeout":
            words.pop(0)
            while words and (words[0].startswith("-") or re.match(r"^\d+(\.\d+)?[smhd]?$", words[0])):
                words.pop(0)
            continue
        break
    if words:
        words[0] = os.path.basename(words[0])
    return words


def _check_git(words, v):
    sub = next((w for w in words[1:] if not w.startswith("-")), None)
    flags = [w for w in words[1:] if w.startswith("-")]
    if sub is None:
        return
    if sub in GIT_OUTWARD:
        v.block("git %s writes to a remote; the operator decides" % sub)
    elif sub in GIT_DANGER_SUB:
        v.block("git %s can wipe untracked work; the operator decides" % sub)
    elif any((sub, f) in GIT_DANGER_FLAGS for f in flags):
        v.block("git %s %s is destructive; the operator decides" % (sub, " ".join(flags)))
    elif sub not in GIT_LOCAL:
        v.block("git subcommand not on the local allowlist: %s" % sub)


def _check_simple(words, root, v):
    words = _strip_wrappers(words)
    if not words:
        return
    prog = words[0]
    if prog in BUILTINS:
        for arg in _path_args(words):
            if not _inside(root, arg):
                v.block("%s would leave the project: %s" % (prog, arg))
        return
    if prog in INLINE_CODE:
        flag = INLINE_CODE[prog]
        takes_inline = flag is None or flag in words[1:] or (prog == "deno" and "eval" in words[1:])
        if takes_inline:
            v.block("%s runs an inline program/query the gate cannot read; the operator decides" % prog)
        return                                        # `python file.py`, `psql -f x.sql`: allowed
    if prog == "xargs":
        rest = list(words[1:])
        while rest and (rest[0].startswith("-") or rest[0].startswith("+")):
            opt = rest.pop(0)
            if opt in ("-I", "-E", "-n", "-P", "-s", "-d", "-a") and rest:
                rest.pop(0)                           # option that takes a value
        if not rest:
            return                                    # `xargs` with no command: harmless
        if os.path.basename(rest[0]) in READ_ONLY:
            return                                    # xargs echo / grep …: safe
        v.block("xargs runs %s over paths from stdin the gate cannot verify; the operator decides"
                % os.path.basename(rest[0]))
        return
    if prog == "find":
        acts = {"-delete", "-exec", "-execdir", "-fprint", "-fprintf", "-ok", "-okdir"}
        first = next((w for w in words[1:] if not w.startswith("-")), ".")
        if not _inside(root, first):
            v.block("find runs over a path outside the project: %s" % first)
        elif any(a in acts for a in words[1:]) and not _inside(root, first):
            v.block("find with an action outside the project")
        return
    if prog in OUTWARD_SUB:
        sub = next((w for w in words[1:] if not w.startswith("-")), None)
        if sub in OUTWARD_SUB[prog]:
            v.block("%s %s publishes or changes the outside world; the operator decides" % (prog, sub))
        return
    if prog == "git":
        _check_git(words, v)
        return
    if prog in READ_ONLY or prog in TOOLING:
        return
    if prog in SCOPED:
        for arg in _path_args(words):
            if not _inside(root, arg):
                v.block("%s would touch a path outside the project: %s" % (prog, arg))
        return
    v.block("program not on the allowlist: %s" % prog)


def _load_policy(root):
    path = Path(root) / ".echoai" / "policy.json"
    if not path.is_file():
        return {}
    try:
        import json
        data = json.loads(path.read_text())
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def check_action(command, *, root=".", from_testimony=False):
    """Decide OK | MODIFY | BLOCK for one proposed command line."""
    root = _project_root(root)
    v = Verdict()
    policy = _load_policy(root)
    if policy.get("stopped"):
        v.block("operator stop is active")
        return v.as_dict()
    text = command if isinstance(command, str) else ""
    if not text.strip():
        v.block("empty command")
        return v.as_dict()
    if from_testimony:
        v.block("this command came from a testimony, not the operator; it is never run as an order")
        return v.as_dict()
    if isinstance(policy.get("deny"), list) and text.strip() in policy["deny"]:
        v.block("denied by operator policy")
        return v.as_dict()
    if isinstance(policy.get("allow"), list) and text.strip() in policy["allow"]:
        return v.as_dict()                            # operator pre-approved this exact line
    _analyse(text, root, v, depth=0)
    if v.decision != BLOCK:                            # quality flags, not safety blocks
        if re.search(r"\|\|\s*(true|:)\b", text):
            v.modify("`|| true` hides a real failure", re.sub(r"\s*\|\|\s*(true|:)\b", "", text).strip())
        if re.search(r"\bgit\b.*\bcommit\b", text) and "--no-verify" in _tokens(_blank_substitutions(text)):
            v.modify("`--no-verify` skips the project's checks",
                     text.replace(" --no-verify", "").replace("--no-verify ", ""))
    return v.as_dict()


def _analyse(text, root, v, depth):
    if depth > 4:
        v.block("command nested too deeply to analyse; the operator decides")
        return
    for inner in _substitutions(text):                # recurse into $(...), `...`, <(...)
        _analyse(inner, root, v, depth + 1)
    try:
        tokens = _tokens(_blank_substitutions(text))
    except ValueError:
        v.block("could not parse the command (unbalanced quotes)")
        return
    for words in _simple_commands(tokens, root, v):
        _check_simple(words, root, v)


def _tokens(text):
    lex = shlex.shlex(text, posix=True, punctuation_chars="();&|<>")
    lex.whitespace_split = True
    lex.commenters = ""
    return list(lex)
