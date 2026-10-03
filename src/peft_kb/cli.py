from __future__ import annotations
import argparse
import json
import logging
import sys

from . import knowledge as K
from .reasoning import InputError, reason


def run(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Reason over the PEFT knowledge state for a NEW idea.")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--text")
    g.add_argument("--file")
    ap.add_argument("--state", default="knowledge/knowledge_state.json")
    ap.add_argument("--top-k", type=int, default=5)
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.WARNING)
    try:
        text = a.text if a.text is not None else open(a.file, encoding="utf-8").read()
        result = reason(text, K.load(a.state), a.top_k)
    except (InputError, K.KnowledgeError, OSError) as e:
        print(json.dumps({"status": "error", "error": str(e)}, indent=2))
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(run())
