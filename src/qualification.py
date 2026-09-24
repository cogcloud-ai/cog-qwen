"""Local serving checks; a reported alias is not independent weights attestation."""
import json
from contracts import require
from local_http import MODEL_ID

FEATURES = {'text-generation', 'json-output', 'json-schema'}


def inspect_catalog(catalog, config, required):
    require(catalog == {'model_id': MODEL_ID} and config['model_id'] == MODEL_ID,
            'qualification-failed', 'Local server must advertise the pinned model alias.')
    require(set(required) <= FEATURES, 'incompatible-requirement', 'Unsupported local inference feature.')
    return list(required), [MODEL_ID]


def routed(config, body):
    return dict(body, model=config['model_id'])


def observe(response, config, endpoints, api, key, trace=None):
    require(isinstance(response, dict) and response.get('model') == config['model_id'],
            'qualification-failed', 'Local response model differs from the admitted model.', 502)
    return {'observed_model': response['model'], 'observed_provider': 'local/llama.cpp'}


def probe(api, config, endpoints, required, key):
    body = routed(config, {'messages': [{'role': 'user', 'content': 'Return only the JSON object {"ok":true}.'}],
                          'max_tokens': 64, 'temperature': 0})
    if 'json-schema' in required:
        body['response_format'] = {'type': 'json_schema', 'json_schema': {'name': 'probe', 'strict': True,
            'schema': {'type': 'object', 'properties': {'ok': {'const': True}}, 'required': ['ok'], 'additionalProperties': False}}}
    elif 'json-output' in required:
        body['response_format'] = {'type': 'json_object'}
    result = api.completion(body, key)
    observe(result, config, endpoints, api, key)
    try:
        message = result['choices'][0]['message']
        text = message['content']
        require(isinstance(text, str) and bool(text.strip()) and not message.get('tool_calls'),
                'qualification-failed', 'Probe returned no plain text.')
        if body.get('response_format'):
            require(json.loads(text) == {'ok': True}, 'qualification-failed', 'Local JSON probe failed.')
    except (KeyError, IndexError, TypeError, ValueError):
        require(False, 'qualification-failed', 'Local probe returned malformed content.')
    return [{'check': 'local-functional-probe', 'observation': 'Exact alias and requested text/JSON behavior observed; weights identity is not independently attested.'}]
