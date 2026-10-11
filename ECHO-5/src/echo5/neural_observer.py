"""Measured Q8/LIF diagnostic, deliberately outside the acting policy.

Uses the historical Layer256 unchanged. The input is an observation digest,
not a semantic claim. Nothing from this diagnostic is sent back to the actor.
"""
import hashlib
import json
from pathlib import Path

from .legacy import module


class NeuralObserver:
    def __init__(self):
        self.qn = module('core.qn')
        self.spoke = module('core.spoke')
        self.layer = self.qn.Layer256()
        self.source_sha256 = hashlib.sha256(Path(self.qn.__file__).read_bytes()).hexdigest()

    def observe(self, observation):
        encoded = json.dumps(observation, sort_keys=True, ensure_ascii=False,
                             separators=(',', ':'), allow_nan=False).encode()
        raw = hashlib.sha256(encoded).digest()
        vertex, latency, input_ticks = self.spoke.encode_event(raw)
        stimulus = vertex & 255
        self.layer.reset()
        frames, counts, saw_code = [], [0] * 256, False
        for tick in range(self.qn.T_MAX):
            hop = tick >= self.qn.STIM_WINDOW + 1 and not saw_code
            bits = self.layer.step(stimulus, tick < self.qn.STIM_WINDOW, hop)
            if bits & self.layer.code_mask:
                saw_code = True
            fired = [i for i in range(256) if bits >> i & 1]
            for neuron in fired:
                counts[neuron] += 1
            frames.append({'tick': tick, 'spikes': fired, 'potential': list(self.layer.v)})
        return {'schema': 'echo5.neural-diagnostic.v1', 'module': 'echoai.core.qn.Layer256',
                'role': 'observation_diagnostic', 'drives_policy': False,
                'input_kind': 'sha256_of_public_observation', 'input_sha256': raw.hex(),
                'source_sha256': self.source_sha256, 'topology': 'Q8', 'neurons': 256,
                'edges': 1024, 'vertex': vertex, 'stimulus': stimulus,
                'input_latency': latency, 'input_ticks': input_ticks,
                'frames': frames, 'spike_counts': counts, 'spikes_total': sum(counts),
                'observer_neuron_updates': 256 * self.qn.T_MAX,
                'energy_joules': None}
