# YottaFlex AI Recruiter Challenge
## Synthetic Learning Data and Explainable Learning Recommendation Workflow

[![Python 3.14](https://img.shields.io/badge/Python-3.14-blue.svg)](https://www.python.org/)
[![Database](https://img.shields.io/badge/Database-SQLite3-green.svg)](https://www.sqlite.org/)
[![Tests](https://img.shields.io/badge/Tests-19%2F19%20Passing-brightgreen.svg)](tests/)
[![Reproducibility](https://img.shields.io/badge/Reproducibility-100%25%20Deterministic-success.svg)](scripts/reproducibility_check.py)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 1. Project Overview

This repository contains the complete implementation for the **YottaFlex Associate AI Forward Deployed Engineer** candidate project. It delivers an end-to-end, local-first, zero-spend workflow that:

1. **Generates Synthetic Learning Telemetry**: A single deterministic generator parameterizes volume tiers from small development fixtures up to the target scale (**10,000 learners, 500 skills, 2,000 content items, and 500,000 attempts**) using a fixed seed (`20261022`).
2. **Models 10 Relational Entities**: Enforces primary keys, foreign keys, bridge tables, and SQLite `PRAGMA foreign_keys = ON;`.
3. **Calculates Temporal-Safe Mastery**: Computes skill mastery via Exponentially Weighted Moving Average (EWMA) strictly as of a cutoff timestamp ($t_{\text{query}}$), preventing future attempts from leaking into past evaluations.
4. **Gates Prerequisites**: Enforces a Directed Acyclic Graph (DAG) of skill prerequisites as a hard eligibility gate before recommending downstream learning activities.
5. **Generates Explainable Recommendations**: Ranks eligible candidate activities using multi-factor weights (Skill Gap 45%, Difficulty Alignment 35%, Content Relevance 20%), attaching machine-readable reason codes, transparent rationale text, and algorithm versioning.
6. **Detects & Isolates 5 Explicit Anomalies**: Validates integrity rules and isolates labeled test fixtures without corrupting the clean baseline dataset.
7. **Verifies 100% Deterministic Reproducibility**: Demonstrates row count and SHA-256 hash parity across independent regeneration runs.
8. **Exports Multi-Format Deliverables**: Exports clean database tables to CSV, JSON, and full SQL transaction dumps.
9. **Interactive Local Dashboard**: Features a Streamlit application (`app.py`) for inspecting learner mastery, prerequisite DAGs, recommendations, and anomaly detection.

---

## 2. Quickstart & Verification (Windows PowerShell)

The solution runs local-first with zero paid APIs, secrets, or cloud dependencies.

### 2.1 Prerequisites
- Windows 10/11 with PowerShell
- Python 3.11+ (Python 3.14+ supported)

### 2.2 Setup Environment
Clone or navigate to the repository directory:
```powershell
# Verify Python version
py --version

# Install dependencies (pytest, pandas, streamlit)
py -m pip install -r requirements.txt
```

### 2.3 Run Core Verification Pipeline
Execute the full sequence with one-line commands:

```powershell
# 1. Generate small baseline dataset & recommendations (with CSV/JSON/SQL exports)
py scripts/generate_data.py --scale small --export-all

# 2. Validate database constraints, business rules, and anomaly fixtures
py scripts/validate_data.py

# 3. Verify deterministic reproducibility across independent runs
py scripts/reproducibility_check.py

# 4. Run automated test suite (31 tests covering REST API, schema, mastery, recommender, and anomalies)
py -m pytest -v
```

### 2.4 Launch the Production Web Application (Frontend + REST API)
Start the complete end-to-end full-stack web application with a single command:

```powershell
# Launch FastAPI web server & interactive single-page application
py run_server.py
```
- **Web Application UI:** [`http://localhost:8000`](http://localhost:8000) (Interactive SPA with mastery radar, real-time simulator, recommendations, interactive DAG visualizer, and anomaly lab)
- **Interactive Swagger REST API:** [`http://localhost:8000/docs`](http://localhost:8000/docs)
- **OpenAPI JSON Spec:** [`http://localhost:8000/openapi.json`](http://localhost:8000/openapi.json)

### 2.5 Alternative Streamlit Dashboard
```powershell
py -m streamlit run app.py
```
Open `http://localhost:8501` to view the alternative Streamlit dashboard.

### 2.6 Docker Containerized Deployment (Ready to Deploy)
Deploy anywhere with one command using Docker:
```bash
# Build and run containerized service
docker compose up --build
```
The application will automatically initialize the database, expose port `8000`, run automated health checks, and serve both the web frontend and the REST API.

---

## 3. Data Architecture & Relational Schema

The data model comprises 10 entities adhering to strict relational constraints:

```mermaid
erDiagram
    learners ||--o{ attempts : initiates
    learners ||--o{ assessment_results : achieves
    learners ||--o{ learning_paths : follows
    learners ||--o{ recommendations : receives

    courses ||--|{ content_items : contains

    skills ||--o{ skill_prerequisites : "requires (DAG)"
    skills ||--o{ content_skills : "mapped to"
    skills ||--o{ assessment_results : "evaluated on"
    skills ||--o{ learning_paths : targets
    skills ||--o{ recommendations : targets

    content_items ||--o{ content_skills : "tagged with"
    content_items ||--o{ attempts : "logged on"
    content_items ||--o{ learning_paths : includes
    content_items ||--o{ recommendations : suggested

    attempts ||--o{ assessment_results : generates
```

### Entity Identifier Formats
- **Learners**: `LRN-000001`
- **Courses**: `CRS-000001`
- **Skills**: `SKL-000001`
- **Content Items**: `CNT-000001`
- **Attempts**: `ATT-<learner_id>-000001`
- **Learning Paths**: `PATH-2026-000001`
- **Assessments**: `ASM-000001`
- **Recommendations**: `REC-000001`

Detailed table definitions, column types, cardinalities, and lifecycle rules are documented in [`docs/data_dictionary.md`](file:///c:/Users/shaik/OneDrive/Documents/yottaflex-project/yottaflex_antigravity_starter/docs/data_dictionary.md).

---

## 4. Algorithmic Formulations

### 4.1 Temporal-Safe Mastery (EWMA)
For learner $L$, skill $S$, and query cutoff timestamp $t_{\text{query}}$:
1. Filter assessment results: `WHERE assessed_at <= t_query AND end_time <= t_query`.
2. Compute Exponentially Weighted Moving Average with recency smoothing factor $\alpha = 0.35$:
   $$M_0 = \text{Score}_1$$
   $$M_i = \alpha \cdot \text{Score}_i + (1 - \alpha) \cdot M_{i-1} \quad \text{for } i \in [1, k]$$
   $$Mastery(L, S, t_{\text{query}}) = \min(1.0, \max(0.0, M_k))$$

### 4.2 Prerequisite Gating
Target skill $S$ is eligible for recommendation to learner $L$ at time $t$ if and only if:
$$\forall P \in \text{Prerequisites}(S): Mastery(L, P, t) \ge \tau_{\text{prereq}} \quad (\tau_{\text{prereq}} = 0.70)$$
If any prerequisite skill has mastery $< 0.70$, all content items tagged to $S$ are disqualified.

### 4.3 Multi-Factor Explainable Recommendation Scoring
For candidate content item $C$ tagged to eligible deficit skill $S$ ($Mastery < 0.85$):
- **Skill Gap**: $\text{Gap} = 1.0 - Mastery(L, S, t)$
- **Difficulty Fit**: $\text{DiffFit} = 1.0 - \frac{| (1 + 4 \cdot Mastery) - \text{Difficulty}(C) |}{4.0}$
- **Content Relevance**: $\text{Rel} = \text{relevance\_weight}(C, S)$
- **Composite Score**:
  $$\text{Score} = 0.45 \cdot \text{Gap} + 0.35 \cdot \text{DiffFit} + 0.20 \cdot \text{Rel}$$
- **Reason Codes**: Machine-readable tags (`SKILL_DEFICIT_HIGH_PRIORITY`, `SKILL_PRACTICE_RECOMMENDED`) paired with transparent narrative explanations.

---

## 5. Isolated Labeled Anomaly Fixtures

In compliance with challenge requirements, intentional anomalies are generated as isolated, cataloged fixtures in [`data/ground_truth/anomalies.json`](file:///c:/Users/shaik/OneDrive/Documents/yottaflex-project/yottaflex_antigravity_starter/data/ground_truth/anomalies.json) rather than corrupting the clean baseline dataset:

| Case ID | Name | Issue Type | Injected Scenario | Expected Handling | Detection Verification |
|---|---|---|---|---|---|
| `ANOM-001` | Prerequisite Violation | `PREREQUISITE_VIOLATION` | Recommendation created for advanced skill when prerequisite mastery is 0.25 (< 0.70) | Engine rejects; Validator flags violation | `tests/test_anomalies.py::test_anomaly_1_prerequisite_violation_detected` |
| `ANOM-002` | Timestamp Inversion | `INVALID_TIMESTAMP_ORDER` | Attempt logged with `start_time` 2 hours after `end_time` | SQLite CHECK constraint rejects; Validator flags | `tests/test_anomalies.py::test_anomaly_2_invalid_timestamp_order_detected` |
| `ANOM-003` | Orphaned Bridge Reference | `ORPHAN_CONTENT_SKILL` | ContentItem mapped to nonexistent `SKL-999999` | SQLite FOREIGN KEY constraint rejects; Validator flags | `tests/test_anomalies.py::test_anomaly_3_orphaned_content_skill_detected` |
| `ANOM-004` | Temporal Future Leakage | `FUTURE_ATTEMPT_LEAKAGE` | Attempt completed at $t+7$ days leaked into mastery at $t$ | Mastery engine strictly ignores attempts past cutoff | `tests/test_anomalies.py::test_anomaly_4_temporal_future_leakage_prevented` |
| `ANOM-005` | Learning Path Loop | `LOOP_WITHOUT_PROGRESS` | Path sequence contains repetitive cycles without skill progress | Validator detects cycle and flags stagnation | `tests/test_anomalies.py::test_anomaly_5_learning_path_loop_detected` |

---

## 6. Project Structure

```text
yottaflex_antigravity_starter/
├── README.md                              # Complete setup, architecture, and verification guide
├── PROJECT_BRIEF.md                       # Challenge overview and constraints
├── ANTIGRAVITY_PROMPT.md                  # Master execution prompt and build instructions
├── YottaFlex_Challenge_and_Job_Description.md  # Official challenge specification
├── requirements.txt                       # Runtime dependencies (pytest, streamlit, pandas)
├── schema.sql                             # DDL with 10 tables, constraints, foreign keys, indexes
├── app.py                                 # Streamlit interactive visual dashboard
├── src/
│   ├── __init__.py
│   ├── config.py                          # Volume tiers, default seed, ID formats, weights
│   ├── data_access.py                     # SQLite DAL, batch insertion, CSV/JSON/SQL export
│   ├── generator.py                       # Deterministic synthetic generator & anomaly builder
│   ├── mastery.py                         # Temporal-safe EWMA skill mastery engine
│   ├── recommender.py                     # Prerequisite-aware explainable recommender
│   ├── validator.py                       # Referential integrity, DAG acyclicity & rule checks
│   ├── api.py                             # Production FastAPI REST application & endpoints
│   ├── static/index.html                  # Interactive Single-Page Application (SPA) web frontend
│   └── evaluation.py                      # Honest metrics calculation and markdown reporter
├── Dockerfile                             # Production container image definition
├── docker-compose.yml                     # One-click containerized deployment service
├── run_server.py                          # Dedicated web application runner
├── scripts/
│   ├── generate_data.py                   # CLI data generator & exporter
│   ├── validate_data.py                   # CLI database and anomaly validator
│   └── reproducibility_check.py           # Verification script comparing table counts & SHA-256 hashes
├── tests/
│   ├── test_api.py                        # Tests for FastAPI REST endpoints & web UI serving
│   ├── test_generator.py                  # Tests for generation, volumes, IDs, and DAGs
│   ├── test_mastery.py                    # Tests for EWMA math and temporal cutoff
│   ├── test_recommendations.py            # Tests for prerequisite gating and explainability
│   └── test_anomalies.py                  # Automated tests for all 5 isolated anomaly fixtures
├── docs/
│   ├── REQUIREMENTS_CHECKLIST.md          # 16-point traceability checklist with evidence
│   ├── DECISIONS_AND_ASSUMPTIONS.md       # Architectural decisions, trade-offs, and rationale
│   ├── data_dictionary.md                 # Entity attributes, types, cardinalities, and formulas
│   ├── architecture.md                    # System architecture and Mermaid diagrams
│   ├── EVALUATION_REPORT.md               # Empirical evaluation report with actual metrics
│   ├── AI_PROMPT_HISTORY.md               # Verbatim prompt history for AI tools
│   └── AI_USAGE_DISCLOSURE.md             # Transparent AI disclosure and manual verification notes
├── data/
│   ├── sample/                            # Small sample database (learning_workflow.db)
│   └── ground_truth/                      # anomalies.json ground truth fixture catalog
└── exports/                               # CSV, JSON, and SQL deliverables (gitignored)
```

---

## 7. Evidence & Test Results Summary

- **Automated Tests**: 31 passed in 1.86s (`pytest -v`)
- **Web Application**: Live interactive SPA serving on `http://localhost:8000` with Swagger docs at `/docs`
- **Reproducibility**: 10/10 tables verified identical SHA-256 checksums across independent runs (`reproducibility_check.py`)
- **Validation**: 6/6 integrity checks passed on baseline (`validate_data.py`)
- **Anomaly Detection**: 5/5 anomaly fixtures identified and verified (`anomalies.json`)
- **Export Deliverables**: CSV, JSON, and SQL dumps generated in `exports/`

---

## 8. License & Attribution

Developed for the YottaFlex Associate AI Forward Deployed Engineer candidate assessment. Distributed under the MIT License.
