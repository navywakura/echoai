from concurrent.futures import ThreadPoolExecutor
import importlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


class ArtifactTests(unittest.TestCase):
    def test_interrupted_publication_leaves_no_partial_final(self):
        a = importlib.import_module('echoai.echo58.crece.artifacts')
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/'receipt.json'
            with patch.object(a.os, 'link', side_effect=OSError('interrupted')):
                with self.assertRaises(OSError):
                    a.save_new(path, {'data':list(range(100))})
            self.assertFalse(path.exists())
            a.save_new(path, {'ok':True})
            with self.assertRaises(FileExistsError):
                a.save_new(path, {'ok':True})

    def test_concurrent_identical_objects_and_durable_reservation(self):
        a = importlib.import_module('echoai.echo58.crece.artifacts')
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/'object'
            with ThreadPoolExecutor(max_workers=8) as pool:
                list(pool.map(lambda _: a.publish(path, b'content', identical=True), range(32)))
            self.assertEqual(path.read_bytes(), b'content')
            with self.assertRaises(ValueError):
                a.publish(path, b'different', identical=True)
            events = []
            original_link, original_sync = os.link, os.fsync
            def link(*args):
                events.append('link')
                return original_link(*args)
            def sync(*args):
                events.append('sync')
                return original_sync(*args)
            with patch.object(a.os, 'link', side_effect=link), patch.object(a.os, 'fsync', side_effect=sync):
                a.save_new(Path(d)/'reservation.json', {'reserved':True})
            self.assertEqual(events, ['sync','link','sync'])
