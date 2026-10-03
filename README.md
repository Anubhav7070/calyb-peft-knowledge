# PEFT Knowledge Reasoner (practice build, Calyb Domain B)

> **Status / honesty note.** This is a practice build. The knowledge model (`knowledge_model/model.json`) and the
> design choices in `approach.md` are *sample* decisions written by an AI assistant, **not** the work of a Calyb
> candidate. Do not submit them to Calyb as your own. No real dataset is bundled: run `scripts/collect_data.py`
> (needs internet) to download one. No evaluation scores are reported because none have been measured.

## Overview
Given a short description of a NEW fine-tuning idea, the system maps it onto an explicit graph of PEFT methods,
concepts, tasks and papers, traverses relationships, and returns ranked related methods, evidence, and
method×task gaps, with a reasoning trace. No LLM is used anywhere.

## Problem
A junior ML engineer wants to choose a parameter-efficient fine-tuning method for an idea but the literature is fragmented.

## Architecture
```
Semantic Scholar API -> collect_data.py -> normalize/dedupe/select -> data/processed/papers.json (+ manifest)
papers.json + knowledge_model/model.json -> mapping.py (explicit rules R1-R3) -> validate -> knowledge/knowledge_state.json
NEW input text -> reasoning.py (alias match -> graph traversal -> scoring -> evidence -> gaps) -> JSON result
```

## Knowledge representation
Plain JSON (`knowledge/knowledge_state.json`): `entities[]` and `relationships[]`, each relationship carrying
`evidence`, `rule` and `source_paper`. `knowledge/schema.json` lists allowed types. Chosen over SQLite/NetworkX
because a reviewer can open and read it with no tooling; at ~100 papers performance is irrelevant.

**Entities:** Paper, Method, Concept, Task.
**Relationships:** `Paper PROPOSES Method`, `Method EXTENDS Method`, `Method USES Concept`, `Method EVALUATED_ON Task`.

## Knowledge construction (no automatic extraction)
| Rule | Creates | Mechanism |
|---|---|---|
| R1 manual_annotation | USES, EXTENDS | Hand-written in `model.json` with a note |
| R2 title_match | PROPOSES | Normalized paper title equals method's `origin_title` |
| R3 abstract_cooccur | EVALUATED_ON | A paper's title+abstract contains a method alias and a task alias; snippet stored as evidence |

Missing evidence means no edge. Nothing is inferred by a model.

## Reasoning
1. Validate input (non-empty, <= 4000 chars).
2. Match methods/concepts/tasks by explicit alias lists.
3. Score methods: named in input +3; uses a concept found in input +2; one EXTENDS hop from a scored method +1.
4. Attach proposing papers and EVALUATED_ON evidence.
5. Gaps: top candidates × tasks (from the input, else all tasks seen in the graph) with no EVALUATED_ON edge.
6. If nothing matches: `status: no_relevant_knowledge`.

## Install and run
```bash
pip install -r requirements.txt
cp .env.example .env            # optional S2_API_KEY
python scripts/collect_data.py  # needs internet; writes data/processed/papers.json + data/metadata/manifest.json
python scripts/build_knowledge.py
python scripts/run_demo.py      # runs examples/input/*.txt -> examples/output/*.json
python -m peft_kb.cli --text "quantized low-rank update for summarization"   # with PYTHONPATH=src
pytest
```
Environment variable used: `S2_API_KEY` (optional).

## Testing
`pytest`: ingestion (normalization, dedupe, retry/rate-limit via fake session, selection), mapping, knowledge
state (save/load/validation/corruption), reasoning (valid, unrelated, task-only, gaps, empty, too long, unicode),
CLI. Tests use clearly synthetic fixtures (`tests/conftest.py`). The leakage test is skipped until real data exists.
Last local run before packaging: 43 passed, 1 skipped (leakage test needs real data).

## Qualitative evaluation
`python scripts/evaluate.py` runs `eval/eval_set.json` (7 hand-written new inputs incl. unrelated, empty and a known-miss paraphrase) and writes `eval/eval_report.json` with expected vs actual status/top methods, latency and trace. It is a tiny qualitative check, not a metric. Before packaging I only dry-ran it on a graph built with zero papers (7/7 matched expectations), which validates reasoning logic, not dataset quality. Re-run it after you build from real data and commit the report.

## Limitations
- EVALUATED_ON is a title+abstract co-occurrence heuristic, not proof a method was evaluated on a task.
- Alias matching is lexical: paraphrases that match no alias are missed; short aliases (e.g. "QA") can false-match.
- The method/concept lexicon is small and hand-made; new methods need manual additions.
- Scores are ranking heuristics, not probabilities. No quantitative evaluation has been run.
- Selection by citation count favors older papers.
- Ranking quirk: EXTENDS hops give the base method (e.g. LoRA) points from every extension, so it can outrank the more specific combination the user described (seen in eval case E1). Review whether that is the behavior you want.

## Future work
Hand-annotate more EXTENDS edges with paper citations; add a manually verified evaluation set; optional LLM for
readable explanations only (kept separate from the knowledge state).

## Assignment compliance (self-check)
No KG-extraction tools; relationships come from stated rules; knowledge state is inspectable JSON; new input is
reasoned over via graph traversal; no fabricated data or results. The one open item: the conceptual model is a
sample, so it does not satisfy "core idea and knowledge model are mine" for a real submission.
