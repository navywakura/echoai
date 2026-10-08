import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from echo_nexus.connections import parse, profile
from echo_nexus.config import load_config, redact
from echo_nexus.transport import Cortex


class Connections(unittest.IsolatedAsyncioTestCase):
    async def test_file_reference_is_lazy_and_runtime_secret_is_redacted(self):
        with tempfile.TemporaryDirectory() as root:
            file = Path(root) / '.key'
            p = parse(['api', 'https://example.org/v1', 'example', '@' + str(file)])
            # An absent file is allowed until the first request; no secret is read on setup.
            self.assertEqual(profile(p)['key_file'], str(file))
            secret = 'fixture-private-credential-only'
            file.write_text('export OPENROUTER_API_KEY="' + secret + '"\n')
            seen = []
            def response(request):
                seen.append(request.headers['Authorization'])
                return httpx.Response(200, json={'choices': [{'message': {'content': secret}}]})
            client = httpx.AsyncClient(transport=httpx.MockTransport(response))
            with patch('echo_nexus.transport.httpx.AsyncClient', return_value=client):
                answer = await Cortex(p['url'], p['model'], key_file=p['key_file']).ask('ping')
            self.assertEqual(seen, ['Bearer ' + secret])
            self.assertNotIn(secret, redact(answer))
            self.assertNotIn(secret, json.dumps(p))

    async def test_save_restart_use_remove_and_default(self):
        from echo_nexus.app import Nexus
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, {
            'ECHO_NEXUS_HOME': root, 'ECHO_NEXUS_STATE': root
        }):
            first = Nexus(stars=False)
            async with first.run_test() as pilot:
                await first.execute('/connect api https://example.org/v1 fixture @/missing/.key')
                await first.execute('/connections save remote')
                await first.execute('/connections default remote')
                self.assertEqual(load_config()['default_connection'], 'remote')
            second = Nexus(stars=False)
            async with second.run_test() as pilot:
                await pilot.pause()
                self.assertEqual(second.active_profile, 'remote')
                self.assertEqual(second.cortex.key_file, '/missing/.key')
                await second.execute('/connections list')
                await second.execute('/connections remove remote')
                self.assertNotIn('default_connection', load_config())
                self.assertFalse(load_config()['connections'])
