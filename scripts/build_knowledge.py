"""Build and validate knowledge/knowledge_state.json from data/processed/papers.json."""
import _path  # noqa
import json, logging, sys
from peft_kb import knowledge as K
from peft_kb.mapping import build_state

logging.basicConfig(level=logging.INFO)
try:
    papers = json.load(open("data/processed/papers.json", encoding="utf-8"))
except FileNotFoundError:
    sys.exit("data/processed/papers.json missing; run scripts/collect_data.py first")
model = json.load(open("knowledge_model/model.json"))
state = build_state(papers, model, "data/metadata/manifest.json")
K.save(state, "knowledge/knowledge_state.json")
json.dump(K.schema_doc(), open("knowledge/schema.json", "w"), indent=2)
print(json.dumps(K.KnowledgeState(state).stats(), indent=2))
