import pytest
from peft_kb.normalize import MalformedRecord, normalize_paper, normalize_all, dedupe
from peft_kb import ingest

def raw(**kw):
    d = {"paperId": "x1", "title": "  Some  Title\u00a0", "abstract": "abs", "year": 2021, "authors": [{"name": "Doe, Jane"}], "externalIds": {"DOI": "10.1/ABC"}, "citationCount": 4}
    d.update(kw); return d

def test_valid_paper_normalized():
    p = normalize_paper(raw())
    assert p["title"] == "Some Title" and p["authors"] == ["Jane Doe"] and p["doi"] == "10.1/abc"

def test_missing_title_and_id_rejected():
    with pytest.raises(MalformedRecord): normalize_paper(raw(title=""))
    with pytest.raises(MalformedRecord): normalize_paper(raw(paperId=None, externalIds={}))

def test_missing_abstract_kept_as_none():
    assert normalize_paper(raw(abstract=None))["abstract"] is None

def test_malformed_dropped_not_crashing():
    assert len(normalize_all([raw(), "junk", {"title": ""}])) == 1

def test_dedupe_prefers_abstract():
    a = normalize_paper(raw(paperId="a", abstract=None)); b = normalize_paper(raw(paperId="b"))
    kept, dropped = dedupe([a, b])
    assert [k["id"] for k in kept] == ["paper:b"] and len(dropped) == 1

def test_dedupe_by_title_without_ids_overlap():
    a = normalize_paper(raw(paperId="a", externalIds={})); b = normalize_paper(raw(paperId="b", externalIds={}, title="some title"))
    assert len(dedupe([a, b])[0]) == 1

class FakeResp:
    def __init__(s, code, data=None, headers=None): s.status_code, s._d, s.headers = code, data or {}, headers or {}
    def json(s): return s._d
class FakeSession:
    def __init__(s, codes): s.codes = list(codes); s.calls = 0
    def get(s, *a, **k):
        s.calls += 1; c = s.codes.pop(0)
        return FakeResp(c, {"data": [{"title": "t"}]}, {"Retry-After": "0"})

def test_rate_limit_retried(monkeypatch):
    monkeypatch.setattr(ingest.time, "sleep", lambda *_: None)
    s = FakeSession([429, 200])
    assert ingest.search("q", "2019-2025", 10, session=s) == [{"title": "t"}] and s.calls == 2

def test_persistent_failure_raises(monkeypatch):
    monkeypatch.setattr(ingest.time, "sleep", lambda *_: None)
    with pytest.raises(ingest.IngestError): ingest.search("q", "2019-2025", 10, retries=2, session=FakeSession([500, 500]))

def test_select_filters_and_anchors():
    cfg = {"year_start": 2019, "year_end": 2025, "target_count": 2, "exclude_title_terms": ["survey"], "require_abstract": True}
    mk = lambda i, t, y=2021, c=0, a="x": {"id": i, "title": t, "year": y, "abstract": a, "citation_count": c}
    ps = [mk("1", "A Survey of X", c=999), mk("2", "No abstract", a=None), mk("3", "Old", y=2010), mk("4", "Popular", c=50), mk("5", "Anchor Paper", c=1)]
    assert [p["id"] for p in ingest.select(ps, cfg, ["Anchor Paper"])] == ["5", "4"]
