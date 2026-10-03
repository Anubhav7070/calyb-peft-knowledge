"""Explicit mapping rules: normalized papers + hand-authored model -> entities and relationships.

Rules (each relationship records which rule created it):
  R1 manual_annotation : Method USES Concept, Method EXTENDS Method (from knowledge_model/model.json)
  R2 title_match       : Paper PROPOSES Method   if normalized paper title == method.origin_title
  R3 abstract_cooccur  : Method EVALUATED_ON Task if a paper's title+abstract mentions a method alias
                         AND a task alias; evidence = snippet around the method mention.
Missing evidence => no relationship is created (never inferred).
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone

from . import knowledge as K
from .normalize import title_key
from .textmatch import find_alias, snippet

log = logging.getLogger(__name__)


def map_paper(p: dict) -> dict:
    return {"id": p["id"], "type": "Paper", "name": p["title"],
            "attributes": {"year": p["year"], "authors": p["authors"], "doi": p["doi"],
                           "arxiv_id": p["arxiv_id"], "url": p["url"], "has_abstract": bool(p["abstract"])}}


def map_model_entity(item: dict, etype: str) -> dict:
    return {"id": f"{etype.lower()}:{item['id']}", "type": etype, "name": item["name"],
            "attributes": {"aliases": item["aliases"]}}


class Builder:
    def __init__(self):
        self.entities, self.relationships = [], []
        self._ids = set()

    def add_entity(self, e):
        if e["id"] in self._ids:
            raise K.KnowledgeError(f"duplicate entity {e['id']}")
        self._ids.add(e["id"])
        self.entities.append(e)

    def create_relationship(self, source, rtype, target, evidence, rule, source_paper=None):
        rid = f"{rtype}:{source}->{target}" + (f"@{source_paper}" if source_paper else "")
        if any(r["id"] == rid for r in self.relationships):
            return
        self.relationships.append({"id": rid, "source": source, "type": rtype, "target": target,
                                   "evidence": evidence, "rule": rule, "source_paper": source_paper})
        log.debug("relationship %s", rid)


def build_state(papers: list[dict], model: dict, manifest_name: str = "") -> dict:
    b = Builder()
    for p in papers:
        b.add_entity(map_paper(p))
    for etype, key in (("Concept", "concepts"), ("Task", "tasks"), ("Method", "methods")):
        for item in model[key]:
            b.add_entity(map_model_entity(item, etype))

    for m in model["methods"]:  # R1 (uses)
        for c in m["uses"]:
            b.create_relationship(f"method:{m['id']}", "USES", f"concept:{c}",
                                  {"type": "annotation", "note": "hand-authored in model.json"}, "manual_annotation")
    by_title = {title_key(p["title"]): p for p in papers}
    origin = {m["id"]: by_title.get(title_key(m["origin_title"])) for m in model["methods"]}
    for x in model["extends"]:  # R1 (extends); provenance paper = the paper proposing the extending method, if in dataset
        sp = origin.get(x["source"])
        b.create_relationship(f"method:{x['source']}", "EXTENDS", f"method:{x['target']}",
                              {"type": "annotation", "note": x["note"],
                               "source_paper_title": sp["title"] if sp else None},
                              "manual_annotation", sp["id"] if sp else None)

    for m in model["methods"]:  # R2
        p = by_title.get(title_key(m["origin_title"]))
        if p is None:
            log.warning("origin paper for %s not in dataset; no PROPOSES edge", m["id"])
            continue
        b.create_relationship(p["id"], "PROPOSES", f"method:{m['id']}",
                              {"type": "title_match", "field": "title", "text": p["title"]}, "title_match", p["id"])

    for p in papers:  # R3
        if not p["abstract"]:
            continue
        text = f"{p['title']}. {p['abstract']}"
        tasks = [(t, find_alias(text, t["aliases"])) for t in model["tasks"]]
        tasks = [(t, h) for t, h in tasks if h]
        if not tasks:
            continue
        for m in model["methods"]:
            mh = find_alias(text, m["aliases"])
            if not mh:
                continue
            for t, _ in tasks:
                b.create_relationship(f"method:{m['id']}", "EVALUATED_ON", f"task:{t['id']}",
                                      {"type": "abstract_cooccurrence", "field": "title+abstract",
                                       "text": snippet(text, mh[1], mh[2])}, "abstract_cooccur", p["id"])
    state = {"schema_version": K.SCHEMA_VERSION, "generated_at": datetime.now(timezone.utc).isoformat(),
             "dataset_manifest": manifest_name, "entities": b.entities, "relationships": b.relationships}
    K.validate(state)
    return state
