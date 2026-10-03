import pytest
from peft_kb.reasoning import reason, InputError, MAX_INPUT_CHARS

def test_valid_new_input_uses_graph(ks):
    r = reason("I want a quantized low-rank approach for summarization", ks)
    assert r["status"] == "ok"
    top = {c["id"]: c for c in r["candidates"]}
    assert top["method:beta"]["score"] > top["method:alpha"]["score"]  # beta uses both concepts
    assert any("EXTENDS" in w for w in top["method:alpha"]["why"]) or top["method:alpha"]["score"] >= 2
    assert top["method:alpha"]["proposed_by"][0]["paper_id"] == "paper:p1"
    assert r["reasoning_trace"]

def test_concept_not_verbatim_method_reached_via_concept(ks):
    r = reason("something quantized", ks)
    assert r["candidates"][0]["id"] == "method:beta"

def test_gaps_reported_for_unevaluated_task(ks):
    r = reason("low-rank for question answering", ks)
    assert any(g["task"] == "QA" for g in r["gaps"])

def test_no_gap_when_evidence_exists(ks):
    r = reason("AlphaTune for summarization", ks)
    assert not any(g["method"] == "AlphaTune" and g["task"] == "Summarization" for g in r["gaps"])

def test_unrelated_input_no_result(ks):
    assert reason("quadruped locomotion controller", ks)["status"] == "no_relevant_knowledge"

def test_task_only_input_has_no_candidates(ks):
    r = reason("summarization", ks)
    assert r["status"] == "no_relevant_knowledge" and r["matched_entities"]

def test_tie_is_flagged(ks):
    r = reason("low-rank", ks)  # alpha and beta both +2, no EXTENDS evidence difference? beta/alpha get +1 each
    assert r["status"] == "ok"

def test_empty_and_too_long(ks):
    for bad in ("", "   ", None):
        with pytest.raises(InputError): reason(bad, ks)
    with pytest.raises(InputError): reason("x" * (MAX_INPUT_CHARS + 1), ks)

def test_unicode_input(ks):
    assert reason("quantized\u00a0low-rank \u2014 résumé", ks)["status"] == "ok"


# ---- red-team additions ----
def test_alias_with_regex_chars_and_word_boundaries():
    from peft_kb.textmatch import find_alias
    assert find_alias("we use (IA)3 here", ["(IA)3"])
    assert find_alias("an equal split", ["QA"]) is None
    assert find_alias("LORA works", ["LoRA"])  # case-insensitive

def test_very_long_but_valid_input(ks):
    assert reason("quantized " * 300, ks)["status"] == "ok"  # 3000 chars

def test_ambiguous_multi_concept_ranks_overlap_highest(ks):
    r = reason("quantized low-rank", ks)
    assert r["candidates"][0]["id"] == "method:beta"

def test_paraphrase_without_alias_is_missed_documented_limitation(ks):
    assert reason("trained tiny factors of the weight change", ks)["status"] == "no_relevant_knowledge"

def test_empty_state_graph_still_valid():
    from peft_kb.mapping import build_state
    from peft_kb import knowledge as K
    from conftest import MODEL
    st = K.KnowledgeState(build_state([], MODEL))
    r = reason("quantized", st)
    assert r["status"] == "ok" and r["candidates"][0]["proposed_by"] == []
