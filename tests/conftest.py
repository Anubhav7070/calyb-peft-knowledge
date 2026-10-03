import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import pytest
from peft_kb.mapping import build_state
from peft_kb import knowledge as K

# SYNTHETIC FIXTURES for unit tests only. These are not real papers and are never used as data.
MODEL = {
    "concepts": [{"id": "lowrank", "name": "Low-rank", "aliases": ["low-rank"]},
                 {"id": "quant", "name": "Quantization", "aliases": ["quantized"]}],
    "tasks": [{"id": "summ", "name": "Summarization", "aliases": ["summarization"]},
              {"id": "qa", "name": "QA", "aliases": ["question answering"]}],
    "methods": [{"id": "alpha", "name": "AlphaTune", "aliases": ["AlphaTune"], "origin_title": "AlphaTune: A Synthetic Method", "uses": ["lowrank"]},
                {"id": "beta", "name": "BetaTune", "aliases": ["BetaTune"], "origin_title": "BetaTune: Another Synthetic Method", "uses": ["lowrank", "quant"]}],
    "extends": [{"source": "beta", "target": "alpha", "note": "synthetic"}],
}
PAPERS = [
    {"id": "paper:p1", "title": "AlphaTune: A Synthetic Method", "abstract": "We test AlphaTune on summarization.", "year": 2021, "authors": ["A B"], "doi": None, "arxiv_id": None, "url": None, "citation_count": 5, "s2_id": "p1"},
    {"id": "paper:p2", "title": "BetaTune: Another Synthetic Method", "abstract": "BetaTune improves AlphaTune.", "year": 2022, "authors": [], "doi": None, "arxiv_id": None, "url": None, "citation_count": 3, "s2_id": "p2"},
]

@pytest.fixture
def state():
    return build_state(PAPERS, MODEL)

@pytest.fixture
def ks(state):
    return K.KnowledgeState(state)
