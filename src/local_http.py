"""Fixed loopback llama.cpp transport. No endpoint overrides or redirects."""
import json
import urllib.request
from contracts import Fault, credential, require

MODEL_ID = 'qwen3-4b-q4_k_m'
BASE = 'http://127.0.0.1:8080'
MAX_BYTES = 8 * 1024 * 1024


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise Fault('provider-unavailable', 'Local model redirects are refused.', 502)


class LocalHTTP:
    def request(self, path, key, body=None):
        data = None if body is None else json.dumps(body, allow_nan=False).encode()
        req = urllib.request.Request(BASE + path, data=data, headers={
            'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
        try:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
            with opener.open(req, timeout=180) as response:
                raw = response.read(MAX_BYTES + 1)
            require(len(raw) <= MAX_BYTES, 'provider-unavailable', 'Local response exceeds size limit.', 502)
            return json.loads(raw)
        except (OSError, ValueError):
            raise Fault('provider-unavailable', 'Local model unavailable or returned invalid JSON; start serve-model with its dedicated token.', 503) from None

    def key_health(self, key):
        return self.request('/v1/models', key)

    def catalog(self, model_id):
        require(model_id == MODEL_ID, 'unsupported-model', 'This package serves only its pinned Qwen model.')
        data = self.key_health(credential('env:COG_QWEN_BACKEND_TOKEN'))
        require(isinstance(data, dict) and isinstance(data.get('data'), list) and
                any(isinstance(x, dict) and x.get('id') == MODEL_ID for x in data['data']),
                'qualification-failed', 'The serving model alias does not match this package.')
        return {'model_id': MODEL_ID}

    def completion(self, body, key):
        require(body.get('model') == MODEL_ID, 'unsupported-model', 'No model override is supported.')
        sent = dict(body, chat_template_kwargs={'enable_thinking': False})
        if 'max_completion_tokens' in sent:
            sent['max_tokens'] = sent.pop('max_completion_tokens')
        return self.request('/v1/chat/completions', key, sent)
