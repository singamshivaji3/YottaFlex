# Antigravity Master Prompt

You are helping implement my YottaFlex Associate AI Forward Deployed Engineer candidate project. Work directly in the open workspace.

## First: inspect, then implement
1. Inspect all files in the workspace and read the company-provided Candidate Project FAQ, Project Submission Guidelines, and full challenge statement/job description if available.
2. Extract the official requirements and create a checklist in `docs/REQUIREMENTS_CHECKLIST.md`, citing the source document/section for each requirement when possible.
3. Identify contradictions or ambiguities. Record assumptions in `docs/DECISIONS_AND_ASSUMPTIONS.md`; do not silently replace official requirements with guesses.
4. Then implement the project. Do not stop after giving me a plan.

## Constraints
- Target Windows development, local-first, and $0 required spend.
- Use Python, SQLite, pytest, Git, and optionally Streamlit for a local demo.
- Do not require paid APIs, API keys, cloud services, or external accounts to run core functionality.
- Use one parameterized deterministic generator for both small and full-scale datasets.
- Do not push, publish, or create a public repository unless I explicitly approve.
- Never put secrets or private recruitment details in the public repo.
- Do not fabricate test results, metrics, benchmarks, prompt history, timestamps, or completion claims.

## Core implementation
Build an end-to-end workflow matching the official challenge:
- relational schema, stable IDs, keys/constraints, documented relationships and cardinalities
- deterministic synthetic data generation with a configurable seed and entity volumes
- clean baseline dataset plus isolated labeled anomaly/edge fixtures
- temporal-safe mastery calculation (only attempts available as of the query timestamp)
- prerequisite-aware candidate filtering before ranking
- explainable recommendations with score, reason codes/rationale, and algorithm version
- validation of keys, references, timestamps, prerequisites, loops/progress, and other official rules
- required CSV/JSON/SQL exports
- reproducibility verification using counts and checksums or an equivalent deterministic check
- honest evaluation metrics where labels and definitions support them
- tests for normal behavior, constraints, anomalies, temporal leakage, and deterministic output
- optional Streamlit dashboard after the core pipeline works

Check the official documents for exact entity names, volumes, ID formats, anomaly definitions, and deliverables. If they specify something more precise than this prompt, follow the official specification.

## Engineering standards
- Separate generator, schema/data access, mastery, recommender, validator, and evaluation logic into understandable modules.
- Use type hints and docstrings where useful.
- Prefer simple, explainable algorithms.
- Use explicit transactions and enable SQLite foreign keys on every connection.
- Avoid loading the entire large dataset into memory unnecessarily.
- Keep baseline data valid; do not inject intentional corruption into the normal dataset.
- Keep ground truth/labels separate from the anomaly records where practical.
- Make recommendation results deterministic for the same data, seed, as-of time, and configuration.
- Include clear error messages and validate CLI arguments.
- Avoid unnecessary dependencies and abstractions.

## Suggested repository layout
Create or adapt this structure based on the official challenge:

- `README.md`
- `PROJECT_BRIEF.md`
- `requirements.txt`
- `app.py` (only if Streamlit is implemented)
- `schema.sql`
- `src/__init__.py`
- `src/config.py`
- `src/generator.py`
- `src/data_access.py`
- `src/mastery.py`
- `src/recommender.py`
- `src/validator.py`
- `src/evaluation.py`
- `scripts/generate_data.py`
- `scripts/validate_data.py`
- `scripts/reproducibility_check.py`
- `tests/test_generator.py`
- `tests/test_mastery.py`
- `tests/test_recommendations.py`
- `tests/test_anomalies.py`
- `docs/data_dictionary.md`
- `docs/architecture.md`
- `docs/DECISIONS_AND_ASSUMPTIONS.md`
- `docs/REQUIREMENTS_CHECKLIST.md`
- `docs/AI_PROMPT_HISTORY.md`
- `docs/AI_USAGE_DISCLOSURE.md`
- `data/sample/` (small sample only)
- `data/ground_truth/`
- `exports/` (generated outputs should usually be gitignored)

## Build order
1. Requirements checklist, assumptions, schema/data dictionary.
2. Deterministic small-scale generator and schema.
3. Validator and labeled anomaly fixtures.
4. Temporal-safe mastery and prerequisite-aware recommender.
5. Tests and reproducibility check.
6. Export formats and evaluation report.
7. Full-scale run and performance notes if feasible.
8. Streamlit demo if time remains.
9. README and AI transparency documentation.
10. Run all commands from a clean setup and fix failures.

## Verification
Provide exact PowerShell commands for Windows. At minimum, verify:
- install dependencies
- generate a small dataset
- validate it
- run tests
- run the reproducibility check
- start the demo if implemented

After each major stage, summarize files changed and evidence produced. At the end, give me:
1. requirements checklist with status and evidence
2. exact commands and actual outputs/results
3. known bugs, incomplete requirements, and limitations
4. architecture and algorithm explanation I can learn for an interview
5. a list of AI-generated/AI-assisted areas I should personally review
6. remaining manual steps for GitHub submission

Do not say “done” just because files were written. Run the code and tests. If something fails, diagnose and fix it where feasible.
