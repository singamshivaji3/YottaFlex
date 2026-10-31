# YottaFlex Learning Recommendation Workflow — Evaluation Report

**Generated at:** 2026-10-31T04:55:59.322591+00:00 (UTC)

## 1. Relational Entity Counts

| Table Name | Row Count |
|---|---|
| `learners` | 10,000 |
| `courses` | 50 |
| `skills` | 500 |
| `skill_prerequisites` | 414 |
| `content_items` | 2,000 |
| `content_skills` | 4,037 |
| `attempts` | 500,000 |
| `assessment_results` | 907,948 |
| `learning_paths` | 17,161 |
| `recommendations` | 5,000 |

## 2. Integrity & Validation Results

- **Baseline Validation Status:** PASS
- **Total Integrity Checks:** 11
- **Checks Passed:** 11
- **Issues Detected on Clean Baseline:** 0

## 3. Recommendation Quality & Safety

- **Active Learners:** 9188
- **Learners Receiving Recommendations:** 1000
- **Recommendation Coverage:** 10.9%
- **Total Recommendations Generated:** 5000
- **Mean Recommendation Score:** 1.0000 (±0.0000)
- **Prerequisite Violation Rate:** 0.00% (Expected: 0.00%)

### Reason Code Breakdown

| Reason Code | Count | Percentage |
|---|---|---|
| `SKILL_DEFICIT_HIGH_PRIORITY` | 5000 | 100.0% |

## 4. Isolated Anomaly Fixtures Benchmark

| Metric | Value | Meaning |
|---|---|---|
| Ground Truth Anomaly Cases | 5 | All 5 required challenge anomaly scenarios |
| Detected Injections (True Positives) | 5 | Correctly identified and flagged/isolated |
| False Positives | 0 | Zero false alarms on clean baseline |
| Detection Precision | 100.0% | Reliable error identification |
| Detection Recall | 100.0% | 100% sensitivity to injected anomalies |
| Detection F1-Score | 1.0000 | Optimal classification balance |

## 5. Performance & Execution Telemetry

| Operation | Latency (seconds) |
|---|---|
| data_generation | 88.056s |
| recommendation_generation | 25.429s |