"""Small Google client: private credentials in headers only, immutable local receipts."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
import urllib.error
import urllib.request
from .artifacts import publish, durable_directory

ENDPOINT = 'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions'
MODELS = ('gemini-3.5-flash', 'gemma-4-31b-it')
PROVIDERS = {'google': (ENDPOINT,'.apigoogleaistudio'),
             'groq': ('https://api.groq.com/openai/v1/chat/completions','.apigroq')}
SAFE_HEADERS = {'retry-after', 'x-ratelimit-limit-requests', 'x-ratelimit-remaining-requests',
                'x-ratelimit-limit-tokens', 'x-ratelimit-remaining-tokens', 'x-ratelimit-reset-requests',
                'x-ratelimit-reset-tokens'}


def http(request, timeout):
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, dict(response.headers), json.loads(response.read(1000000))
    except urllib.error.HTTPError as exc:
        try:
            body = json.loads(exc.read(1000000))
        except ValueError:
            body = {}
        return exc.code, dict(exc.headers), body


def provider_errors(response):
    rows = response if type(response) is list else [response]
    errors = []
    for row in rows:
        error = row.get('error') if type(row) is dict else None
        if type(error) is not dict:
            continue
        safe = {k:error.get(k) for k in ('status','type','code')}
        safe.update(violations=[], retry_delay=None)
        details = error.get('details',[])
        for detail in details if type(details) is list else []:
            if type(detail) is not dict:
                continue
            for v in detail.get('violations',[]):
                if type(v) is dict:
                    safe['violations'].append({k:v[k] for k in ('quotaMetric','quotaId','quotaValue') if k in v})
            if 'retryDelay' in detail:
                safe['retry_delay'] = detail['retryDelay']
        errors.append(safe)
    return errors


def complete(model, prompt, cache, *, max_tokens=3000, key_path=None, transport=http,
             provider='google', reasoning_effort=None, before_call=None):
    endpoint, key_filename = PROVIDERS[provider]
    body = {'model': model, 'messages': [{'role': 'user', 'content': prompt}],
            'temperature': 0, 'max_completion_tokens' if provider == 'groq' else 'max_tokens': max_tokens}
    if reasoning_effort is not None:
        body['reasoning_effort'] = reasoning_effort
    identity = json.dumps({'endpoint': endpoint, 'body': body}, sort_keys=True, separators=(',', ':'))
    sha = hashlib.sha256(identity.encode()).hexdigest()
    cache = Path(cache)
    path = cache / (sha + '.json')
    if path.exists():
        result = json.loads(path.read_text())
        if result['request_sha256'] != sha or result['prompt'] != prompt or result['model_requested'] != model:
            raise ValueError('cache identity mismatch')
        return {**result, 'cached': True}
    credential = (Path(key_path) if key_path else Path.home() / key_filename).read_text().strip()
    if not credential:
        raise ValueError('empty credential file')
    request = urllib.request.Request(endpoint, data=json.dumps(body).encode(),
                                     headers={'Authorization': 'Bearer ' + credential, 'Content-Type': 'application/json',
                                              'User-Agent':'echoai-crece/1.0'})
    start = time.monotonic_ns()
    error = None
    if before_call is not None:
        before_call()
    try:
        status, headers, response = transport(request, 90)
    except Exception as exc:
        status, headers, response, error = 0, {}, {}, type(exc).__name__
    service_errors = provider_errors(response)
    if status >= 400:
        response = {}
    choice, content = {}, ''
    try:
        if type(response) is not dict:
            raise TypeError()
        choices = response.get('choices') or []
        if type(choices) is not list:
            raise TypeError()
        if choices:
            choice = choices[0]
            if type(choice) is not dict or type(choice.get('message')) is not dict:
                raise TypeError()
            content = choice['message'].get('content') or ''
            if type(content) is not str:
                raise TypeError()
    except (TypeError, KeyError):
        error, response, choice, content = 'MalformedResponse', {}, {}, ''
    result = {'request_sha256': sha, 'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest(),
              'prompt': prompt, 'model_requested': model, 'model_returned': response.get('model'),
              'temperature': 0, 'max_tokens': max_tokens, 'status': status, 'content': content,
              'finish_reason': choice.get('finish_reason'), 'usage': response.get('usage', {}),
              'rate_headers': {k.lower(): v for k, v in headers.items() if k.lower() in SAFE_HEADERS},
              'elapsed_ms': (time.monotonic_ns() - start) // 1000000,
              'utc': datetime.now(timezone.utc).isoformat(), 'error_type': error, 'cached': False}
    result.update(provider=provider, reasoning_effort=reasoning_effort, provider_errors=service_errors)
    encoded = json.dumps(result, indent=2, sort_keys=True).replace(credential, '[REDACTED]')
    del credential
    durable_directory(cache)
    if status != 200 or not content:
        path = cache / (sha + '-failed-' + str(time.time_ns()) + '.json')
    publish(path, (encoded + '\n').encode())
    return json.loads(encoded)


def quota_probe(output):
    output = Path(output)
    if output.exists():
        raise ValueError('quota report already exists')
    rows = []
    for model in MODELS:
        for index in range(2):
            row = complete(model, f'Responde únicamente con el entero {index + 1}. Prueba pequeña de disponibilidad CRECE F1.',
                           output.parent / 'api-cache', max_tokens=64)
            public = {k: row[k] for k in ('model_requested', 'model_returned', 'status', 'elapsed_ms', 'usage',
                                         'rate_headers', 'cached', 'request_sha256', 'finish_reason')}
            public['nonempty'] = bool(row['content'])
            rows.append(public)
            print(json.dumps(public), flush=True)
            if row['status'] != 200:
                break
    report = {'requests': rows, 'daily_quota': None, 'billing_tier_verified': False,
              'interpretation': 'Observed small-call availability only; no inferred daily quota or free billing certification.'}
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--quota-output', type=Path, required=True)
    quota_probe(parser.parse_args().quota_output)
