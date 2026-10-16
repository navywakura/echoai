"""Regenerate seven figures without inference or access to private authorities."""
from pathlib import Path
import argparse
import hashlib
import json
import runpy

HERE=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--repository',type=Path,default=HERE.parents[3])
parser.add_argument('--output',type=Path,default=HERE/'regenerated')
args=parser.parse_args()
manifest=json.loads((HERE/'MANIFEST.json').read_bytes())
for name,digest in manifest['sha256'].items():
    if hashlib.sha256((HERE/name).read_bytes()).hexdigest()!=digest:
        raise SystemExit('Archive file changed: '+name)
original=runpy.run_path(str(args.repository/'scripts/plot_swebench_results.py'),run_name='plotter')
if hashlib.sha256((args.repository/'scripts/plot_swebench_results.py').read_bytes()).hexdigest()!=manifest['original_plotter_sha256']:
    raise SystemExit('Original plotter differs from the frozen experiment')
registration=original['load_registration'](HERE/'SWE-CONTRACT.json',HERE/'SWE-SAMPLE.json')
analysis=json.loads((HERE/'analysis.json').read_bytes())
original['render'](analysis,args.output/'figures',registration=registration)
supplemental=runpy.run_path(str(HERE/'render_supplemental.py'),run_name='supplemental')
supplemental['render'].__globals__['G']=args.output
supplemental['render'](json.loads((HERE/'full-results.json').read_bytes()),analysis)
print('7 PNG + 7 PDF regenerated. File hashes checked; HMAC custody requires the original local store.')
