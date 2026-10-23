"""Synthetic parameter-boundary tests; these cannot certify a flight."""
import unittest
from copy import deepcopy
from pathlib import Path
import struct
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
import subprocess

from echo5.sitl_parameters import (EXTRA, LEGACY_ALLOWED, audit_parameters,
                                  configure_driver, validate_parameters, packet_integrity,
                                  reconcile_parameter_evidence, require_parameter_manifest,
                                  extract_ulog_parameters)


class ParameterCalibrationTests(unittest.TestCase):
    def test_velocity_calibration_accepts_bounded_accelerometer_uncertainty(self):
        class Driver:
            ALLOWED = set(LEGACY_ALLOWED)
        parameters = {'EKF2_ACC_NOISE': .7, EXTRA: .01}
        receipt = configure_driver(Driver, parameters)
        self.assertIn('EKF2_ACC_NOISE', Driver.ALLOWED)
        self.assertEqual(receipt['requested'], parameters)
        self.assertEqual(audit_parameters(parameters, parameters, []), [])
        self.assertIn('ulog_parameter_changed:EKF2_ACC_NOISE',
                      audit_parameters(parameters, parameters, [[42, 'EKF2_ACC_NOISE', .35]]))
        for value in (.009, 1.001, True, float('inf')):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_parameters({'EKF2_ACC_NOISE': value})

    def test_extension_preserves_inherited_allowlist_and_requires_known_driver(self):
        class Driver:
            ALLOWED = set(LEGACY_ALLOWED)
        old = Driver.ALLOWED
        receipt = configure_driver(Driver, {EXTRA: .01, 'EKF2_HGT_REF': 1})
        self.assertEqual(old, LEGACY_ALLOWED)
        self.assertEqual(Driver.ALLOWED, LEGACY_ALLOWED | {EXTRA})
        self.assertEqual(receipt['requested'], {EXTRA: .01, 'EKF2_HGT_REF': 1})
        with self.assertRaises(ValueError):
            configure_driver(Driver, {EXTRA: .01})

    def test_rejects_unbounded_unknown_boolean_string_or_nonfinite_request(self):
        bad = [{EXTRA: x} for x in (-.001, .010001, .06, True, '0.01', float('nan'), float('inf'))]
        bad += [{'COM_ARM_WO_GPS': 1}, {'EKF2_GPS_DELAY': False}, []]
        for request in bad:
            with self.subTest(request=request), self.assertRaises(ValueError):
                validate_parameters(request)

    def test_readback_accepts_float32_rounding_not_missing_or_wrong_values(self):
        expected = {EXTRA: .01, 'EKF2_HGT_REF': 1}
        actual = {EXTRA: .009999999776, 'EKF2_HGT_REF': 1}
        self.assertEqual(audit_parameters(expected, actual, []), [])
        for value in (.003, None, True, '0.01', float('nan')):
            with self.subTest(value=value):
                self.assertIn('ulog_parameter_readback:' + EXTRA,
                              audit_parameters(expected, {**actual, EXTRA: value}, []))

    def test_rejects_in_flight_change_even_when_it_returns_to_expected_value(self):
        expected = {EXTRA: .01}
        changes = [[10, EXTRA, .003], [20, EXTRA, .01]]
        self.assertEqual(audit_parameters(expected, expected, changes),
                         ['ulog_parameter_changed:' + EXTRA])
        self.assertEqual(audit_parameters(expected, expected, [[10, EXTRA, .009999999776]]), [])
        for changes in (None, [[10, EXTRA]], [[10, [], .01]]):
            with self.assertRaises(ValueError):
                audit_parameters(expected, expected, changes)

    def test_binary_framing_rejects_truncated_header_body_dropouts_and_appends(self):
        header = b'ULog\x01\x12\x35\x01' + struct.pack('<Q', 1)
        frame = lambda kind, body: struct.pack('<HB', len(body), ord(kind)) + body
        key = b'float EKF2_ACC_B_NOISE'
        parameter = bytes([len(key)]) + key + struct.pack('<f', .01)
        valid = header + frame('B', b'\x01' + b'\x00'*39) + frame('P', parameter)
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)/'synthetic.ulg'
            p.write_bytes(valid)
            self.assertEqual(packet_integrity(p)['bytes'], len(valid))
            invalid = [valid[:-1], valid+b'\x01', valid+frame('O', b'\x01\x00'),
                       header+frame('B', b'\x00'*8+b'\x01'+b'\x00'*31),
                       header, header+frame('D', b'1234'),
                       valid+frame('P', parameter[:-1])+frame('P',parameter)]
            for raw in invalid:
                p.write_bytes(raw)
                with self.subTest(raw=raw[-8:]), self.assertRaises(ValueError):
                    packet_integrity(p)

    def test_parameter_binding_rejects_substitution_even_with_matching_metadata(self):
        original = dict(schema='echo5.sitl.ulog-parameters.v1', nonce='a'*32, sha256='b'*64,
                        initial={EXTRA:.003}, changes=[], health=dict(complete_frames=True,
                            parser_clean_eof=True, corruption=False, dropouts=0,
                            packets=10, start_us=1, end_us=10000))
        forged = deepcopy(original);forged['initial'][EXTRA] = .01
        with self.assertRaises(ValueError):
            reconcile_parameter_evidence(forged, original, nonce='a'*32, sha256='b'*64,
                                         start_ns=2000, end_ns=10_000_000)
        for field in ('nonce', 'sha256'):
            other = deepcopy(original);other[field] = 'c'*64
            with self.assertRaises(ValueError):
                reconcile_parameter_evidence(other, other, nonce='a'*32, sha256='b'*64,
                                             start_ns=2000, end_ns=10_000_000)

    def test_parameter_history_requires_coverage_and_clean_parser(self):
        receipt = dict(schema='echo5.sitl.ulog-parameters.v1', nonce='a'*32, sha256='b'*64,
                       health=dict(complete_frames=True, parser_clean_eof=True, corruption=False, dropouts=0,
                                   packets=10, start_us=1, end_us=1_000_000))
        args = dict(nonce='a'*32, sha256='b'*64, start_ns=2000, end_ns=1_000_000_000)
        reconcile_parameter_evidence(receipt, receipt, **args)
        for field, value in [('complete_frames',False), ('parser_clean_eof',False),
                             ('corruption',True), ('dropouts',1),
                             ('start_us',3), ('end_us',800_000), ('packets',0)]:
            changed = deepcopy(receipt);changed['health'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                reconcile_parameter_evidence(changed, changed, **args)

    def test_manifest_cannot_omit_parameter_extraction_or_binary(self):
        names = ['configuration.json','runner.py','sitl_parameters.py','out/px4-parameter-adapter.json',
                 'out/ulog-parameters.json','out/ulog-evidence.json','out/wd/flight.ulg']
        manifest = dict.fromkeys(names, 'x'*64)
        require_parameter_manifest(manifest, 'wd/flight.ulg')
        for name in names:
            with self.subTest(name=name), self.assertRaises(ValueError):
                require_parameter_manifest({k:v for k,v in manifest.items() if k != name}, 'wd/flight.ulg')

    def test_silently_stopped_parser_cannot_certify_clean_eof(self):
        raw = b'ULog\x01\x12\x35\x01' + struct.pack('<Q', 1) + struct.pack('<HB', 40, ord('B')) + bytes(40)
        def silent_parser(reader, **kwargs):
            reader.read()  # All bytes consumed, but no EOF probe: premature return.
            reader.close()
            return SimpleNamespace(file_corruption=False, dropouts=[], start_timestamp=1, last_timestamp=100)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'framed.ulg';path.write_bytes(raw)
            with patch.dict('sys.modules', {'pyulog':SimpleNamespace(ULog=silent_parser)}):
                with self.assertRaisesRegex(ValueError, 'clean EOF'):
                    extract_ulog_parameters(path, 'a'*32, 'framed.ulg')

    def test_extractor_timeout_becomes_failed_evidence_and_cleans_only_owned_container(self):
        from echo5 import sitl
        calls = []
        def command(argv, timeout):
            calls.append((argv, timeout))
            if argv[1] == 'run':
                raise subprocess.TimeoutExpired(argv, timeout)
            return SimpleNamespace(returncode=1 if argv[1:3] == ['container','exists'] else 0)
        with patch.object(sitl, '_command', side_effect=command):
            with self.assertRaisesRegex(ValueError, 'TimeoutExpired'):
                sitl._independent_parameters(Path('/unused.ulg'), 'a'*32, 'unused.ulg')
        self.assertEqual(len(calls), 3)
        run = calls[0][0];name = run[run.index('--name')+1]
        self.assertTrue(name.startswith('echo5-ulog-'))
        self.assertIn('--timeout=45', run)
        self.assertEqual(calls[1][0], ['podman','rm','--force','--ignore',name])
        self.assertEqual(calls[2][0], ['podman','container','exists',name])


if __name__ == '__main__':
    unittest.main()
