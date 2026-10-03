"""Knowledge state: schema, validation, (de)serialization, traversal helpers."""
from __future__ import annotations
import json
import os

ENTITY_TYPES = {"Paper", "Method", "Concept", "Task"}
# relationship type -> (allowed source type, allowed target type)
RELATIONSHIPS = {
    "PROPOSES": ("Paper", "Method"),
    "EXTENDS": ("Method", "Method"),
    "USES": ("Method", "Concept"),
    "EVALUATED_ON": ("Method", "Task"),
}
SCHEMA_VERSION = "1.0"


class KnowledgeError(ValueError):
    pass


def schema_doc() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "entity_types": sorted(ENTITY_TYPES),
        "relationship_types": {k: {"source": v[0], "target": v[1]} for k, v in RELATIONSHIPS.items()},
    }


def validate(state: dict) -> None:
    errors = []
    ents = {}
    for e in state.get("entities", []):
        if e.get("type") not in ENTITY_TYPES:
            errors.append(f"entity {e.get('id')}: bad type {e.get('type')}")
        if e.get("id") in ents:
            errors.append(f"duplicate entity id {e.get('id')}")
        ents[e.get("id")] = e
    seen = set()
    for r in state.get("relationships", []):
        rid = r.get("id")
        if rid in seen:
            errors.append(f"duplicate relationship id {rid}")
        seen.add(rid)
        spec = RELATIONSHIPS.get(r.get("type"))
        if not spec:
            errors.append(f"relationship {rid}: unknown type {r.get('type')}")
            continue
        s, t = ents.get(r.get("source")), ents.get(r.get("target"))
        if s is None or t is None:
            errors.append(f"relationship {rid}: orphan endpoint ({r.get('source')} -> {r.get('target')})")
            continue
        if (s["type"], t["type"]) != spec:
            errors.append(f"relationship {rid}: {s['type']}-{r['type']}->{t['type']} not allowed")
        if not r.get("evidence") or not r.get("rule"):
            errors.append(f"relationship {rid}: missing evidence/rule (provenance required)")
    if errors:
        raise KnowledgeError("invalid knowledge state:\n  " + "\n  ".join(errors))


class KnowledgeState:
    def __init__(self, data: dict):
        validate(data)
        self.data = data
        self.entities = {e["id"]: e for e in data["entities"]}
        self._out: dict = {}
        self._in: dict = {}
        for r in data["relationships"]:
            self._out.setdefault((r["source"], r["type"]), []).append(r)
            self._in.setdefault((r["target"], r["type"]), []).append(r)

    def entity(self, eid: str) -> dict:
        if eid not in self.entities:
            raise KnowledgeError(f"unknown entity: {eid}")
        return self.entities[eid]

    def of_type(self, t: str) -> list[dict]:
        return [e for e in self.data["entities"] if e["type"] == t]

    def out_edges(self, eid: str, rtype: str) -> list[dict]:
        return self._out.get((eid, rtype), [])

    def in_edges(self, eid: str, rtype: str) -> list[dict]:
        return self._in.get((eid, rtype), [])

    def stats(self) -> dict:
        ec, rc = {}, {}
        for e in self.data["entities"]:
            ec[e["type"]] = ec.get(e["type"], 0) + 1
        for r in self.data["relationships"]:
            rc[r["type"]] = rc.get(r["type"], 0) + 1
        return {"entities": ec, "relationships": rc}


def save(state: dict, path: str) -> None:
    validate(state)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def load(path: str) -> KnowledgeState:
    if not os.path.exists(path):
        raise KnowledgeError(f"knowledge state not found at {path}; run scripts/build_knowledge.py")
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise KnowledgeError(f"knowledge state is corrupted: {e}") from e
    if not isinstance(data, dict) or "entities" not in data or "relationships" not in data:
        raise KnowledgeError("knowledge state is corrupted: missing entities/relationships")
    return KnowledgeState(data)
