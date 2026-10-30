# UI and Functional Audit Report
**YottaFlex AI Learning Recommendation & Data Quality Engine**

- **Audit Date:** October 31, 2026
- **Auditor:** Candidate Engineering Team (Pair Programming Audit)
- **Environment:** Windows 11 (PowerShell), Python 3.14.5, SQLite 3.50.4
- **Automated Test Evidence:** 31 / 31 passing tests (`py -m pytest -v`)

---

## 1. Executive Summary

This audit rigorously inspects the full-stack system against the 13 required end-to-end workflows specified in the YottaFlex coding challenge. While the core algorithmic engines (temporal-safe EWMA mastery, prerequisite DAG gating, deterministic generation, and isolated anomaly fixtures) operate with 100% mathematical precision and pass all automated tests, the inspection revealed **three specific functional and UI gaps** that require remediation:
1. **Database Explorer Disconnection (Workflow 9)**: The UI table explorer hardcoded a fallback to `/api/skills/prerequisites-graph` for all tables other than `learners`, because `src/api.py` lacked a generic table query endpoint.
2. **Hardcoded Anomaly Detector Endpoint (Workflow 8)**: In `src/api.py`, `POST /api/anomalies/detect/{case_id}` hardcoded `detected = True` as a stub rather than executing authentic validation logic against the fixture payload.
3. **Incomplete Learner Selection View & Simulator Stubs (Workflows 1 & 6)**: Selecting a learner rendered the mastery breakdown but omitted the recent assessment history table; and the simulator dropdown used static stub options rather than real content items from the database.

---

## 2. Detailed Audit Table (Workflows 1 to 13)

| ID | Requirement / Workflow | Current Implementation | Actual Evidence or Test Used | Status | Recommended Fix |
|---|---|---|---|---|---|
| **W-01** | Selecting a learner updates mastery, assessment history and recommendations. | `loadLearnerMastery()` in `index.html` queries `/api/learners/{id}/mastery` and renders skills. Assessment history endpoint `GET /api/learners/{id}` exists on backend but is not called in the UI. Recommendations dropdown is unlinked. | Inspected `src/static/index.html` lines 773-835. `tests/test_api.py::test_learner_profile` passes. | **PARTIAL** | Fetch and render recent assessment history in the Learner Mastery tab; synchronize learner selection across Mastery, Recommendations, and Simulator tabs. |
| **W-02** | Mastery calculations respect selected time cutoff and exclude future attempts. | `src/mastery.py` filters `WHERE ar.assessed_at <= ? AND a.end_time <= ?`. The UI has a temporal cutoff input box passing `?as_of=...`. | `tests/test_mastery.py::test_temporal_cutoff_prevents_future_leakage` PASSED. Verified Attempt at $t+14$ days has 0 influence on cutoff at $t$. | **PASS** | Add quick cutoff presets in UI (e.g., "Cutoff 10 Days Ago", "Reset") to facilitate interviewer demonstration. |
| **W-03** | Recommendations are ranked using documented logic and include clear reason codes. | Multi-factor ranking: $0.45 \cdot \text{SkillGap} + 0.35 \cdot \text{DifficultyFit} + 0.20 \cdot \text{Relevance}$. Attach reason codes (`SKILL_DEFICIT_HIGH_PRIORITY`) and descriptions. | `tests/test_recommendations.py::test_recommendation_explainability_and_attributes` PASSED. UI cards display full score breakdown. | **PASS** | None required. Logic is verified and fully explainable. |
| **W-04** | Activities with unmet prerequisites are blocked by backend logic, not just hidden by UI. | `LearningRecommender.recommend_for_learner()` executes `check_prerequisites_met()` on the backend before ranking. Disqualifies candidate skills where prerequisite mastery $< 0.70$. | `tests/test_recommendations.py::test_prerequisite_gate_blocks_advanced_content` PASSED. Backend SQL query excludes disqualified items. | **PASS** | None required. Backend gate is strictly enforced. |
| **W-05** | The prerequisite graph reflects actual database dependencies and detects cycles. | `GET /api/skills/prerequisites-graph` loads nodes and edges from `skill_prerequisites`. `src/validator.py` implements Kahn's algorithm to detect cycles. | `tests/test_generator.py::test_prerequisite_dag_acyclicity` PASSED. Graph renders in Vis.js. | **PARTIAL** | Add real-time acyclicity verification in `GET /api/skills/prerequisites-graph` and display a "DAG Verified: Acyclic (0 Cycles)" badge in the UI. |
| **W-06** | Submitting a valid simulated assessment persists attempt and updates relevant results. | `POST /api/attempts` atomically writes attempt and creates `assessment_results` for all tagged skills. Simulator UI submits payload and displays created IDs. | `tests/test_api.py::test_submit_attempt_endpoint` PASSED. Verified new rows created in SQLite `attempts` and `assessment_results`. | **PARTIAL** | Replace static stub items in simulator dropdown with dynamic fetch from `GET /api/content-items`. |
| **W-07** | Invalid inputs are rejected or handled safely with clear error messages. | Pydantic schema validates ranges (`score: [0.0, 1.0]`, `duration: [1, 300]`). Nonexistent entities return HTTP 404. Negative tests assert `sqlite3.IntegrityError`. | `tests/test_api.py` and `tests/test_anomalies.py` pass. FastAPI returns structured JSON error responses. | **PASS** | Add ISO-8601 validation for `as_of` query parameter to return HTTP 400 on malformed date strings. |
| **W-08** | All five required anomaly scenarios are detected and traceable to ground truth. | Fixtures cataloged in `data/ground_truth/anomalies.json`. 5 negative unit tests verify rejection/flagging. BUT `POST /api/anomalies/detect/{case_id}` hardcoded `detected = True`. | `tests/test_anomalies.py` (5/5 tests PASSED). Inspected `src/api.py` line 433: stub `detected = True`. | **PARTIAL** | Implement real execution logic in `POST /api/anomalies/detect/{case_id}` by testing the actual fixture payload against database constraints and validator rules. |
| **W-09** | Database Explorer values match actual stored records. | UI has dropdown for 10 tables, but JavaScript only routed `learners`; other tables fell back to `skills/prerequisites-graph`. Backend had no generic table reader. | Inspected `src/static/index.html` line 1060: `fetch('/api/${tbl === "learners" ? "learners?limit=15" : "skills/prerequisites-graph"}')`. | **FAIL** | Add `GET /api/tables/{table_name}` in `src/api.py` with table name whitelist validation and pagination; update UI to query it directly. |
| **W-10** | KPI counts, recommendation coverage and evaluation metrics are calculated from real data. | `GET /api/overview` runs live `COUNT(*)` queries on SQLite. `src/evaluation.py` computes metrics without fabrication. | `tests/test_api.py::test_overview_endpoint` PASSED. `docs/EVALUATION_REPORT.md` reflects actual table counts and runtimes. | **PASS** | None required. Metrics derive directly from live SQLite database. |
| **W-11** | API endpoints return appropriate results and handle invalid requests. | REST endpoints for health, overview, learners, mastery, recommendations, attempts, validation, and anomalies implemented. | `tests/test_api.py` (12/12 PASSED). HTTP status codes 200, 201, 404, 422 verified. | **PARTIAL** | Add missing `GET /api/tables/{table_name}` and `GET /api/content-items` endpoints. |
| **W-12** | Dataset generation is reproducible using seed 20261022 and identical parameters. | Single parameterized generator deriving from `random.Random(seed)`. Stable fallback timestamp for recommendations. | `scripts/reproducibility_check.py` PASSED with 10/10 table count and SHA-256 matches. Seed `999999` diverged. | **PASS** | None required. Proven mathematically deterministic. |
| **W-13** | The main workflow works from a clean application startup. | Full run from clean setup: generation, exports, validation, API server, and test suite execute without errors. | Clean runs: `scripts/generate_data.py --scale small --export-all`, `scripts/validate_data.py`, `py -m pytest -v`. | **PASS** | None required. |

---

## 3. Top Three Highest-Priority Correctness Fixes

To achieve 100% compliance across all workflows, the following three fixes must be applied in order of priority:

### Priority 1: Implement `GET /api/tables/{table_name}` and Connect Database Explorer (Fixes W-09 & W-11)
- **Problem:** Database Explorer could only display `learners`. Selecting any of the other 9 tables displayed mismatched graph data because no table reader endpoint existed.
- **Fix:** 
  1. Add `GET /api/tables/{table_name}` in `src/api.py` with strict whitelist validation (`TABLE_NAMES`) and pagination parameters (`limit`, `skip`).
  2. Update `loadExplorerData()` in `src/static/index.html` to query `/api/tables/${tbl}` and dynamically render table columns and rows from SQLite.

### Priority 2: Replace Hardcoded Anomaly Detector with Real Verification Logic (Fixes W-08)
- **Problem:** `POST /api/anomalies/detect/{case_id}` in `src/api.py` hardcoded `detected = True` without running detection logic on the payload.
- **Fix:**
  1. Load the specific fixture payload from `data/ground_truth/anomalies.json`.
  2. Execute the actual detection logic:
     - `ANOM-001`: check prerequisite mastery vs threshold.
     - `ANOM-002`: verify `start_time > end_time`.
     - `ANOM-003`: check foreign key presence of `skill_id` in `skills` table.
     - `ANOM-004`: evaluate attempt timestamp against query cutoff.
     - `ANOM-005`: analyze step sequence for repeated cycle of content IDs.
  3. Return genuine detection confirmation and failure message.

### Priority 3: Complete Learner Selection Workflow & Simulator Dynamic Content (Fixes W-01 & W-06)
- **Problem:** Selecting a learner in the Learner Mastery tab omitted their recent assessment/attempt history; recommendations tab used an unlinked dropdown; simulator used hardcoded dummy content IDs.
- **Fix:**
  1. Add `GET /api/content-items` endpoint in `src/api.py` to return real content items.
  2. In `src/static/index.html`, populate simulator options from `/api/content-items`.
  3. In `loadLearnerMastery()`, simultaneously fetch `GET /api/learners/{id}` and render the **Recent Attempt & Assessment Telemetry** table.
  4. Synchronize learner selection across all tabs via `syncLearnerSelection(id)`.

---

## 4. Remediation & Verification Summary

All three high-priority fixes have been implemented and validated:

| Fix Domain | Implemented Changes | Status | Automated Test Evidence |
|---|---|---|---|
| **Database Explorer (W-09, W-11)** | Added `GET /api/tables/{table_name}` in `src/api.py` with strict SQL injection protection and pagination. Updated `loadExplorerData()` in `index.html` to dynamically render headers, rows, and counts. | **VERIFIED** | `tests/test_api.py::test_tables_explorer_valid_and_invalid` PASSED |
| **Authentic Anomaly Detection (W-08)** | Replaced hardcoded stub in `POST /api/anomalies/detect/{case_id}` with authentic constraint, FK, timestamp, and loop evaluation logic. | **VERIFIED** | `tests/test_api.py::test_all_five_anomalies_detected_individually` PASSED |
| **Learner Hub & Simulator (W-01, W-05, W-06)** | Added `GET /api/content-items`. Linked simulator dropdown to DB content. Added recent telemetry table to Learner tab. Added Kahn's algorithm cycle detection badge to DAG graph. | **VERIFIED** | `tests/test_api.py::test_content_items_endpoint`, `tests/test_api.py::test_skills_prerequisites_graph` PASSED |

**Final Automated Test Suite Result:**
`33 passed, 1 warning in 2.02s` (`py -m pytest -v`)
`scripts/validate_data.py`: 6/6 checks passed, 5/5 anomalies detected.
`scripts/reproducibility_check.py`: 10/10 tables deterministic match (SHA-256 identical).
