"""Two accuracy labels; assert all other source bytes remain identical."""
import difflib
import hashlib
import json
from pathlib import Path

path = Path('/opt/PX4-Autopilot/src/modules/simulation/sensor_gps_sim/SensorGpsSim.cpp')
original = path.read_text()
replacements = {'sensor_gps.eph = 0.9f;': 'sensor_gps.eph = 0.2f;',
                'sensor_gps.s_variance_m_s = 0.4f;': 'sensor_gps.s_variance_m_s = 0.158f;'}
changed = original
for before, after in replacements.items():
    assert changed.count(before) == 1, before
    changed = changed.replace(before, after)
restored = changed
for before, after in replacements.items():
    restored = restored.replace(after, before)
assert restored == original
for unchanged in ('generate_wgn() * 0.2', 'noiseGauss3f(0.06f, 0.077f, 0.158f)',
                  'sensor_gps.epv = 1.78f;', 'sensor_gps.timestamp_sample = gpos.timestamp_sample;'):
    assert unchanged in changed
patch = ''.join(difflib.unified_diff(original.splitlines(True), changed.splitlines(True),
                                   fromfile='SensorGpsSim.stock.cpp', tofile='SensorGpsSim.v5.cpp'))
path.write_text(changed)
Path('/opt/gps-accuracy.patch').write_text(patch)
Path('/opt/gps-accuracy.json').write_text(json.dumps(dict(
    before_sha256=hashlib.sha256(original.encode()).hexdigest(),
    after_sha256=hashlib.sha256(changed.encode()).hexdigest(),
    replacements=replacements, other_source_bytes_unchanged=True),sort_keys=True))
