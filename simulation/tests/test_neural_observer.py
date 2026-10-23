import hashlib
import json
import unittest

from echo5.neural_observer import NeuralObserver


class NeuralObserverTests(unittest.TestCase):
    def test_measured_frames_match_historical_network_not_random_animation(self):
        probe = NeuralObserver()
        observation = {'cells': [[1, 2, 'key']], 'direction': 1}
        before = json.dumps(observation, sort_keys=True)
        result = probe.observe(observation)
        layer = probe.qn.Layer256()
        saw = False
        total = 0
        for frame in result['frames']:
            tick = frame['tick']
            bits = layer.step(result['stimulus'], tick < probe.qn.STIM_WINDOW,
                              tick >= probe.qn.STIM_WINDOW + 1 and not saw)
            saw = saw or bool(bits & layer.code_mask)
            self.assertEqual(frame['potential'], layer.v)
            self.assertEqual(frame['spikes'], [i for i in range(256) if bits >> i & 1])
            total += bits.bit_count()
        self.assertEqual(result['spikes_total'], total)
        self.assertEqual(json.dumps(observation, sort_keys=True), before)
        self.assertFalse(result['drives_policy'])
        self.assertIsNone(result['energy_joules'])
        self.assertEqual(result, probe.observe(observation))

    def test_input_provenance_and_true_hypercube_topology(self):
        p = NeuralObserver()
        r = p.observe({'observed': False})
        self.assertEqual(r['input_sha256'], hashlib.sha256(b'{"observed":false}').hexdigest())
        edges = {(min(i, i ^ (1 << b)), max(i, i ^ (1 << b)))
                 for i in range(256) for b in range(8)}
        self.assertEqual(len(edges), r['edges'])
        self.assertNotEqual(r['input_sha256'], p.observe({'observed': True})['input_sha256'])
