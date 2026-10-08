"""S6-B1: format repair in a separate, source-pinned controller instance."""
import importlib.util
import os
from pathlib import Path
import sys

# Reuse the identical implementation without changing B0 or another experiment's globals.
_spec = importlib.util.spec_from_file_location('seed._s6b1_core',
                                             Path(__file__).with_name('game_selfimprove.py'))
core = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = core
_spec.loader.exec_module(core)
core.PROTECTED += ('seed/game_selfimprove_b1.py', 'docs/ECHO45-S6-B1-DESIGN.md')
_requests = core.requests
_worker_init = core.worker_init
_play_one = core.play_one


def worker_init():
    _worker_init()


def play_one(item):
    return _play_one(item)


def requests(arm, round_id, policy, stats, result, accepted):
    batch = _requests(arm, round_id, policy, stats, result, accepted)
    prefix = (
        'Improve ECHO v5.7 control. Output one COMPLETE, COMPACT valid JSON object, no markdown or prose. '
        'Exactly two keys: "defaults" and "rules". Use at most 3 parameters in defaults, and at most ONE rule '
        'with at most 3 parameters in set and exactly ONE condition in when. Empty sections are allowed. '
        'Use the literal parameter/feature names below. All values are integers, never bounds arrays. '
        'Operators must be QUOTED strings: "eq", "ge", "le". No gt/lt. '
        'A VALID example (choose your own strategy): '
        '{"defaults":{"MIN_EVIDENCE":4},"rules":[{"when":{"reset_known":["eq",1]},"set":{"HOLD":60}}]}. '
        'Another VALID example: {"defaults":{"BABBLE":3,"WALL_MIN":4},"rules":[]}. '
        'Allowed parameters and inclusive bounds: ' + core.canonical(core.strategy.LIMITS) + '. '
        'Allowed observable features and bounds: ' + core.canonical(core.strategy.FEATURES) + '. '
        'HOLD=40 waits between resets; MIN_EVIDENCE=8 identifies the body; WALL_MIN=3 needs wall evidence; '
        'MARGIN=2 gives planning room; BABBLE=2 tries movement keys; TEST_WINDOW=4 waits for remote effects; '
        'WINDOW=16 tracks changes; MAX_PER_TARGET=60 limits retries; MIN_CLICK_EVIDENCE=2 learns clicks; '
        'MAX_UNITS=16 bounds click planning; EXPLORE=1 explores frontiers. '
        'Rules run before every action. Omitted parameters retain v5.7 values. Budget 600 actions. ')
    intentions = {'P1': 'Repair the decisions for the almost-completed game.',
                  'P2': 'Repair a shared failure across the failed games.',
                  'P3': 'Generalize the previously verified improvement.',
                  'P4': 'Choose a useful control strategy from the diary.'}
    for req in batch:
        evidence = req['prompt'].split('\nCurrent strategy: ', 1)[1]
        intent = 'Here are three failures. Propose a better general strategy.' if arm == 'fijo' else intentions[req['type']]
        req['prompt'] = prefix + intent + '\nCurrent strategy: ' + evidence
    return batch


def baseline(root, workers):
    root = Path(root)
    profile = {'sources': core.hashes(), 'calls': core.CALLS, 'round_size': core.ROUND_SIZE,
               'A': core.A, 'B': core.B, 'schema': 'echo45-s6-b1', 'calibration_calls': 2}
    if (root / 'profile.json').exists():
        assert core.json.loads((root / 'profile.json').read_text()) == core.json.loads(core.canonical(profile))
    else:
        core.atomic(root / 'profile.json', profile)
    for name, specs in [('A', core.A), ('B', core.B)]:
        res = core.measure(root, core.strategy.EMPTY, specs, workers)
        core.atomic(root / ('baseline-' + name + '.json'), res)
        print(core.canonical({'baseline': name, 'levels': res['levels'], 'score': res['score']}), flush=True)


def hf_proposer(model_id):
    import torch
    import transformers
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(model_id)
    tok.padding_side = 'left'
    model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=torch.float16, device_map='auto')
    model.eval()
    def call(prompts, seed):
        torch.manual_seed(seed)
        answers, usages = [], []
        texts = [tok.apply_chat_template([{'role': 'user', 'content': p}], tokenize=False,
                                        add_generation_prompt=True) for p in prompts]
        for start in range(0, len(texts), 2):
            chunk = texts[start:start + 2]
            enc = tok(chunk, padding=True, truncation=False, return_tensors='pt').to(model.device)
            if enc['input_ids'].shape[1] > 6000:
                raise ValueError('refusing prompt truncation')
            with torch.no_grad():
                out = model.generate(**enc, max_new_tokens=600, do_sample=True, temperature=0.7,
                                     top_p=0.95, pad_token_id=tok.pad_token_id or tok.eos_token_id)
            raw = tok.batch_decode(out[:, enc['input_ids'].shape[1]:], skip_special_tokens=True)
            answers.extend(raw)
            usages.extend({'prompt_tokens': len(tok.encode(t)), 'completion_tokens': len(tok.encode(a)),
                           'cost_usd': 0} for t, a in zip(chunk, raw))
        return answers, usages
    if os.environ.get('S6B_MODEL_PROFILE'):
        core.atomic(Path(os.environ['S6B_MODEL_PROFILE']), {
            'model': model_id, 'revision': getattr(model.config, '_commit_hash', None),
            'torch': torch.__version__, 'transformers': transformers.__version__,
            'devices': {k: str(v) for k, v in model.hf_device_map.items()}, 'max_new_tokens': 600})
    return call


core.requests = requests
core.baseline = baseline
core.hf_proposer = hf_proposer
core.worker_init = worker_init
core.play_one = play_one


def __getattr__(name):
    return getattr(core, name)


if __name__ == '__main__':
    core.main()
