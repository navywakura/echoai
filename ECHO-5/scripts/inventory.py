"""Read-only AST inventory of existing ECHO sources; never imports inventoried code."""

import ast
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import tokenize

WORK = Path(__file__).resolve().parents[1]
SOURCE = WORK.parent
ROOTS = ("nexus0", "echo4", "echo_arc", "seed", "gui4", "harness",
         "metaverse1", "release1", "tests", "viz_tasks")
SKIP = {"__pycache__", ".git", ".venv", "venv", "node_modules"}
OUTPUT = WORK / "docs" / "inventory"


def files():
    for root in ROOTS:
        for folder, dirs, names in os.walk(SOURCE / root, followlinks=False):
            dirs[:] = sorted(d for d in dirs if d not in SKIP
                             and not (Path(folder) / d).is_symlink())
            for name in sorted(names):
                path = Path(folder) / name
                if not path.is_symlink() and path.suffix not in {".pyc", ".pyo"}:
                    yield path
    yield from sorted(p for p in SOURCE.glob("*.py") if not p.is_symlink())


def aliases(path):
    parts = list(Path(path).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    bare = ".".join(parts)
    result = {bare, "echoai" + ("." + bare if bare else "")}
    if path.startswith("harness/echo-nexus/src/"):
        result.add(".".join(parts[3:]))
    if path.startswith("release1/"):
        result.add(".".join(parts[1:]))
    return sorted(result - {""})


def role(path):
    p = Path(path)
    if "tests" in p.parts or p.name.startswith("test_"):
        return "test"
    if p.name == "__init__.py":
        return "package"
    if any(x in p.stem for x in ("bench", "exam", "audit", "campaign", "report",
                                "review", "forensics", "calibrat", "close", "build")):
        return "evaluation-or-tool (name heuristic)"
    if path.startswith("seed/s6") or path.startswith("seed/game_selfimprove"):
        return "S6-research (not production)"
    return "implementation-or-support (review required)"


def parse(path):
    rel = path.relative_to(SOURCE).as_posix()
    data = path.read_bytes()
    result = {"path": rel, "sha256": hashlib.sha256(data).hexdigest(),
              "bytes": len(data), "aliases": aliases(rel), "role_hint": role(rel),
              "imports": [], "definitions": [], "docstring": "",
              "dynamic_imports": [], "sys_path_mutation_lines": [],
              "parse_error": None}
    try:
        with tokenize.open(path) as f:
            text = f.read()
        tree = ast.parse(text, filename=rel)
    except (SyntaxError, UnicodeError, LookupError) as exc:
        result["parse_error"] = str(exc)
        return result
    result["lines"] = len(text.splitlines())
    result["docstring"] = ast.get_docstring(tree) or ""
    result["definitions"] = [{"name": n.name, "line": n.lineno, "kind": type(n).__name__}
                             for n in tree.body if isinstance(n, (ast.FunctionDef,
                                                                  ast.AsyncFunctionDef,
                                                                  ast.ClassDef))]
    package = rel.removesuffix(".py").split("/")[:-1]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result["imports"].extend({"module": x.name, "members": [],
                                      "line": node.lineno, "relative": False}
                                     for x in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                base_parts = package[:len(package) - node.level + 1]
                base = ".".join(base_parts + ([base] if base else []))
            result["imports"].append({"module": base, "members": [x.name for x in node.names],
                                      "line": node.lineno, "relative": bool(node.level)})
        elif isinstance(node, ast.Call):
            func = ast.unparse(node.func)
            if func in {"importlib.import_module", "__import__", "import_module"}:
                arg = node.args[0] if node.args else None
                name = arg.value if isinstance(arg, ast.Constant) and isinstance(arg.value, str) else None
                result["dynamic_imports"].append({"line": node.lineno, "literal": name})
            if func.startswith("sys.path."):
                result["sys_path_mutation_lines"].append(node.lineno)
    return result


def render_cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def main():
    discovered = sorted(set(files()))
    modules = [parse(p) for p in discovered if p.suffix == ".py"]
    index = defaultdict(set)
    for row in modules:
        for name in row["aliases"]:
            index[name].add(row["path"])
    # Trace directly referenced host Python modules in the parent repository,
    # then their own host imports. No other parent trees or credentials are read.
    parent_rows = []
    checked = set()
    queue = list(modules)
    release_tree = ast.parse((SOURCE / "release1/build.py").read_text())
    packaged_host = []
    for node in release_tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "NAVI"
                                               for t in node.targets):
            packaged_host = list(ast.literal_eval(node.value))
    queue.append({"imports": [{"module": name} for name in packaged_host]})
    while queue:
        row = queue.pop()
        for imp in row["imports"]:
            name = imp["module"].split(".")[0]
            if not name or name in checked or name in index or name in sys.stdlib_module_names:
                continue
            checked.add(name)
            target = SOURCE.parent / (name + ".py")
            if not target.is_file() or target.is_symlink():
                continue
            # parse() normally requires an in-root path; a small dedicated AST
            # record keeps these dependencies explicit rather than relocating them.
            data = target.read_bytes()
            with tokenize.open(target) as f:
                text = f.read()
            tree = ast.parse(text, filename=str(target))
            record = {"path": "../" + target.name, "sha256": hashlib.sha256(data).hexdigest(),
                      "bytes": len(data), "aliases": [name], "role_hint": "parent-host-dependency",
                      "docstring": ast.get_docstring(tree) or "", "imports": [],
                      "definitions": [], "parse_error": None, "dynamic_imports": [],
                      "sys_path_mutation_lines": [], "lines": len(text.splitlines())}
            for n in ast.walk(tree):
                if isinstance(n, ast.Import):
                    record["imports"].extend({"module": a.name, "members": [], "line": n.lineno,
                                              "relative": False} for a in n.names)
                elif isinstance(n, ast.ImportFrom):
                    record["imports"].append({"module": n.module or "", "members": [a.name for a in n.names],
                                              "line": n.lineno, "relative": bool(n.level)})
            parent_rows.append(record)
            index[name].add(record["path"])
            queue.append(record)
    modules.extend(parent_rows)
    modules.sort(key=lambda x: x["path"])
    reverse = defaultdict(set)
    for row in modules:
        local, unknown, stdlib = set(), set(), set()
        for imp in row["imports"]:
            base = imp["module"]
            candidates = [base] + [base + ("." if base else "") + member
                                    for member in imp["members"] if member != "*"]
            found = set().union(*(index.get(n, set()) for n in candidates))
            if found:
                local.update(found)
            elif base.split(".")[0] in sys.stdlib_module_names:
                stdlib.add(base.split(".")[0])
            else:
                unknown.add(base or "<relative-unresolved>")
        row["local_dependencies"] = sorted(local)
        row["external_or_unresolved"] = sorted(unknown)
        row["stdlib_dependencies"] = sorted(stdlib)
        for target in local:
            reverse[target].add(row["path"])
    docs = {p.relative_to(SOURCE).as_posix(): p.read_text(errors="replace")
            for p in (SOURCE / "docs").glob("*.md")}
    for row in modules:
        row["imported_by"] = sorted(reverse[row["path"]])
        row["referencing_tests"] = sorted(p for p in reverse[row["path"]]
                                           if "tests/" in p or Path(p).name.startswith("test_"))
        row["document_path_mentions"] = sorted(p for p, text in docs.items()
                                                if row["path"] in text)
    groups = Counter(r["path"].split("/")[0] for r in modules)
    unresolved = Counter(x for r in modules for x in r["external_or_unresolved"])
    duplicate_map = defaultdict(list)
    for row in modules:
        duplicate_map[row["sha256"]].append(row["path"])
    code_extensions = {".py", ".sh", ".c", ".h", ".rs", ".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".gbnf", ".toml"}
    resources = [{"path": p.relative_to(SOURCE).as_posix(), "bytes": p.stat().st_size,
                  "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                 for p in discovered if p.suffix in code_extensions and p.suffix != ".py"]
    result = {"generated_at": datetime.now(timezone.utc).isoformat(), "source_root": str(SOURCE),
              "scope": list(ROOTS) + ["root *.py", "transitive explicitly imported parent *.py"],
              "excluded": ["lab (datasets, sealed results, snapshots, third-party tools)",
                           "ROGEX-LABORATORIES", "echo-discord", "ECHO-5", "binary assets", "environments"],
              "method": "AST only; all lexical imports including conditional/test imports; no execution",
              "limitations": ["imports are potential dependencies, not a runtime call graph",
                              "external_or_unresolved does not imply missing installation",
                              "doc mentions and test imports do not certify validation or coverage",
                              "dynamic/path-dependent imports require manual review",
                              "non-Python sources are hashed, not AST-analyzed",
                              "parent host entries have reduced metadata"],
              "counts": dict(groups), "python_files": len(modules),
              "parse_errors": [r["path"] for r in modules if r["parse_error"]],
              "source_set_sha256": hashlib.sha256(json.dumps([(r["path"], r["sha256"]) for r in modules],
                                                              separators=(",", ":")).encode()).hexdigest(),
              "external_or_unresolved_counts": dict(unresolved.most_common()),
              "identical_python_files": [v for v in duplicate_map.values() if len(v) > 1],
              "non_python_code_and_config": resources, "modules": modules}
    result["scope"].append("parent host modules explicitly packaged by release1/build.py:NAVI")
    result["packaged_host_modules"] = packaged_host
    result["support_file_paths"] = [p.relative_to(SOURCE).as_posix()
                                     for p in discovered if p.suffix != ".py"]
    result["alias_collisions"] = {name: sorted(paths) for name, paths in index.items()
                                  if len(paths) > 1}
    # Potential cycles include conditional imports; they are not runtime failures.
    graph = {r["path"]: set(r["local_dependencies"]) - {r["path"]} for r in modules}
    indices, lows, active, stack, cycles = {}, {}, set(), [], []

    def visit(node):
        indices[node] = lows[node] = len(indices)
        stack.append(node)
        active.add(node)
        for target in sorted(graph[node]):
            if target not in indices:
                visit(target)
                lows[node] = min(lows[node], lows[target])
            elif target in active:
                lows[node] = min(lows[node], indices[target])
        if lows[node] == indices[node]:
            component = []
            while True:
                target = stack.pop()
                active.remove(target)
                component.append(target)
                if target == node:
                    break
            if len(component) > 1:
                cycles.append(sorted(component))

    for node in sorted(graph):
        if node not in indices:
            visit(node)
    result["potential_import_cycles"] = cycles
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "modules.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    lines = ["# Catálogo completo de módulos Python", "", "Generado mediante `scripts/inventory.py`.",
             "Cada fila describe un archivo, no una capacidad independiente. Los roles son orientativos.",
             "Imports y menciones documentales no equivalen a pruebas ejecutadas ni cobertura.", "",
             f"Archivos: {len(modules)}. Errores de parseo: {len(result['parse_errors'])}.", "",
             "Detalle de símbolos, hashes, imports, consumidores, tests y documentos: [modules.json](modules.json).", ""]
    for group in sorted(groups):
        lines += [f"## {group} — {groups[group]} archivos", "",
                  "| Archivo | Descripción declarada / rol orientativo | Dependencias locales | Tests importadores |",
                  "|---|---|---:|---:|"]
        for row in modules:
            if row["path"].split("/")[0] != group:
                continue
            description = row["docstring"].splitlines()[0] if row["docstring"] else row["role_hint"]
            lines.append(f"| [{row['path']}](../../../{row['path']}) | {render_cell(description[:240])} | "
                         f"{len(row['local_dependencies'])} | {len(row['referencing_tests'])} |")
        lines.append("")
    (OUTPUT / "CATALOG.md").write_text("\n".join(lines) + "\n")
    group_edges = Counter((a.split('/')[0], b.split('/')[0])
                          for a, targets in graph.items() for b in targets
                          if a.split('/')[0] != b.split('/')[0])
    ids = {name: f"g{i}" for i, name in enumerate(sorted(groups))}
    diagram = ["flowchart LR"]
    for name, node in ids.items():
        diagram.append(f'  {node}["{name}: {groups[name]} Python"]')
    for (a, b), count in sorted(group_edges.items()):
        diagram.append(f'  {ids[a]} -->|"{count} imports locales"| {ids[b]}')
    (OUTPUT / "dependencies.mmd").write_text("\n".join(diagram) + "\n")
    print(json.dumps({"python_files": len(modules), "groups": dict(groups),
                      "non_python_files": len(resources), "parse_errors": result["parse_errors"],
                      "source_set_sha256": result["source_set_sha256"]}, indent=2))


if __name__ == "__main__":
    main()
