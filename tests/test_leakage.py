"""Data-leakage check: no example/test input may equal a paper title or abstract in the knowledge state."""
import glob, json, os
import pytest
from peft_kb.normalize import title_key

STATE = "knowledge/knowledge_state.json"
PAPERS = "data/processed/papers.json"

@pytest.mark.skipif(not os.path.exists(PAPERS), reason="run scripts/collect_data.py first")
def test_examples_not_in_dataset():
    papers = json.load(open(PAPERS, encoding="utf-8"))
    keys = {title_key(p["title"]) for p in papers} | {title_key(p["abstract"]) for p in papers if p["abstract"]}
    for f in glob.glob("examples/input/*.txt"):
        assert title_key(open(f, encoding="utf-8").read()) not in keys, f
