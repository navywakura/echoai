"""Index of the sealed receipts shipped with the release (open evidence)."""
import json
from importlib import resources


def index():
    return json.loads(resources.files(__package__).joinpath("evidence_index.json").read_text())
