import asyncio
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

import httpx

from echo_nexus.app import Nexus
from echo_nexus.connections import parse
from echo_nexus.config import register_secret
from echo_nexus.editor import MessageEditor
from echo_nexus.transport import Cortex, endpoint, model_catalog


class Nexus15(unittest.IsolatedAsyncioTestCase):
    async def test_missing_model_fails_before_inference_or_credential_read(self):
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, {'ECHO_NEXUS_HOME':root,'ECHO_NEXUS_STATE':root}):
            app = Nexus(autoconnect=False)
            async with app.run_test():
                with patch('echo_nexus.app.model_catalog', AsyncMock(return_value=[{'id':'openrouter/free'}])):
                    await app.execute('/connect openrouter retired:free @/missing/key')
                self.assertIsNone(app.cortex)
                self.assertIn('no figura', app.last_message)
                self.assertEqual(endpoint('https://openrouter.ai/api/v1/chat/completions'), 'https://openrouter.ai/api/v1')
                self.assertEqual(parse(['openrouter','free'])['model'], 'openrouter/free')

    async def test_catalog_filters_free_and_never_sends_authorization(self):
        requests=[]
        def respond(request):
            requests.append(request)
            return httpx.Response(200,json={'data':[
                {'id':'free','pricing':{'prompt':'0','completion':'0'}},
                {'id':'paid','pricing':{'prompt':'0.5','completion':'1'}},
                {'id':'unknown','pricing':{}}]})
        client=httpx.AsyncClient(transport=httpx.MockTransport(respond))
        with patch('echo_nexus.transport.httpx.AsyncClient',return_value=client):
            rows=await model_catalog()
        self.assertEqual([r['id'] for r in rows],['free'])
        self.assertNotIn('authorization',requests[0].headers)

    async def test_provider_error_is_actionable_redacted_and_not_saved(self):
        register_secret('fixture-secret-in-error')
        client=httpx.AsyncClient(transport=httpx.MockTransport(lambda request:httpx.Response(404,json={
            'error':{'message':'Unavailable fixture-secret-in-error','metadata':{'raw':'must-not-display'}}})))
        c=Cortex('https://example.org/v1','missing')
        with patch('echo_nexus.transport.httpx.AsyncClient',return_value=client):
            with self.assertRaises(RuntimeError) as caught:
                await c.ask('hola')
        text=str(caught.exception)
        self.assertIn('/models free',text)
        self.assertNotIn('fixture-secret-in-error',text)
        self.assertNotIn('must-not-display',text)
        self.assertEqual(c.history,[])

    async def test_editor_sends_pasted_commands_as_one_message(self):
        from textual.widgets import TextArea
        seen=[]
        class Model:
            model='fixture'
            async def ask(self,text,**kw):
                seen.append(text)
                return 'fixture answer'
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ,{'ECHO_NEXUS_HOME':root,'ECHO_NEXUS_STATE':root}):
            app=Nexus(autoconnect=False)
            async with app.run_test() as pilot:
                app.cortex=Model()
                await app.execute('/paste')
                await pilot.pause()
                self.assertIsInstance(app.screen,MessageEditor)
                draft='/disconnect\n/world start dev-world'
                app.screen.query_one(TextArea).load_text(draft)
                await pilot.click('#send')
                await pilot.pause()
                self.assertEqual(seen,[draft])
                self.assertIsNotNone(app.cortex)
                self.assertIsNone(app.world_task)

    async def test_world_keeps_running_during_chat_and_editor_then_stops(self):
        script='import json,time\nwhile True:\n print(json.dumps({"kind":"progress","step":1,"budget":"session"}),flush=True)\n time.sleep(.02)'
        seen=[]
        class Model:
            model='fixture'
            async def ask(self,text,**kw):
                seen.append(text)
                await asyncio.sleep(.04)
                return 'proposal'
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ,{'ECHO_NEXUS_HOME':root,'ECHO_NEXUS_STATE':root}):
            p=Path(root)/'backend.json'
            p.write_text(json.dumps({'schema':'echo-nexus-backend-v1','tests':[], 'worlds':[
                {'id':'dev-world','title':'fixture','kind':'development','argv':[sys.executable,'-u','-c',script]}]}))
            app=Nexus(backend=str(p),autoconnect=False)
            async with app.run_test() as pilot:
                app.cortex=Model()
                await app.execute('/world start dev-world')
                for _ in range(30):
                    await pilot.pause(.02)
                    if app.world_runner.process:break
                proc=app.world_runner.process
                self.assertIsNotNone(proc)
                app.consume({'kind':'decision','action':'wait','reason':'observed'},'fixture')
                app.consume({'kind':'frame','grid':[[1]],'observer':{'secret_coordinate':'viewer-only'}},'fixture')
                await app.execute('/ask Qué observaste?')
                self.assertIn('observed',seen[-1])
                self.assertNotIn('secret_coordinate',seen[-1])
                self.assertIsNone(proc.returncode)
                await app.execute('/paste')
                await pilot.pause(.05)
                self.assertIsInstance(app.screen,MessageEditor)
                app.screen.action_cancel()
                await pilot.pause()
                await app.execute('/world stop')
                self.assertIsNone(app.world_task)
                self.assertIsNotNone(proc.returncode)

    async def test_copy_why_uses_clean_source_text(self):
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ,{'ECHO_NEXUS_HOME':root,'ECHO_NEXUS_STATE':root}):
            app=Nexus(autoconnect=False)
            async with app.run_test():
                app.consume({'kind':'decision','action':'left','reason':'actual source'},'fixture')
                with patch('echo_nexus.app.clipboard', AsyncMock(return_value=True)) as copy:
                    await app.execute('/copy why')
                self.assertIn('actual source',copy.call_args.args[0])
                self.assertNotIn('\x1b',copy.call_args.args[0])
