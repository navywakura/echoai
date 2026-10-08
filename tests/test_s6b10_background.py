import json
from pathlib import Path
import tempfile
import unittest

from seed.s6b10_background import check_audit_cache
from seed.game_selfimprove import sha


class RestartCache(unittest.TestCase):
    def test_empty_shutdown_artifact_blocks_restart_and_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cache = root / 'pilot-audit/cache/replay'
            cache.mkdir(parents=True)
            path = cache / 'key.json'
            path.write_bytes(b'')
            with self.assertRaisesRegex(ValueError, 'Incomplete audit cache'):
                check_audit_cache(root)
            self.assertEqual(path.read_bytes(), b'')

    def test_valid_cache_survives_check_and_altered_record_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cache = root / 'pilot-audit/cache/main'
            cache.mkdir(parents=True)
            path = cache / 'key.json'
            row = {'key': 'key', 'record': {'levels': 3}, 'digest': sha({'levels': 3})}
            path.write_text(json.dumps(row))
            before = path.read_bytes()
            self.assertEqual(check_audit_cache(root), 1)
            self.assertEqual(path.read_bytes(), before)
            row['record']['levels'] = 4
            path.write_text(json.dumps(row))
            with self.assertRaisesRegex(ValueError, 'digest mismatch'):
                check_audit_cache(root)


if __name__ == '__main__':
    unittest.main()
