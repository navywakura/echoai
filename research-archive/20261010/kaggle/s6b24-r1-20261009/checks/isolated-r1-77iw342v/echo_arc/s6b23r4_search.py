"""R4 changes only the model wire format; R3 evidence selection is preserved."""
import json
from echo_arc import s6b23_search as prior
from echo_arc.feasible_grammar import canonical

KINDS = ('N7', 'N14')
ROUNDS = prior.ROUNDS
validate_proposal = prior.validate_proposal


def config():
    return dict(original=prior.config(), revision='B23-R4', arms=KINDS,
                change='unambiguous JSON contract and constrained decoding; same evidence')


def format_fields():
    return dict(
        output_instructions='Return only the JSON object. Exactly one patch. when is an object '
        'with 1 to 3 distinct allowed feature keys in alphabetical order. Each value is '
        '[operator, integer] from allowed_atoms. set contains only HOLD: ONE integer '
        'from allowed_hold_values. No markdown, commentary, schema, extra keys or value lists.',
        allowed_hold_values=list(prior.old.VALUES),
        format_example={'patches': [{'when': {'body_known': ['eq', 0]}, 'set': {'HOLD': 4}}]},
        example_warning='Syntax example only; no measured utility. Select your own conditions '
        'and duration using the provided observations and your own previous results.')


def model_request(kind, index, seed, policy, base, history):
    req = prior.model_request(kind, index, seed, policy, base, history)
    payload = json.loads(req['prompt'])
    del payload['response_schema']
    payload.update(format_fields())
    return dict(req, prompt=canonical(payload))


def from_bytes(data):
    obj = json.loads(data)
    if set(obj) != {'policy', 'base', 'own_history', 'kind', 'index', 'seed'}:
        raise ValueError('unexpected investigator input surface')
    if obj['kind'] not in KINDS or not 0 <= obj['index'] < ROUNDS:
        raise ValueError('unknown R4 arm or slot')
    return model_request(obj['kind'], obj['index'], obj['seed'], obj['policy'], obj['base'], obj['own_history'])
