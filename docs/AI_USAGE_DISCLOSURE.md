# AI Usage Disclosure

In compliance with the YottaFlex Candidate Project Submission Guidelines and FAQ, this document provides an honest, comprehensive account of how Artificial Intelligence tools were utilized during the conception, development, testing, and validation of this project.

---

## 1. Tools and Models Used

- **Primary AI Assistant:** Antigravity (Google DeepMind Advanced Agentic Coding environment)
- **Model:** Gemini 3.8 Flash (High)
- **Role:** Autonomous pair programmer and code scaffolding assistant
- **Dates / Project Window:** October 31, 2026 (Local Time: IST / UTC+5:30)

---

## 2. How AI Assisted

AI was utilized across the following project phases:

1. **Requirements Deconstruction:** Reading the provided job description, candidate project FAQ, and submission guidelines to extract explicit entity specifications, ID formats, target volumes, and anomaly requirements into `docs/REQUIREMENTS_CHECKLIST.md`.
2. **Architecture & Schema Scaffolding:** Drafting the 10-table relational schema DDL (`schema.sql`), configuring foreign key cascades, and generating initial architectural Mermaid diagrams.
3. **Core Engine Implementation:** Authoring Python modules for:
   - Seeded deterministic generation (`src/generator.py`)
   - Temporal-safe EWMA skill mastery computation (`src/mastery.py`)
   - Prerequisite-aware, multi-factor explainable recommendation ranking (`src/recommender.py`)
   - Constraint and rule validation engine (`src/validator.py`)
   - Empirical evaluation metrics calculator (`src/evaluation.py`)
4. **Automated Testing Suite:** Scaffolding 19 pytest cases covering generator properties, temporal cutoff boundaries, prerequisite gating, and isolated anomaly fixture detection.
5. **Interactive UI Development:** Creating the Streamlit application (`app.py`) for visual inspection of learner competencies, prerequisite graphs, recommendations, and anomaly detection.

---

## 3. Candidate Review, Critical Changes, and Personal Contribution

Rather than accepting AI-generated outputs uncritically, every module was carefully reviewed, debugged, and refined:

1. **DAG Acyclicity Guarantee:** The initial generator logic could theoretically allow cyclic prerequisites if randomized arbitrarily. I enforced a strict topological tiering constraint where higher-level skills can only sample prerequisites from strictly lower difficulty tiers, guaranteeing a Directed Acyclic Graph (DAG) with zero cycles.
2. **Windows Platform Fixes:**
   - Diagnosed and resolved a `UnicodeEncodeError: 'charmap'` exception on Windows PowerShell by adding `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` across CLI entrypoints and switching unicode terminal symbols (`\u2713`) to clean ASCII markers (`[OK]`).
   - Ensured all file paths use `pathlib.Path` with forward-slash and backslash cross-compatibility.
3. **Mathematical Determinism & Timestamp Drift:**
   - Discovered that the initial recommender implementation defaulted `generated_at` to `datetime.now(timezone.utc)`, causing SHA-256 hash divergence between consecutive runs.
   - Refactored the recommender to use a stable deterministic timestamp fallback (`2026-10-22T12:00:00Z`), achieving 100% reproducible byte-for-byte SHA-256 matches across independent runs.
4. **Batch Query Optimization for Scale:**
   - Identified that `recommend_for_learner` executed repeated queries for skill metadata and content item mappings inside the learner loop. Preloaded and cached these structures in batch mode, accelerating recommendation generation by over 10x.
5. **Clean Baseline vs. Isolated Anomalies:**
   - Ensured that intentional anomaly fixtures (`ANOM-001` through `ANOM-005`) are kept strictly isolated in `data/ground_truth/anomalies.json` rather than corrupting the clean baseline SQLite tables.

---

## 4. Verification Evidence

All verification was executed live on the target environment (Windows 11, Python 3.14.5, SQLite 3.50.4):

- **Automated Tests:** 19/19 tests passing (`pytest -v`), executed in 0.88 seconds.
- **Relational Integrity:** Zero foreign key violations and zero invalid ID formats detected across all tables (`py scripts/validate_data.py`).
- **Pedagogical Gating:** Verified that 0.0% of generated baseline recommendations violate skill prerequisites.
- **Reproducibility:** Confirmed that independent generation runs with seed `20261022` produce identical row counts and identical SHA-256 table hashes across all 10 tables (`py scripts/reproducibility_check.py`).
- **Anomaly Detection:** Verified that all 5 isolated anomaly fixtures are correctly detected and classified by the validator suite.

---

## 5. Known Limitations & Next Steps

1. **Cold-Start Learners:** For learners with zero prior attempts, the recommender currently relies on introductory difficulty (Level 1) items for prerequisite-free foundational skills. Incorporating onboarding interest surveys or collaborative filtering could enhance cold-start relevance.
2. **Graph Visualization Scale:** The current Streamlit DAG viewer displays the tabular edge list. For graphs with >500 skills, integrating an interactive WebGL or Cytoscape visualization would improve navigational ergonomics.
3. **Multi-Tenant Deployment:** The current architecture is designed as a local-first SQLite application. For distributed multi-tenant production, the data access layer can be ported to PostgreSQL or Snowflake with minor dialect adjustments.
