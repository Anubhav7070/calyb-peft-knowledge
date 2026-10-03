# Decision log (sample decisions; AI-proposed for a practice build)
| ID | Decision | Alternatives | Why | Tradeoff |
|---|---|---|---|---|
| D1 | JSON knowledge state | SQLite, NetworkX | Human-readable, no tooling | No query engine; fine at ~100 papers |
| D2 | Hand-annotated EXTENDS/USES | Text extraction | Assignment forbids auto-extraction; metadata lacks them | Manual effort, small coverage |
| D3 | EVALUATED_ON via abstract co-occurrence | Full-text parsing | Simple, explainable rule | False positives/negatives |
| D4 | No LLM | LLM explanations | Traceability | Less fluent output |
| D5 | CLI only | FastAPI/Streamlit | Minimal surface to test | Less demo-friendly |
