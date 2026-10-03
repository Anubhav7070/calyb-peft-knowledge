# approach.md (SAMPLE: written for a practice build; replace with your own reasoning for a real submission)

## 1. Problem
A junior ML engineer picking a PEFT method for a new idea faces scattered comparisons across papers.

## 2. Dataset scope
Semantic Scholar, 2019-2025, target 70 papers on PEFT. Anchor papers (origin papers of the modeled methods) are
always included; the rest are by citation count. Excluded: no abstract, out of range, title contains survey/review/overview,
duplicates. Manifest is written to `data/metadata/manifest.json`.

## 3. Target user
Master's student / junior ML engineer, intermediate level.

## 4. Knowledge model
Entities: Paper (provenance), Method (the thing the user chooses), Concept (the mechanism, which lets an idea
that doesn't name a method still map to methods), Task (what methods are applied to; enables gap finding).
Relationships: PROPOSES (provenance), EXTENDS (lineage), USES (mechanism sharing), EVALUATED_ON (coverage).
Not modeled: datasets, metrics, hyperparameters, authors (no reliable source in metadata; would require extraction).

## 5-6. Construction and mapping
Rules R1-R3 in `src/peft_kb/mapping.py`; every edge stores its rule and evidence. EXTENDS/USES are hand-annotated
because Semantic Scholar metadata does not contain them and automatic extraction is prohibited.

## 7. Representation
JSON file: inspectable without tools; the dataset is small.

## 8. New input
A short free-text description of a proposed fine-tuning idea that is not an existing dataset paper; checked by `tests/test_leakage.py`.

## 9-10. Reasoning and evidence
Alias matching, then scoring by traversal (named +3, shared concept +2, EXTENDS hop +1), gaps from missing
EVALUATED_ON edges. Each candidate lists why it scored, proposing papers, and snippet evidence. Conflicts: none are
resolved; ties are flagged. No match returns `no_relevant_knowledge`.

## 11. Output
JSON: status, matched entities, ranked candidates with evidence, gaps, suggested baselines/reading, trace.

## 12. Tradeoffs
No LLM, embeddings, or UI: keeps reasoning traceable and the project explainable.

## 13. Limitations
See README. In particular EVALUATED_ON is heuristic and no quantitative evaluation exists.

## 14. Future work
Manual evaluation set; citation-linked EXTENDS annotations; optional LLM explanation layer separated from the graph.
