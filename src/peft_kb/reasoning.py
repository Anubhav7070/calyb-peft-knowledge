"""Reasoning over the knowledge state. Deterministic; no LLM involved.

Steps: validate input -> map to concepts/methods/tasks (alias match) -> score candidate methods by
graph traversal (named, shared concept via USES, one EXTENDS hop) -> collect evidence ->
derive gaps (candidate x task with no EVALUATED_ON edge) -> structured result with trace.
"""
from __future__ import annotations
from .knowledge import KnowledgeState
from .normalize import clean_text
from .textmatch import find_alias

MAX_INPUT_CHARS = 4000
PTS_NAMED, PTS_CONCEPT, PTS_EXTENDS = 3, 2, 1


class InputError(ValueError):
    pass


def match_entities(text: str, ks: KnowledgeState) -> list[dict]:
    hits = []
    for etype in ("Method", "Concept", "Task"):
        for e in ks.of_type(etype):
            h = find_alias(text, e["attributes"]["aliases"])
            if h:
                hits.append({"entity_id": e["id"], "type": etype, "name": e["name"], "matched_alias": h[0]})
    return hits


def reason(text: str, ks: KnowledgeState, top_k: int = 5) -> dict:
    if not isinstance(text, str) or not text.strip():
        raise InputError("input is empty")
    if len(text) > MAX_INPUT_CHARS:
        raise InputError(f"input too long ({len(text)} > {MAX_INPUT_CHARS} chars)")
    norm = clean_text(text)
    trace = []
    hits = match_entities(norm, ks)
    trace.append(f"Matched {len(hits)} entities in input by explicit alias rules.")
    methods = [h for h in hits if h["type"] == "Method"]
    concepts = [h for h in hits if h["type"] == "Concept"]
    tasks = [h for h in hits if h["type"] == "Task"]

    scores: dict[str, int] = {}
    why: dict[str, list[str]] = {}

    def add(mid, pts, reason):
        scores[mid] = scores.get(mid, 0) + pts
        why.setdefault(mid, []).append(f"+{pts} {reason}")

    for h in methods:
        add(h["entity_id"], PTS_NAMED, "named in input")
    for h in concepts:
        for edge in ks.in_edges(h["entity_id"], "USES"):
            add(edge["source"], PTS_CONCEPT, f"USES concept '{h['name']}' found in input")
    direct = list(scores)
    for mid in direct:
        for e in ks.out_edges(mid, "EXTENDS"):
            add(e["target"], PTS_EXTENDS, f"is extended by / base of {ks.entity(mid)['name']} (EXTENDS)")
        for e in ks.in_edges(mid, "EXTENDS"):
            add(e["source"], PTS_EXTENDS, f"extends {ks.entity(mid)['name']} (EXTENDS)")
    trace.append(f"Scored {len(scores)} candidate methods via named/USES/EXTENDS traversal.")

    if not scores:
        return {"status": "no_relevant_knowledge", "input": norm, "matched_entities": hits,
                "candidates": [], "gaps": [], "notes": ["No method or concept in the input matches this knowledge state."],
                "reasoning_trace": trace}

    ranked = sorted(scores, key=lambda m: (-scores[m], ks.entity(m)["name"]))[:top_k]
    notes = []
    if len(ranked) > 1 and scores[ranked[0]] == scores[ranked[1]]:
        notes.append("Top candidates are tied on score; the ranking among them is not meaningful.")
    cands = []
    for mid in ranked:
        cands.append({
            "method": ks.entity(mid)["name"], "id": mid, "score": scores[mid], "why": why[mid],
            "proposed_by": [{"paper_id": e["source"], "title": ks.entity(e["source"])["name"]}
                            for e in ks.in_edges(mid, "PROPOSES")],
            "evaluated_on": [{"task": ks.entity(e["target"])["name"], "source_paper": e["source_paper"],
                              "evidence": e["evidence"]["text"]} for e in ks.out_edges(mid, "EVALUATED_ON")],
            "uses": [ks.entity(e["target"])["name"] for e in ks.out_edges(mid, "USES")],
        })
    task_ids = [t["entity_id"] for t in tasks] or sorted(
        {r["target"] for r in ks.data["relationships"] if r["type"] == "EVALUATED_ON"})
    gaps = []
    for c in cands:
        covered = {e["target"] for e in ks.out_edges(c["id"], "EVALUATED_ON")}
        for tid in task_ids:
            if tid not in covered:
                gaps.append({"method": c["method"], "task": ks.entity(tid)["name"],
                             "note": "No EVALUATED_ON edge in this knowledge state (absence in a small subset is not proof it is untested)."})
    trace.append(f"Checked {len(cands)} candidates x {len(task_ids)} tasks for missing EVALUATED_ON edges.")
    return {"status": "ok", "input": norm, "matched_entities": hits, "candidates": cands, "gaps": gaps,
            "notes": notes + ["Scores are heuristic ranking weights, not probabilities."],
            "suggested_actions": {"baselines_to_compare": [c["method"] for c in cands[:3]],
                                  "read_first": [p["title"] for c in cands[:3] for p in c["proposed_by"]]},
            "reasoning_trace": trace}
