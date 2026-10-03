import json, copy, pytest
from peft_kb import knowledge as K

def test_save_load_roundtrip(state, tmp_path):
    p = tmp_path / "ks.json"; K.save(state, str(p))
    assert K.load(str(p)).stats() == K.KnowledgeState(state).stats()

def test_entity_lookup_and_unknown(ks):
    assert ks.entity("method:alpha")["name"] == "AlphaTune"
    with pytest.raises(K.KnowledgeError): ks.entity("method:nope")

def test_traversal(ks):
    assert [e["target"] for e in ks.out_edges("method:beta", "EXTENDS")] == ["method:alpha"]
    assert [e["source"] for e in ks.in_edges("method:alpha", "EXTENDS")] == ["method:beta"]

def test_orphan_relationship_rejected(state):
    bad = copy.deepcopy(state); bad["relationships"][0]["target"] = "x:missing"
    with pytest.raises(K.KnowledgeError, match="orphan"): K.validate(bad)

def test_missing_provenance_rejected(state):
    bad = copy.deepcopy(state); bad["relationships"][0]["evidence"] = None
    with pytest.raises(K.KnowledgeError, match="provenance"): K.validate(bad)

def test_duplicate_id_and_bad_types(state):
    bad = copy.deepcopy(state); bad["entities"].append(dict(bad["entities"][0]))
    with pytest.raises(K.KnowledgeError, match="duplicate"): K.validate(bad)
    bad = copy.deepcopy(state); bad["relationships"][0]["type"] = "LIKES"
    with pytest.raises(K.KnowledgeError, match="unknown type"): K.validate(bad)

def test_missing_and_corrupted_file(tmp_path):
    with pytest.raises(K.KnowledgeError, match="not found"): K.load(str(tmp_path / "none.json"))
    p = tmp_path / "bad.json"; p.write_text("{not json")
    with pytest.raises(K.KnowledgeError, match="corrupted"): K.load(str(p))
    p.write_text('{"a": 1}')
    with pytest.raises(K.KnowledgeError, match="corrupted"): K.load(str(p))
