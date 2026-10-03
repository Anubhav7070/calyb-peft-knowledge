"""Semantic Scholar collection + selection. Network code is isolated here."""
from __future__ import annotations
import json
import logging
import os
import time
from datetime import datetime, timezone

import requests

from .normalize import dedupe, normalize_all, title_key

log = logging.getLogger(__name__)
API = "https://api.semanticscholar.org/graph/v1/paper/search"
FIELDS = "paperId,title,abstract,year,authors,externalIds,url,citationCount"


class IngestError(RuntimeError):
    pass


def search(query: str, year_range: str, limit: int, retries: int = 5, session=None) -> list[dict]:
    s = session or requests
    headers = {"x-api-key": os.environ["S2_API_KEY"]} if os.environ.get("S2_API_KEY") else {}
    params = {"query": query, "year": year_range, "fields": FIELDS, "limit": min(limit, 100)}
    for attempt in range(retries):
        try:
            r = s.get(API, params=params, headers=headers, timeout=30)
        except requests.RequestException as e:
            log.warning("network error (%s), retry %d", e, attempt + 1)
            time.sleep(2 ** attempt)
            continue
        if r.status_code == 200:
            return r.json().get("data", []) or []
        if r.status_code in (429, 500, 502, 503, 504):
            wait = float(r.headers.get("Retry-After", 2 ** attempt))
            log.warning("HTTP %s for '%s', sleeping %.1fs", r.status_code, query, wait)
            time.sleep(wait)
            continue
        raise IngestError(f"HTTP {r.status_code} for query '{query}'")
    raise IngestError(f"gave up after {retries} attempts for query '{query}'")


def select(papers: list[dict], cfg: dict, anchor_titles: list[str]) -> list[dict]:
    lo, hi = cfg["year_start"], cfg["year_end"]
    terms = [t.lower() for t in cfg["exclude_title_terms"]]
    ok = []
    for p in papers:
        if p["year"] is None or not (lo <= p["year"] <= hi):
            continue
        if cfg["require_abstract"] and not p["abstract"]:
            continue
        if any(t in p["title"].lower() for t in terms):
            continue
        ok.append(p)
    anchors = {title_key(t) for t in anchor_titles}
    anchored = [p for p in ok if title_key(p["title"]) in anchors]
    rest = sorted((p for p in ok if p not in anchored), key=lambda p: (-p["citation_count"], p["id"]))
    return (anchored + rest)[: cfg["target_count"]]


def collect(cfg: dict, anchor_titles: list[str], session=None) -> tuple[list[dict], dict]:
    yr = f"{cfg['year_start']}-{cfg['year_end']}"
    raws: list[dict] = []
    for q in list(cfg["queries"]) + list(anchor_titles):
        limit = cfg["per_query_limit"] if q in cfg["queries"] else 5
        raws += search(q, yr, limit, session=session)
        time.sleep(1.1)  # stay under public rate limit
    normalized = normalize_all(raws)
    unique, dropped = dedupe(normalized)
    chosen = select(unique, cfg, anchor_titles)
    found = {title_key(p["title"]) for p in chosen}
    missing = [t for t in anchor_titles if title_key(t) not in found]
    manifest = {
        "dataset_name": cfg["dataset_name"], "source": "Semantic Scholar Graph API (paper/search)",
        "topic": cfg["topic"], "selection_criteria": cfg["selection_rule"],
        "exclusion_criteria": {"title_terms": cfg["exclude_title_terms"], "require_abstract": cfg["require_abstract"]},
        "paper_count": len(chosen), "date_range": [cfg["year_start"], cfg["year_end"]],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "raw_records": len(raws), "after_normalization": len(normalized), "duplicates_dropped": len(dropped),
        "anchor_titles_not_found": missing,
        "paper_ids": [p["id"] for p in chosen],
    }
    return chosen, manifest


def write_json(path: str, obj) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
