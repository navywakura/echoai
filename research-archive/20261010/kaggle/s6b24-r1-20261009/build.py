"""Offline, deterministic ZIP-profile fork. Never imports a runner or launches tools."""
import copy
import difflib
import hashlib
import io
import json
from pathlib import Path
import shutil
import tarfile
import zipfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PARENT = HERE.parent / "s6b24-20261009"
PARENT_ZIP_SHA = "a2cab9b6a6d5d1dd3fd9b0bcdf294c190f051ef733e695c2af77f4be91a74b2b"
EVIDENCE_SHA = "82a8021e5ba109724436da9992d0eb6f3079c18f8a806d52606ff662bad44b35"
PROFILE_SHA = "de1c1dc9c7206ebde60a3a9de2756d3ae6c8ac1eb6d4fe7904a333553c43b488"
NATIVE_SHA = "a0dac5390422129b6cf4eacda0746d4e1f7b1ee81edea6c96d9aa5f90128b2f8"
CONTRACT = "docs/ECHO45-S6-B24-DESIGN.md"
DECLARED = {"seed/s6b24_model.py", "seed/s6b24.py", CONTRACT}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data if isinstance(data, bytes) else data.encode())


def save(path, value):
    write(path, json.dumps(value, sort_keys=True, indent=2) + "\n")


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise RuntimeError("parent replacement anchor changed: " + old)
    return text.replace(old, new)


def verified_parent():
    bundle = (PARENT / "dataset/echo-b24-private.zip").read_bytes()
    evidence = (PARENT / "output-v1/b24-evidence.tar.gz").read_bytes()
    if digest(bundle) != PARENT_ZIP_SHA or digest(evidence) != EVIDENCE_SHA:
        raise RuntimeError("parent ZIP/evidence changed")
    with zipfile.ZipFile(io.BytesIO(bundle)) as z:
        files = {name: z.read(name) for name in z.namelist()}
    intent = json.loads(files["b24-input/intent.json"])
    with tarfile.open(fileobj=io.BytesIO(evidence), mode="r:gz") as tf:
        records = {m.name: tf.extractfile(m).read() for m in tf.getmembers() if m.isfile()}
    manifest = json.loads(records["b24-results/input/manifest.json"])
    if digest(canonical(manifest).encode()) != PROFILE_SHA or manifest["sources"] != intent["sources"]:
        raise RuntimeError("parent profile or source map changed")
    if len(intent["sources"]) != 100:
        raise RuntimeError("expected exactly 100 parent sources")
    for name, expected in intent["sources"].items():
        if digest(files[name]) != expected or digest((REPO / name).read_bytes()) != expected:
            raise RuntimeError("original frozen source changed: " + name)
    for name, expected in intent["inputs"].items():
        if digest(files["b24-input/" + name]) != expected:
            raise RuntimeError("parent ZIP input changed: " + name)
    for name, expected in manifest["inputs"].items():
        if digest(records["b24-results/input/" + name]) != expected:
            raise RuntimeError("parent runtime input changed: " + name)
    if any(n.startswith("b24-results/executions/") for n in records) or any(
            "b24-results/" + n in records for n in ("budget.json", "model-budget.json", "micro.json")):
        raise RuntimeError("parent has scientific execution evidence")
    calls = ["FORMAT-REF/000", "FORMAT-REF/001", "FORMAT-REF/002", "FORMAT-REF/003",
             "FORMAT-ID/000", "FORMAT-ID/001"]
    ledger = json.loads(records["b24-results/format-preflight/model-budget.json"])
    if ledger["calls"] != calls:
        raise RuntimeError("parent call accounting changed")
    call_receipts = []
    for ident in calls:
        base = "b24-results/format-preflight/calls/" + ident + "/"
        result = json.loads(records[base + "result.json"])
        if result["profile_sha256"] != PROFILE_SHA or result["usage"]["model_calls"] != 1:
            raise RuntimeError("parent call profile/usage mismatch")
        for name, expected in result["files"].items():
            if digest(records[base + name]) != expected:
                raise RuntimeError("parent call artifact changed")
        if (result["proposal"] is None) != (ident == "FORMAT-ID/001"):
            raise RuntimeError("unexpected parent format outcome")
        call_receipts.append(dict(call_id=ident, result_sha256=digest(records[base + "result.json"]),
                                  request_sha256=result["request_sha256"], seed=result["seed"],
                                  usage=result["usage"], seconds=result["seconds"], error=result["error"]))
    failed = "b24-results/format-preflight/calls/FORMAT-ID/001/"
    if records[failed + "stdout.txt"] != b" [end of text]\n\n\n":
        raise RuntimeError("failed stdout changed")
    tokens = json.loads(records[failed + "tokens.json"])["N7"]
    if len(tokens) != 132 or tokens[127] != 151645:
        raise RuntimeError("failed input-EOG boundary changed")
    registry = json.loads(records["b24-results/input/models.json"])
    native_path = PARENT / "output-v1/b24-native.tar.gz"
    if digest(native_path.read_bytes()) != NATIVE_SHA:
        raise RuntimeError("parent native archive changed")
    with tarfile.open(native_path) as tf:
        for name, field in (("llama-cli", "cli_sha256"), ("llama-tokenize", "tokenizer_sha256")):
            if digest(tf.extractfile("cuda-build/bin/" + name).read()) != registry["N7"][field]:
                raise RuntimeError("native registry mismatch")
    return files, intent, manifest, evidence, call_receipts, registry


def overrides(files):
    model = files["seed/s6b24_model.py"].decode()
    model = replace_once(model, "grammar_constraint=True,model='N7',protocols=['r4-json','candidate-id'],",
                         "grammar_constraint=True,model='N7',protocols=['r4-json','candidate-id'],\n"
                         "                logical_batch_size=MAX_INPUT,microbatch_size=64,transport_revision='B24-R1',")
    model = replace_once(model, "    cmd=prior.command(spec,prompt,seed)\n",
                         "    cmd=prior.command(spec,prompt,seed)\n"
                         "    cmd[cmd.index('-b')+1]=str(MAX_INPUT)  # R1: keep prompt EOG off intermediate chunks.\n")
    runner = files["seed/s6b24.py"].decode()
    runner = replace_once(runner, "        audit=review(ROOT,INPUT/'manifest.json')\n",
                          "        audit=review(ROOT,INPUT/'manifest.json')\n"
                          "        recovery=read(INPUT/'recovery.json')\n"
                          "        prior_format_calls=recovery['parent']['charged_format_calls']\n"
                          "        current_format_calls=read(ROOT/'format-preflight/receipt.json')['model_calls']\n")
    runner = replace_once(runner,
        "physical_games=audit['completed_games'],model_calls=audit['model_calls'],format_calls=8,total_model_calls=audit['model_calls']+8,",
        "physical_games=audit['completed_games'],model_calls=audit['model_calls'],\n"
        "                    prior_format_calls=prior_format_calls,current_profile_format_calls=current_format_calls,\n"
        "                    format_calls=prior_format_calls+current_format_calls,\n"
        "                    current_profile_total_model_calls=audit['model_calls']+current_format_calls,\n"
        "                    total_model_calls=audit['model_calls']+current_format_calls+prior_format_calls,\n"
        "                    recovery_sha256=file_sha(INPUT/'recovery.json'),")
    annotation = """

## Recuperacion declarada R1 — 9 de octubre de 2026

Esta adenda prevalece sobre las referencias anteriores a ocho llamadas totales
de formato y a la continuidad del perfil original. R1 es un perfil ZIP nuevo,
con namespace de resultados propio y sin checkpoint inicial. El recibo
`b24-input/recovery.json`, incluido por hash en el intent/manifest, conserva
archivo, perfil y seis llamadas de formato cobradas de v1; cinco pasaron y
FORMAT-ID/001 fallo. V1 inicio cero partidas y cero llamadas cientificas.

El unico cambio de transporte es lote logico `-b 128` a `-b 8192` (MAX_INPUT);
el microlote `-ub 64` permanece igual. La configuracion declara logical_batch_size,
microbatch_size y transport_revision=B24-R1. Pesos, binarios nativos, tokenizer,
mensajes, gramatica, ocho casos sinteticos, semillas, cohortes, presupuestos,
criterios, parser y proteccion de examen conservan sus condiciones anteriores.
No se modifica ninguna fuente original: tres copias declaradas viven en el ZIP R1.

R1 exige ocho inferencias de formato nuevas y completas antes de ciencia. Las
seis previas no se reutilizan como pases ni se borran: formato acumulado 14,
formato del perfil actual 8. El techo cientifico sigue en 72 llamadas y 8.310
partidas; techo de llamadas del perfil actual 80, acumulado 86. El cierre informa
model_calls cientificas, prior_format_calls, current_profile_format_calls,
format_calls acumuladas, current_profile_total_model_calls y total_model_calls
acumuladas, con recovery_sha256. Otro fallo exige otra recuperacion declarada.

El paquete local no acredita un pase de preflight R1. Memoria, latencia y
comportamiento numerico del nuevo lote requieren validacion en el runtime fijado.
"""
    return {"seed/s6b24_model.py": model.encode(), "seed/s6b24.py": runner.encode(),
            CONTRACT: files[CONTRACT] + annotation.encode()}


def build():
    if (HERE / "submitted.json").exists():
        raise RuntimeError("R1 already submitted; cannot rebuild a frozen launch")
    files, old_intent, manifest, evidence, calls, registry = verified_parent()
    edits = overrides(files)
    for name, data in edits.items():
        if name.endswith(".py"):
            compile(data, name, "exec")
        write(HERE / "source-override" / name, data)
    delta = {name: dict(parent_sha256=digest(files[name]), r1_sha256=digest(data))
             for name, data in edits.items()}
    recovery = dict(schema="echoai.s6b24.recovery.v1", recovery_id="S6-B24-R1-20261009",
        status="DECLARED_NOT_EXECUTED", initial_checkpoint=False,
        reason="input ChatML EOG at token index 127 stops the pinned noninteractive CLI at -b 128 before proposal sampling",
        parent=dict(kaggle_ref="rogeernavarro/echo45-s6b24-20261009", version=1,
            bundle_sha256=PARENT_ZIP_SHA, evidence_sha256=EVIDENCE_SHA, profile_sha256=PROFILE_SHA,
            manifest_sha256=digest((canonical(manifest) + "\n").encode()),
            failed_case="FORMAT-ID/001", failed_stdout_sha256="ef9ea7f6620ab14103f8da54b436115262606a0d462faea70dd1661d3d554df8",
            charged_format_calls=6, successful_format_calls=5, calls=calls,
            science_games_started=0, scientific_model_calls_started=0),
        transport_delta=dict(logical_batch_size=dict(parent=128, r1=8192), microbatch_size=64),
        limits=dict(prior_format_calls=6, current_format_calls=8, scientific_model_calls=72,
                    cumulative_model_calls=86, scientific_games=8310),
        assets=dict(native_archive_sha256=NATIVE_SHA, model_sha256=registry["N7"]["model_sha256"],
                    cli_sha256=registry["N7"]["cli_sha256"], tokenizer_sha256=registry["N7"]["tokenizer_sha256"]),
        source_overrides=delta,
        invariants="no parser, prompt, grammar, preflight case, scientific cohort/budget or acceptance-rule changes; preserve failed v1 receipts; fresh eight-case preflight; no silent retry")
    # The manifest is saved by the inherited canonical atomic writer. Bind its actual bytes.
    with tarfile.open(fileobj=io.BytesIO(evidence), mode="r:gz") as tf:
        manifest_bytes = tf.extractfile("b24-results/input/manifest.json").read()
    recovery["parent"]["manifest_sha256"] = digest(manifest_bytes)
    current = dict(files, **edits)
    current["b24-input/recovery.json"] = (canonical(recovery) + "\n").encode()
    intent = copy.deepcopy(old_intent)
    intent["configuration"]["model"].update(logical_batch_size=8192, microbatch_size=64,
                                              transport_revision="B24-R1")
    intent["sources"] = {name: digest(current[name]) for name in old_intent["sources"]}
    intent["inputs"]["recovery.json"] = digest(current["b24-input/recovery.json"])
    intent["contract_sha256"] = digest(current[CONTRACT])
    current["b24-input/intent.json"] = canonical(intent).encode()
    changed = {name for name in files if files[name] != current[name]}
    if changed != DECLARED | {"b24-input/intent.json"}:
        raise RuntimeError("undeclared package diff")
    dest = HERE / "dataset/echo-b24-r1-private.zip"
    dest.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest, "w") as z:
        for name, data in sorted(current.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 9, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, data, compresslevel=9)
    bundle_sha = digest(dest.read_bytes())
    shutil.copyfile(PARENT / "output-v1/b24-native.tar.gz", HERE / "dataset/b24-native.bin")
    write(HERE / "recovery.json", current["b24-input/recovery.json"])
    save(HERE / "intent.json", intent)
    write(HERE / "provenance/parent-intent.json", files["b24-input/intent.json"])
    write(HERE / "provenance/parent-manifest.json", manifest_bytes)
    write(HERE / "provenance/b24-v1-evidence.tar.gz", evidence)
    save(HERE / "source-diff.json", delta)
    source_diff = "".join("".join(difflib.unified_diff(files[n].decode().splitlines(True),
                         current[n].decode().splitlines(True), fromfile="v1/" + n, tofile="r1/" + n))
                          for n in sorted(edits))
    write(HERE / "source-overrides.diff", source_diff)

    old_notebook = (PARENT / "notebook/run.py").read_text()
    notebook = replace_once(old_notebook, "WORK / 'b24-project'", "WORK / 'b24-r1-project'")
    notebook = notebook.replace("'b24-results'", "'b24-r1-results'")
    notebook = notebook.replace("echo-b24-private.zip", "echo-b24-r1-private.zip")
    notebook = replace_once(notebook, "BUNDLE_SHA = '" + PARENT_ZIP_SHA + "'",
                             "BUNDLE_SHA = '" + bundle_sha + "'\nNATIVE_SHA = '" + NATIVE_SHA + "'")
    start, end = notebook.index("def setup_llama():"), notebook.index("def setup_models(hf):")
    notebook = notebook[:start] + """def setup_llama():
    bundles=list(Path('/kaggle/input').rglob('b24-native.bin'))
    if len(bundles)!=1:
        raise RuntimeError('R1 requires exactly one pinned native archive')
    if digest(bundles[0])!=NATIVE_SHA:
        raise RuntimeError('R1 native archive differs from v1')
    with tarfile.open(bundles[0]) as tar:tar.extractall(ASSETS,filter='data')
    return ASSETS/'cuda-build/bin/llama-cli',ASSETS/'cuda-build/bin/llama-tokenize'


""" + notebook[end:]
    write(HERE / "notebook/run.py", notebook)
    write(HERE / "notebook.diff", "".join(difflib.unified_diff(old_notebook.splitlines(True),
          notebook.splitlines(True), fromfile="v1/notebook/run.py", tofile="r1/notebook/run.py")))
    metadata = json.loads((PARENT / "notebook/kernel-metadata.json").read_text())
    metadata.update(id="rogeernavarro/echo45-s6b24-r1-20261009", title="echo45-s6b24-r1-20261009",
                    dataset_sources=["rogeernavarro/echo45-s6b24-r1-private-20261009"])
    save(HERE / "notebook/kernel-metadata.json", metadata)
    save(HERE / "dataset/dataset-metadata.json", dict(id=metadata["dataset_sources"][0],
        title="echo45-s6b24-r1-private-20261009", licenses=[{"name": "other"}],
        description="Private declared B24 R1 ZIP profile and exact v1 native binaries; fresh preflight, no evidence checkpoint."))
    package = dict(path=str(dest), sha256=bundle_sha, configuration_sha256=digest(canonical(intent["configuration"]).encode()),
        recovery_sha256=intent["inputs"]["recovery.json"], source_count=100, unchanged_sources=97,
        declared_source_overrides=sorted(edits), parent_bundle_sha256=PARENT_ZIP_SHA,
        native_archive_sha256=NATIVE_SHA, private=True, published=False,
        initial_checkpoint=False, runtime_results_root="/kaggle/working/b24-r1-results",
        local_validation="see local-validation.json; package build itself performs no inference or games")
    save(HERE / "package.json", package)
    save(HERE / "provenance/build.json", dict(parent_source_hashes=old_intent["sources"],
        r1_source_hashes=intent["sources"], changed_zip_members=sorted(changed),
        added_zip_members=sorted(set(current) - set(files)),
        parent_notebook_sha256=digest(old_notebook.encode()), r1_notebook_sha256=digest(notebook.encode()),
        builder_sha256=digest(Path(__file__).read_bytes()), package=package))
    print(json.dumps(package, indent=2))


if __name__ == "__main__":
    build()
