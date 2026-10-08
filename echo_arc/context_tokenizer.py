"""Offline token counting only, in the separate S6 tokenizer environment."""
import hashlib
import json
from pathlib import Path
import sys


def main():
    from transformers import AutoTokenizer
    root = Path(__file__).resolve().parents[1] / 'lab/tools/s6-qwen-tokenizer'
    tokenizer = AutoTokenizer.from_pretrained(str(root), local_files_only=True, trust_remote_code=False)
    results = []
    for prompt in json.load(sys.stdin):
        rendered = tokenizer.apply_chat_template([{'role': 'user', 'content': prompt}],
                                                 tokenize=False, add_generation_prompt=True)
        ids = tokenizer.encode(rendered)
        results.append({'tokens': len(ids), 'token_ids_sha256': hashlib.sha256(
            json.dumps(ids, separators=(',', ':')).encode()).hexdigest()})
    print(json.dumps(results))


if __name__ == '__main__':
    main()
