"""Static Python AST and import graph; other languages are explicitly inventoried."""
from __future__ import annotations

import ast
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .common import digest, save, sources


def module_name(relative: Path) -> str:
    parts = list(relative.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def inspect_tree(root: Path, output: Path) -> dict[str, Any]:
    paths = sources(root)
    python = [p for p in paths if p.suffix == ".py"]
    modules = {module_name(p.relative_to(root)): str(p.relative_to(root)) for p in python}
    nodes: list[dict[str, Any]] = []
    edges: set[tuple[str, str]] = set()
    duplicates: dict[str, list[str]] = defaultdict(list)
    mock_sites: list[dict[str, Any]] = []
    external: Counter[str] = Counter()
    errors: list[dict[str, str]] = []
    for path in python:
        relative = str(path.relative_to(root))
        module = module_name(path.relative_to(root))
        try:
            tree = ast.parse(path.read_bytes(), filename=relative)
        except (SyntaxError, ValueError) as exc:
            errors.append({"path": relative, "error": str(exc)})
            continue
        definitions, stubs = [], []
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                body = node.body
                meaningful = [s for s in body if not (isinstance(s, ast.Expr) and
                              isinstance(s.value, ast.Constant) and isinstance(s.value.value, str))]
                incomplete = bool(meaningful) and all(isinstance(s, ast.Pass) or
                    (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant) and s.value.value is Ellipsis)
                    or (isinstance(s, ast.Raise) and s.exc is not None and
                        "NotImplementedError" in ast.unparse(s.exc)) for s in meaningful)
                item = {"name": node.name, "kind": type(node).__name__, "line": node.lineno,
                        "signature": ast.unparse(node.args) if not isinstance(node, ast.ClassDef) else None,
                        "returns": ast.unparse(node.returns) if not isinstance(node, ast.ClassDef) and node.returns else None,
                        "bases": [ast.unparse(b) for b in node.bases] if isinstance(node, ast.ClassDef) else [],
                        "decorators": [ast.unparse(d) for d in node.decorator_list]}
                definitions.append(item)
                if incomplete:
                    stubs.append(node.lineno)
                if not isinstance(node, ast.ClassDef) and len(meaningful) >= 3:
                    normalized = digest(ast.dump(ast.Module(body=body, type_ignores=[]),
                                                 include_attributes=False).encode())
                    duplicates[normalized].append(f"{relative}:{node.lineno}:{node.name}")
            if isinstance(node, ast.Import):
                imports.extend(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                package = module.split(".") if path.name == "__init__.py" else module.split(".")[:-1]
                prefix = package[:len(package) - node.level + 1] if node.level else []
                base = ".".join(prefix + ([node.module] if node.module else []))
                imports.append(base)
                imports.extend(".".join(filter(None, (base, a.name))) for a in node.names)
            elif isinstance(node, ast.Call):
                called = ast.unparse(node.func)
                if any(k in called for k in ("patch", "Mock", "mock", "skip", "subprocess", "urlopen",
                                             "httpx", "cuda", "gguf", "Popen")):
                    mock_sites.append({"path": relative, "line": node.lineno, "call": called,
                                       "kind": "mock_or_skip" if any(x in called.lower() for x in ("mock", "patch", "skip"))
                                       else "external_boundary"})
        for imported in sorted(set(imports)):
            target = imported.removeprefix("echoai.")
            while target and target not in modules:
                target = target.rpartition(".")[0]
            if target and target != module:
                edges.add((module, target))
            elif imported and not target:
                external[imported.split(".")[0]] += 1
        nodes.append({"path": relative, "module": module, "sha256": digest(path.read_bytes()),
                      "definitions": definitions, "imports": sorted(set(imports)),
                      "stub_candidates": stubs,
                      "ast_nodes": sum(1 for _ in ast.walk(tree))})
    graph: dict[str, set[str]] = defaultdict(set)
    for a, b in edges:
        graph[a].add(b)
    # Cycles are graph facts, not proof that imports fail at runtime.
    index = 0
    stack: list[str] = []
    active: set[str] = set()
    indices: dict[str, int] = {}
    low: dict[str, int] = {}
    components: list[list[str]] = []

    def visit(node: str) -> None:
        nonlocal index
        indices[node] = low[node] = index
        index += 1
        stack.append(node)
        active.add(node)
        for target in sorted(graph.get(node, ())):
            if target not in indices:
                visit(target)
                low[node] = min(low[node], low[target])
            elif target in active:
                low[node] = min(low[node], indices[target])
        if low[node] == indices[node]:
            component = []
            while True:
                target = stack.pop()
                active.remove(target)
                component.append(target)
                if target == node:
                    break
            if len(component) > 1:
                components.append(sorted(component))

    for module in sorted(modules):
        if module not in indices:
            visit(module)
    report = {"schema": 1, "scope": "static Python AST; dynamic imports/calls unresolved",
              "python_files": len(python), "parsed": len(nodes), "errors": errors, "modules": nodes,
              "edges": sorted(edges), "cycles": components,
              "duplicate_body_candidates": [v for v in duplicates.values() if len(v) > 1],
              "mock_and_external_sites": mock_sites, "external_import_roots": dict(external),
              "other_code": [str(p.relative_to(root)) for p in paths
                             if p.suffix in {".c", ".h", ".cpp", ".rs", ".js", ".jsx", ".ts", ".tsx"}],
              "exclusions": "lab, archives, secrets, dependencies, symlinks, large files; no imports executed"}
    save(output / "inventory.json", report)
    groups = sorted({m.split(".")[0] for m in modules if m})
    ids = {m: f"m{i}" for i, m in enumerate(groups)}
    counts = Counter((a.split(".")[0], b.split(".")[0]) for a, b in edges
                     if a.split(".")[0] != b.split(".")[0])
    lines = ["flowchart LR"] + [f'  {ids[m]}["{m}"]' for m in groups]
    lines += [f"  {ids[a]} -->|{n}| {ids[b]}" for (a, b), n in sorted(counts.items())]
    (output / "dependencies.mmd").write_text("\n".join(lines) + "\n")
    return {k: report[k] for k in ("python_files", "parsed", "errors", "cycles")}
