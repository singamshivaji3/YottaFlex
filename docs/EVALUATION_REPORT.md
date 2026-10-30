# YottaFlex Learning Recommendation Workflow — Evaluation Report

**Generated at:** 2026-10-30T20:06:46.315034+00:00 (UTC)

## 1. Relational Entity Counts

| Table Name | Row Count |
|---|---|
| `learners` | 50 |
| `courses` | 5 |
| `skills` | 20 |
| `skill_prerequisites` | 23 |
| `content_items` | 60 |
| `content_skills` | 126 |
| `attempts` | 600 |
| `assessment_results` | 1,170 |
| `learning_paths` | 98 |
| `recommendations` | 220 |

## 2. Integrity & Validation Results

- **Baseline Validation Status:** PASS
- **Total Integrity Checks:** 6
- **Checks Passed:** 6
- **Issues Detected on Clean Baseline:** 0

## 3. Recommendation Quality & Safety

- **Active Learners:** 44
- **Learners Receiving Recommendations:** 44
- **Recommendation Coverage:** 100.0%
- **Total Recommendations Generated:** 220
- **Mean Recommendation Score:** 0.8846 (±0.0996)
- **Prerequisite Violation Rate:** 0.00% (Expected: 0.00%)

### Reason Code Breakdown

| Reason Code | Count | Percentage |
|---|---|---|
| `SKILL_DEFICIT_HIGH_PRIORITY` | 206 | 93.6% |
| `SKILL_PRACTICE_RECOMMENDED` | 14 | 6.4% |

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
| data_generation | 0.108s |
| recommendation_generation | 0.037s |
| exports | 0.098s |