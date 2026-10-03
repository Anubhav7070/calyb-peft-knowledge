"""Collect, normalize, dedupe and select papers from Semantic Scholar. Needs network access."""
import _path  # noqa
import json, logging
from peft_kb.ingest import collect, write_json

logging.basicConfig(level=logging.INFO)
cfg = json.load(open("config/dataset.json"))
model = json.load(open("knowledge_model/model.json"))
papers, manifest = collect(cfg, [m["origin_title"] for m in model["methods"]])
write_json("data/processed/papers.json", papers)
write_json("data/metadata/manifest.json", manifest)
print(f"selected {manifest['paper_count']} papers; anchors not found: {manifest['anchor_titles_not_found']}")
