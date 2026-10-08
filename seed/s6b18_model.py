"""B18 CUDA transport, reusing the frozen bounded GGUF receipt machinery."""
import os
from pathlib import Path
from types import FunctionType
from seed import s6b13_model as old


def configured(model, cli, tokenizer):
    model, cli, tokenizer = map(Path, (model, cli, tokenizer))
    if old.digest_file(model) != old.MODEL_SHA:
        raise RuntimeError('B18 must retain the B17 model weights')
    def command(prompt, grammar, seed):
        return [str(cli), '-m', str(model), '-ngl', '99', '--split-mode', 'none', '--main-gpu', '0',
            '-t', '4', '-tb', '4', '-c', str(old.CONTEXT), '-b', '128', '-ub', '64',
            '-n', str(old.MAX_OUTPUT), '--seed', str(seed), '--temp', '0.6', '--top-k', '40',
            '--top-p', '0.95', '--no-conversation', '--no-display-prompt', '--simple-io',
            '--no-context-shift', '--no-escape', '--grammar-file', str(grammar), '-f', str(prompt)]
    scope = dict(vars(old), MODEL=model, CLI=cli, TOKENIZER=tokenizer, command=command, TIMEOUT=300)
    for name in ('tokenize','load','propose'):
        f = getattr(old,name)
        scope[name] = FunctionType(f.__code__,scope,name,f.__defaults__)
        scope[name].__kwdefaults__ = f.__kwdefaults__
    return scope


def environment_model():
    return configured(os.environ['ECHO_B18_MODEL'],os.environ['ECHO_B18_CLI'],os.environ['ECHO_B18_TOKENIZER'])
