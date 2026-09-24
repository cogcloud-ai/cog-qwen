"""Model-free candidate, admission, transport and artifact regressions."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from contracts import Fault, validate_request, DECLARATION, validate
from provider import bind
from reference_host import Store, admit
from gateway import infer, make_server
from local_http import MODEL_ID, LocalHTTP, NoRedirect

TOKEN = 'test-token-only-' + 'x' * 40


class FakeModel:
    def __init__(self):
        self.calls = 0
        self.model = MODEL_ID
        self.content = '{"ok":true}'
    def key_health(self, key): return {'data': [{'id': self.model}]}
    def catalog(self, model): return {'model_id': self.model}
    def completion(self, body, key):
        self.calls += 1
        return {'model': self.model, 'choices': [{'message': {'role':'assistant','content':self.content}}]}


class ProviderTests(unittest.TestCase):
    def setUp(self):
        self.request = json.loads((ROOT / 'examples/bind-request.json').read_text())
        self.api = FakeModel()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name) / 'state')
        env = patch.dict(os.environ, {'COG_QWEN_TOKEN':TOKEN, 'COG_QWEN_BACKEND_TOKEN':TOKEN})
        env.start(); self.addCleanup(env.stop)

    def admission(self):
        candidate = bind(self.request, self.api)
        return admit(self.request, candidate, self.api, self.store, self.request['configuration']['gateway_base_url'])

    def test_candidate_does_not_admit(self):
        result = bind(self.request, self.api)
        self.assertEqual(result['payload']['binding']['state'], 'candidate')
        self.assertIsNone(result['payload']['binding']['admission'])
        self.assertFalse(list(self.store.root.glob('*.json')))
        self.assertEqual(result['payload']['binding']['locality'], 'local')

    def test_host_reprobes_and_records_local_binding(self):
        binding = self.admission()
        self.assertEqual(self.api.calls, 2)
        self.assertEqual(binding['state'], 'admitted')
        self.assertFalse(binding['qualification']['identity_verified'])
        self.assertFalse(binding['qualification']['revision_pinned'])
        result = infer(self.store, self.api, binding['binding_id'], 1,
                       {'messages':[{'role':'user','content':'JSON please'}], 'response_format':{'type':'json_object'}},
                       self.request['configuration']['gateway_base_url'])
        self.assertEqual(result['cog_binding']['outcome'], 'completed')
        self.assertEqual(result['cog_binding']['observed_provider'], 'local/llama.cpp')

    def test_wrong_model_and_cloud_only_requirements_fail(self):
        for key, value in [('model_id','other'), ('gateway_base_url','http://example.com:8080')]:
            req = copy.deepcopy(self.request); req['configuration'][key] = value
            self.assertEqual(bind(req,self.api)['payload']['status'], 'failed')
        self.request['requirement']['allowed_localities']=['cloud']
        self.assertEqual(bind(self.request,self.api)['payload']['status'],'failed')

    def test_missing_token_is_explicit_and_not_echoed(self):
        with patch.dict(os.environ, {'COG_QWEN_BACKEND_TOKEN':'short-secret'}):
            result=bind(self.request,self.api)
        self.assertEqual(result['payload']['status'],'failed')
        self.assertNotIn('short-secret',json.dumps(result))

    def test_host_rejects_forged_candidate(self):
        candidate=bind(self.request,self.api)
        candidate['payload']['binding']['locality']='cloud'
        with self.assertRaises(Fault): admit(self.request,candidate,self.api,self.store,self.request['configuration']['gateway_base_url'])

    def test_no_endpoint_model_or_tool_override(self):
        binding=self.admission()
        for extra in [{'model':'other'}, {'tools':[]}, {'provider':{}}, {'max_tokens':999999}]:
            with self.assertRaises(Fault):
                infer(self.store,self.api,binding['binding_id'],1,dict(messages=[{'role':'user','content':'x'}],**extra),self.request['configuration']['gateway_base_url'])

    def test_revocation_and_corrupt_state_fail(self):
        binding=self.admission()
        self.store.revoke(binding['binding_id'],1)
        with self.assertRaises(Fault): self.store.load(binding['binding_id'],1)

    def test_changed_model_and_invalid_json_fail(self):
        binding=self.admission()
        self.api.content='not json'
        with self.assertRaises(Fault): infer(self.store,self.api,binding['binding_id'],1,{'messages':[{'role':'user','content':'x'}],'response_format':{'type':'json_object'}},self.request['configuration']['gateway_base_url'])
        self.api.model='different-model'
        with self.assertRaises(Fault): infer(self.store,self.api,binding['binding_id'],1,{'messages':[{'role':'user','content':'x'}]},self.request['configuration']['gateway_base_url'])

    def test_binding_schema(self):
        validate(DECLARATION,'provider')
        validate_request(self.request)

    def test_redirects_are_refused(self):
        with self.assertRaises(Fault): NoRedirect().redirect_request(None,None,302,'redirect',{},'https://example.com')

    def test_gateway_auth_host_origin_and_media_type(self):
        server=make_server(self.store,self.api,0)
        self.addCleanup(server.server_close)
        self.request['configuration']['gateway_base_url']=f'http://127.0.0.1:{server.server_port}'
        binding=self.admission()
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        self.addCleanup(server.shutdown)
        url=binding['invocation']['address']+'/chat/completions'
        body=json.dumps({'messages':[{'role':'user','content':'x'}]}).encode()
        for extras, status in [({'Authorization':'Bearer wrong'},401),({'Origin':'http://evil.invalid'},403),({'Host':'evil.invalid'},403),({'Content-Type':'text/plain'},415)]:
            headers={'Authorization':'Bearer '+TOKEN,'Content-Type':'application/json',**extras}
            with self.assertRaises(urllib.error.HTTPError) as caught: urllib.request.urlopen(urllib.request.Request(url,data=body,headers=headers),timeout=5)
            self.assertEqual(caught.exception.code,status)
            caught.exception.close()
        with urllib.request.urlopen(urllib.request.Request(url,data=body,headers={'Authorization':'Bearer '+TOKEN,'Content-Type':'application/json'}),timeout=5) as response:
            self.assertEqual(json.load(response)['model'],MODEL_ID)


class ArtifactTests(unittest.TestCase):
    def test_checksum_and_symlink_refusal(self):
        spec=importlib.util.spec_from_file_location('qwen_artifact',ROOT/'scripts/model.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'model.gguf';p.write_bytes(b'fixture-model')
            pin=dict(module.MODEL,size=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
            with patch.object(module,'MODEL',pin):
                self.assertEqual(module.verify(p),pin['sha256'])
                link=Path(tmp)/'link';link.symlink_to(p)
                with self.assertRaises(ValueError):module.verify(link)
                p.write_bytes(b'changed-model')
                with self.assertRaises(ValueError):module.verify(p)


if __name__ == '__main__': unittest.main()
