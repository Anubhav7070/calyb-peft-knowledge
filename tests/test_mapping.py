import pytest
from peft_kb.mapping import build_state, map_paper, Builder
from peft_kb import knowledge as K
from conftest import MODEL, PAPERS

def types(state): return {r["type"] for r in state["relationships"]}

def test_entities_created(state):
    ids = {e["id"] for e in state["entities"]}
    assert {"paper:p1", "method:alpha", "concept:lowrank", "task:summ"} <= ids

def test_relationships_created(state):
    assert types(state) == {"PROPOSES", "USES", "EXTENDS", "EVALUATED_ON"}

def test_proposes_by_title(state):
    assert any(r["type"] == "PROPOSES" and r["source"] == "paper:p1" and r["target"] == "method:alpha" for r in state["relationships"])

def test_evaluated_on_has_evidence_and_paper(state):
    r = next(r for r in state["relationships"] if r["type"] == "EVALUATED_ON")
    assert r["source_paper"] == "paper:p1" and "AlphaTune" in r["evidence"]["text"]

def test_missing_abstract_creates_no_evaluated_on():
    papers = [dict(PAPERS[0], abstract=None)]
    assert "EVALUATED_ON" not in types(build_state(papers, MODEL))

def test_missing_origin_paper_creates_no_proposes():
    assert "PROPOSES" not in types(build_state([], MODEL))

def test_duplicate_entity_rejected():
    b = Builder(); b.add_entity(map_paper(PAPERS[0]))
    with pytest.raises(K.KnowledgeError): b.add_entity(map_paper(PAPERS[0]))

def test_invalid_mapping_bad_endpoint_type():
    model = dict(MODEL, extends=[{"source": "beta", "target": "ghost", "note": "x"}])
    with pytest.raises(K.KnowledgeError): build_state(PAPERS, model)


def test_extends_has_source_paper_when_origin_in_dataset(state):
    r = next(r for r in state["relationships"] if r["type"] == "EXTENDS")
    assert r["source_paper"] == "paper:p2" and r["evidence"]["source_paper_title"].startswith("BetaTune")
