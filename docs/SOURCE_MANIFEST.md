# YottaFlex Learning Recommendation Workflow — Source & Data Manifest

## 1. Provenance and Lawful Use Statement
This dataset and all accompanying relational artifacts are **100% synthetically generated** in a local execution environment using Python's deterministic pseudorandom number generator with configured seed `20261022`.
- **Zero Proprietary Data**: No confidential, commercial, or unauthorized proprietary data was used.
- **Zero Real Personal Identifiable Information (PII)**: All student names, email addresses, and timestamps are generated synthetically using randomized name permutations and synthetic domains (`@example.org`).
- **Zero Paid API Dependencies**: No paid third-party AI APIs, cloud services, or external services were queried ($0 budget).
- **Public Reference Schema Inspiration**: The curriculum taxonomy and prerequisite structures were inspired by public educational taxonomy standards:
  - IEEE Standard for Learning Object Metadata (LOM - IEEE 1484.12.1)
  - Bloom's Revised Taxonomy (Cognitive difficulty progression levels 1 to 5)
  - Knowledge Tracing and EWMA Mastery models (Corbett & Anderson Bayesian Knowledge Tracing principles)

---

## 2. Generator Commands and Seed Configuration
- **Fixed Seed**: `20261022`
- **Default Baseline Command (Small Tier - 50 Learners, 600 Attempts)**:
  ```powershell
  py scripts/generate_data.py --scale small --seed 20261022 --export-all
  ```
- **Full Volume Command (10,000 Learners, 500,000 Attempts)**:
  ```powershell
  py scripts/generate_data.py --scale full --seed 20261022 --db-path data/full/learning_workflow_full.db --export-all
  ```
- **Validation Command**:
  ```powershell
  py scripts/validate_data.py
  ```
- **Deterministic Reproducibility Check**:
  ```powershell
  py scripts/reproducibility_check.py
  ```

---

## 3. Entity Catalog and Export Manifest

All 10 relational tables are exported to CSV, JSON, and complete transactional SQL dumps in the [`exports/`](file:///c:/Users/shaik/OneDrive/Documents/yottaflex-project/yottaflex_antigravity_starter/exports) directory:

| Entity Name | Primary Key | Baseline Count (Small) | Target Volume (Full Tier) | Export Files |
|---|---|---|---|---|
| `learners` | `learner_id` | 50 | 10,000 | `learners.csv`, `learners.json` |
| `courses` | `course_id` | 5 | 50 | `courses.csv`, `courses.json` |
| `skills` | `skill_id` | 20 | 500 | `skills.csv`, `skills.json` |
| `skill_prerequisites` | `(skill_id, prerequisite_skill_id)` | 23 | ~550 | `skill_prerequisites.csv`, `skill_prerequisites.json` |
| `content_items` | `content_id` | 60 | 2,000 | `content_items.csv`, `content_items.json` |
| `content_skills` | `(content_id, skill_id)` | 126 | ~4,200 | `content_skills.csv`, `content_skills.json` |
| `attempts` | `attempt_id` | 600 | 500,000 | `attempts.csv`, `attempts.json` |
| `assessment_results` | `assessment_id` | 1,170 | ~980,000 | `assessment_results.csv`, `assessment_results.json` |
| `learning_paths` | `(path_id, step_number)` | 98 | ~16,500 | `learning_paths.csv`, `learning_paths.json` |
| `recommendations` | `recommendation_id` | 220 | ~48,000 | `recommendations.csv`, `recommendations.json` |
| **Complete SQL Seed Dump** | Transactional DDL + DML | All 10 Tables | Full relational dump | `database_dump.sql` |

---

## 4. Isolated Anomaly Ground Truth Manifest

Located in [`data/ground_truth/`](file:///c:/Users/shaik/OneDrive/Documents/yottaflex-project/yottaflex_antigravity_starter/data/ground_truth):
- [`anomalies.json`](file:///c:/Users/shaik/OneDrive/Documents/yottaflex-project/yottaflex_antigravity_starter/data/ground_truth/anomalies.json)
- [`ground_truth.json`](file:///c:/Users/shaik/OneDrive/Documents/yottaflex-project/yottaflex_antigravity_starter/data/ground_truth/ground_truth.json)
- [`ground_truth.csv`](file:///c:/Users/shaik/OneDrive/Documents/yottaflex-project/yottaflex_antigravity_starter/data/ground_truth/ground_truth.csv)

| Case ID | Anomaly Name | Issue Type | Target Entity | Detection Mechanism |
|---|---|---|---|---|
| `ANOM-001` | Prerequisite Violation in Recommendation | `PREREQUISITE_VIOLATION` | `recommendations` | Gating validator: Target prerequisite mastery $< 0.70$ |
| `ANOM-002` | Invalid Attempt Timestamp Order | `INVALID_TIMESTAMP_ORDER` | `attempts` | SQLite `CHECK (start_time <= end_time)` constraint |
| `ANOM-003` | Content Mapped to Nonexistent Skill | `ORPHAN_CONTENT_SKILL` | `content_skills` | SQLite `FOREIGN KEY (skill_id) REFERENCES skills(skill_id)` |
| `ANOM-004` | Mastery Calculation Temporal Future Leakage | `FUTURE_ATTEMPT_LEAKAGE` | `attempts` | Temporal cutoff filter: $t_{\text{attempt}} > t_{\text{as\_of}}$ |
| `ANOM-005` | Learning Path Loop Without Progress | `LOOP_WITHOUT_PROGRESS` | `learning_paths` | Graph cycle detector: cyclic step repetition |

---

## 5. Validation Summary
- **Baseline Checks**: 100% passing (0 referential issues, 0 timestamp inversions, 0 circular dependencies).
- **Acyclicity Guarantee**: Directed Acyclic Graph (DAG) verified via Kahn's Topological Sorting algorithm (0 cycles).
- **Anomaly Detection**: 5 / 5 isolated fixtures detected with 100% Precision and 100% Recall.
- **Deterministic Parity**: 10/10 table counts and SHA-256 hashes match across independent generation runs with seed `20261022`.
