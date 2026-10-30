# YottaFlex Learning Recommendation Challenge — Project Brief

## Purpose
Build an explainable, reproducible end-to-end synthetic-data and learning-recommendation workflow for the YottaFlex Associate AI Forward Deployed Engineer challenge.

## Source of truth
Before implementing, read the complete company-provided:
1. Candidate Project FAQ
2. Project Submission Guidelines
3. Full challenge problem statement / job description

If this brief conflicts with the company's documents, follow the company documents and record the conflict or ambiguity in `docs/DECISIONS_AND_ASSUMPTIONS.md`. Do not invent missing requirements.

## Proposed stack
- Python 3.11+ (use the installed compatible Python version if 3.11+ is unavailable and document it)
- SQLite with explicit schema, primary keys, foreign keys, and constraints
- Standard-library `random` with a fixed seed for deterministic synthetic data
- pytest for tests
- Streamlit for a small local demo, only after the core workflow works
- Git/GitHub for version control and submission
- Pandas only if it materially simplifies analysis/exports; avoid unnecessary dependencies
- No paid services, API keys, or hosted infrastructure required

## Functional requirements
1. Generate synthetic data for the entities and relationships required by the official challenge.
2. Use stable, documented IDs (for example `LRN-000001`, `CRS-000001`, `SKL-000001`, `CNT-000001`). Follow the exact formats in the challenge document when specified.
3. Use one parameterized generator for both small development datasets and the full target dataset.
4. Support a fixed seed and demonstrate reproducibility using row counts and file checksums or an equivalent deterministic comparison.
5. Create a relational schema and data dictionary. Document keys, relationships, cardinalities, lifecycle/effective dates, bridge tables, event history, and derived values where applicable.
6. Implement mastery calculations using only attempts available at the requested as-of time. Prevent future-data leakage.
7. Implement prerequisite-aware recommendation logic: candidates must pass hard prerequisite gates before ranking.
8. Return a ranked list with score, rationale/reason codes, and a rule/algorithm version.
9. Validate primary keys, foreign keys, timestamp order, prerequisite constraints, and other applicable business rules.
10. Include isolated, labeled edge/anomaly cases matching the official challenge, including at least: prerequisite-violating recommendation, invalid attempt timestamp order, content mapped to a nonexistent skill, mastery using a future attempt, and a learning path loop without progress. Confirm exact expectations against the official statement.
11. Keep intentionally invalid cases separate from clean baseline data so they do not silently corrupt normal generation. Use a documented anomaly fixture/ground-truth format.
12. Export required outputs in the formats requested by the official challenge (CSV/JSON/SQL as applicable).
13. Provide a simple local demo only after core generation, recommendation, validation, and tests work.
14. Include tests and honest evaluation results. Never fabricate metrics or claim unrun tests passed.

## Scale and performance
The challenge mentions target volumes of 10,000 learners, 500 skills, 2,000 content items, and 500,000 attempts. Confirm these values and all other requirements against the official challenge document.
- First run a small fixture.
- Then run a medium dataset.
- Attempt the full target only after correctness checks pass.
- Record generation time, validation time, row counts, and any limitations.
- Do not reduce target volumes silently. If full scale cannot be completed, document exactly what was completed and what remains.

## Suggested implementation order
1. Inspect source documents and workspace; summarize requirements and uncertainties.
2. Write `docs/DECISIONS_AND_ASSUMPTIONS.md` and schema/data dictionary.
3. Implement deterministic data generation and database constraints.
4. Implement validation and anomaly fixtures.
5. Implement temporal-safe mastery and prerequisite-aware recommendation ranking.
6. Add tests for normal and edge cases.
7. Add evaluation metrics only where labels and definitions justify them.
8. Add exports and reproducibility check.
9. Add Streamlit demo if time allows.
10. Write README, AI usage disclosure, and actual prompt history; run all verification commands.

## Definition of done
- Fresh setup instructions work on Windows.
- A small dataset can be generated from a documented command.
- Validation and tests run, and actual results are recorded.
- Recommendations are explainable and respect prerequisite and as-of-time rules.
- Edge cases are intentionally labeled and testable.
- Reproducibility is demonstrated rather than merely asserted.
- README explains setup, run, verify, architecture, decisions, limitations, and outputs.
- AI prompt history and usage disclosure are truthful and reflect actual tool usage.
- No secrets, credentials, `.venv`, or unnecessarily large generated data are committed.
- Do not publish or push to GitHub unless the user explicitly approves.

## Working principles
- Implement the project; do not stop after producing a plan.
- Prefer clear, modular, testable code over clever abstractions.
- Do not claim a requirement is complete without evidence.
- Do not invent data provenance, benchmark results, evaluation labels, citations, or prompt timestamps.
- Ask the user only when a genuinely blocking decision cannot be resolved from the source documents.
