"""Raw paper record -> normalized paper dict. Every dropped/changed item is logged."""
from __future__ import annotations
import logging
import re
import unicodedata
from typing import Any

log = logging.getLogger(__name__)


class MalformedRecord(ValueError):
    pass


def clean_text(s: Any) -> str:
    if s is None:
        return ""
    s = unicodedata.normalize("NFKC", str(s))
    return re.sub(r"\s+", " ", s).strip()


def title_key(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", clean_text(title).lower())


def normalize_author(name: Any) -> str:
    n = clean_text(name)
    if "," in n:  # "Last, First" -> "First Last"
        last, _, first = n.partition(",")
        n = f"{first.strip()} {last.strip()}".strip()
    return n


def normalize_paper(raw: dict) -> dict:
    if not isinstance(raw, dict):
        raise MalformedRecord("record is not an object")
    title = clean_text(raw.get("title"))
    if not title:
        raise MalformedRecord("missing title")
    ext = raw.get("externalIds") or {}
    s2_id = clean_text(raw.get("paperId"))
    arxiv = clean_text(ext.get("ArXiv")).lower() or None
    doi = clean_text(ext.get("DOI")).lower() or None
    if not (s2_id or arxiv or doi):
        raise MalformedRecord(f"no identifier for '{title}'")
    pid = f"paper:{s2_id}" if s2_id else (f"paper:arxiv:{arxiv}" if arxiv else f"paper:doi:{doi}")
    abstract = clean_text(raw.get("abstract")) or None
    year = raw.get("year")
    year = year if isinstance(year, int) else None
    if year is None:
        log.warning("paper %s has no valid year", pid)
    authors = [a for a in (normalize_author((x or {}).get("name") if isinstance(x, dict) else x)
                           for x in (raw.get("authors") or [])) if a]
    cites = raw.get("citationCount")
    return {
        "id": pid, "s2_id": s2_id or None, "title": title, "abstract": abstract, "year": year,
        "authors": authors, "doi": doi, "arxiv_id": arxiv,
        "url": clean_text(raw.get("url")) or None,
        "citation_count": cites if isinstance(cites, int) else 0,
    }


def normalize_all(raws: list) -> list[dict]:
    out = []
    for r in raws:
        try:
            out.append(normalize_paper(r))
        except MalformedRecord as e:
            log.warning("dropped malformed record: %s", e)
    return out


def dedupe(papers: list[dict]) -> tuple[list[dict], list[dict]]:
    """Dedupe on DOI, arXiv id, then normalized title. Keeps the record with an abstract / more citations."""
    kept: dict[str, dict] = {}
    index: dict[str, str] = {}
    dropped = []
    for p in papers:
        keys = [k for k in (f"doi:{p['doi']}" if p["doi"] else None,
                            f"arxiv:{p['arxiv_id']}" if p["arxiv_id"] else None,
                            f"title:{title_key(p['title'])}") if k]
        hit = next((index[k] for k in keys if k in index), None)
        if hit is None:
            kept[p["id"]] = p
            for k in keys:
                index[k] = p["id"]
            continue
        cur = kept[hit]
        better = (bool(p["abstract"]), p["citation_count"]) > (bool(cur["abstract"]), cur["citation_count"])
        loser = cur if better else p
        dropped.append({"dropped_id": loser["id"], "kept_id": (p if better else cur)["id"]})
        log.info("duplicate: dropped %s", loser["id"])
        if better:
            del kept[hit]
            kept[p["id"]] = p
            for k in keys:
                index[k] = p["id"]
    return list(kept.values()), dropped
