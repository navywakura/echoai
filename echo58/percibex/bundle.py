"""Deterministic isolated imports of byte-identical existing source files."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[2]
FROZEN = {
    'echoai/nexus0/pattern1.py': 'nexus0/pattern1.py',
    'echoai/nexus0/pattern1r_v4/memory.py': 'nexus0/pattern1r_v4/memory.py',
    'echoai/nexus0/pattern1r_v4/assets/consumer.py': 'nexus0/pattern1r_v4/assets/consumer.py',
    'echoai/echo58/memx/memory.py': 'echo58/memx/memory.py',
}
FLIGHT = {'frozen_tap.py': 'nexus0/pattern1r/assets/sensor_runner.py',
          'flightrunner_survey.py': 'nexus0/pattern1r_v4/assets/flightrunner_survey.py'}


def build(path, *, flight=False):
    files = dict(FROZEN)
    if flight: files.update(FLIGHT)
    for name in ('protocol', 'online', 'consumer', 'flight'):
        files['echoai/echo58/percibex/'+name+'.py'] = 'echo58/percibex/'+name+'.py'
    blobs = {target: (ROOT/source).read_bytes() for target, source in files.items()}
    # Namespace shells avoid executing the unrelated historical Agent initializer.
    # They contain no learner/control algorithm and are inventoried explicitly.
    for target in list(blobs):
        bits = target.split('/')
        for n in range(1, len(bits)):
            blobs.setdefault('/'.join(bits[:n])+'/__init__.py', b'')
    entry = 'flight' if flight else 'consumer'
    blobs['__main__.py'] = ('from echoai.echo58.percibex.'+entry+' import main\nraise SystemExit(main())\n').encode()
    manifest = {k: hashlib.sha256(v).hexdigest() for k, v in sorted(blobs.items())}
    blobs['bundle-manifest.json'] = json.dumps(manifest, sort_keys=True).encode()
    with zipfile.ZipFile(path, 'x', compression=zipfile.ZIP_STORED) as z:
        for name, raw in sorted(blobs.items()):
            info = zipfile.ZipInfo(name, date_time=(1980,1,1,0,0,0))
            z.writestr(info, raw)
    return dict(path=str(path), sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(),
                files=manifest, original_sources={s: manifest[t] for t,s in files.items()
                                                 if t in FROZEN or t in FLIGHT})
