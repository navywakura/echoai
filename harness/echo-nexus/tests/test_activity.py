import asyncio
import json
import os
import tempfile
import unittest
from unittest.mock import patch

import httpx

from echo_nexus.decisions import DecisionView
from echo_nexus.transport import Cortex


class Activity(unittest.IsolatedAsyncioTestCase):
    async def test_stream_shows_answer_and_ignores_reasoning_and_tools(self):
        rows = [
            {'choices': [{'delta': {'reasoning': 'private-field'}}]},
            {'choices': [{'delta': {'tool_calls': [{'id': 'unused'}]}}]},
            {'choices': [{'delta': {'content': 'Hola '}}]},
            {'choices': [{'delta': {'content': 'ECHO'}}]},
        ]
        wire = ''.join('data: ' + json.dumps(r) + '\n\n' for r in rows) + 'data: [DONE]\n\n'
        client = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(
            200, headers={'content-type': 'text/event-stream'}, text=wire)))
        chunks, phases = [], []
        with patch('echo_nexus.transport.httpx.AsyncClient', return_value=client):
            c = Cortex('https://example.org/v1', 'fixture')
            result = await c.ask('hola', progress=phases.append, on_delta=chunks.append)
        self.assertEqual(result, 'Hola ECHO')
        self.assertEqual(chunks, ['Hola ', 'ECHO'])
        self.assertEqual(phases[-1], 'Respuesta completada')
        self.assertNotIn('private-field', str(c.history))

    async def test_interrupted_stream_is_not_stored_as_a_complete_answer(self):
        wire = 'data: {"choices":[{"delta":{"content":"partial"}}]}\n\n'
        client = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(
            200, headers={'content-type': 'text/event-stream'}, text=wire)))
        with patch('echo_nexus.transport.httpx.AsyncClient', return_value=client):
            c = Cortex('https://example.org/v1', 'fixture')
            with self.assertRaisesRegex(RuntimeError, 'interrumpió'):
                await c.ask('hola', on_delta=lambda s: None)
        self.assertEqual(c.history, [])

    async def test_cancel_stops_visible_activity_and_preserves_observed_decisions(self):
        from echo_nexus.app import Nexus
        started = asyncio.Event()
        class Slow:
            model = 'fixture'
            async def ask(self, prompt, *, progress, on_delta):
                progress('Solicitud enviada · esperando al modelo')
                on_delta('Parte pública')
                started.set()
                await asyncio.Event().wait()
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, {
            'ECHO_NEXUS_HOME': root, 'ECHO_NEXUS_STATE': root
        }):
            app = Nexus(stars=False)
            async with app.run_test(size=(80, 30)):
                app.cortex = Slow()
                app.consume({'kind': 'decision', 'action': 'wait', 'branches': [{'label': 'Observed guard'}]})
                task = asyncio.create_task(app.execute('hola'))
                await started.wait()
                self.assertEqual(app.stream_text, 'Parte pública')
                self.assertNotIn('ended', app.activity)
                await app.action_cancel()
                await task
                self.assertEqual(app.activity['stage'], 'Cancelado')
                self.assertIn('ended', app.activity)
                self.assertIn('Observed guard', app.decisions.explain())
                await app.execute('/why')

    def test_decision_view_never_supplies_a_missing_reason(self):
        view = DecisionView()
        view.consume({'kind': 'decision', 'action': 'left'}, 'fixture')
        self.assertIn('esta fuente no lo proporcionó', view.explain())
        self.assertIn('left', view.explain())
        view.clear()
        self.assertNotIn('left', view.explain())

    def test_victory_hypothesis_is_distinct_from_active_destination(self):
        view = DecisionView()
        view.consume({'kind': 'observation', 'beliefs': {
            'pos': [55, 47], 'target': None, 'rule': {'4': [8, 0]},
            'recent_hypotheses': [[1, ['near', 3], 'proposed']]}}, 'actor')
        view.consume({'kind': 'result', 'level_up': True, 'step': 56}, 'actor')
        view.consume({'kind': 'result', 'level_up': False, 'step': 57}, 'actor')
        report = view.explain()
        self.assertIn('destino activo ninguno', report)
        self.assertIn('Hipótesis visual de meta: color 3 (propuesta)', report)
        self.assertIn('Metas alcanzadas en esta sesión: 1', report)
        self.assertNotIn('objetivo sin identificar', report)
        view.clear()
        self.assertNotIn('Metas alcanzadas', view.explain())

    def test_coordinates_and_heading_do_not_modify_the_environment_grid(self):
        from echo_nexus.world import world_text
        grid = [[0, 1, 2], [3, 4, 5]]
        original = json.dumps(grid)
        text = world_text(grid, 40, 15, {'position': [1, 1], 'direction': [1, 0], 'direction_kind': 'mirada'})
        self.assertIn('→', text.plain)
        self.assertIn('y/x', text.plain)
        self.assertIn('mirada', text.plain)
        self.assertEqual(json.dumps(grid), original)

    async def test_agent_selection_changes_catalog_and_preserves_the_chat_connection(self):
        from pathlib import Path
        from echo_nexus.app import Nexus
        from echo_nexus.backend import read_manifest
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, {
            'ECHO_NEXUS_HOME': root, 'ECHO_NEXUS_STATE': root
        }):
            file = Path(root) / 'backend.json'
            def entry(agent):
                return {'id': agent, 'tests': [{'id': 'world', 'title': agent, 'kind': 'development',
                    'argv': ['fixture', agent]}]}
            file.write_text(json.dumps({'schema': 'echo-nexus-backend-v1', 'tests': [],
                'agents': [entry('echo4'), entry('echo45')], 'default_agent': 'echo45'}))
            app = Nexus(backend=str(file), stars=False)
            async with app.run_test():
                self.assertEqual(app.selected_agent, 'echo45')
                await app.execute('/connect api https://example.org/v1 model')
                chat = app.cortex
                await app.execute('/agent echo4')
                self.assertEqual(app.catalog[0]['argv'], ['fixture', 'echo4'])
                self.assertIs(app.cortex, chat)
                app.consume({'kind': 'progress', 'cases_done': 2, 'cases_total': 3, 'solved': 1})
                self.assertEqual(app.metrics['solved'], 1)
            bad = json.loads(file.read_text())
            bad['agents'][0]['tests'][0]['argv'] = 'shell string'
            file.write_text(json.dumps(bad))
            with self.assertRaises(ValueError):
                read_manifest(file)
