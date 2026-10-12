"""Strict, bounded JSON at untrusted process/provider boundaries."""
import json


def load_json(raw, *, max_bytes=65536):
    if not isinstance(raw, (str, bytes)) or len(raw) > max_bytes:
        raise ValueError('JSON payload exceeds protocol limit')
    if isinstance(raw, str) and len(raw.encode('utf-8')) > max_bytes:
        raise ValueError('JSON payload exceeds protocol limit')

    def constant(_):
        raise ValueError('nonfinite JSON number')

    def object_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate JSON field')
            result[key] = value
        return result

    try:
        value = json.loads(raw, parse_constant=constant, object_pairs_hook=object_pairs)
        # Reject overflow to infinity (1e999), lone surrogates and deep output.
        json.dumps(value, allow_nan=False, ensure_ascii=False).encode('utf-8')
        return value
    except (RecursionError, UnicodeError, TypeError) as exc:
        raise ValueError('invalid JSON payload') from exc
