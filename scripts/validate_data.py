"""
CLI Script to validate relational integrity, pedagogical rules, and isolated anomaly fixtures.
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
WORKSPACE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE_DIR))

# Ensure robust console output on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.config import GROUND_TRUTH_DIR, SAMPLE_DATA_DIR
from src.data_access import get_db_connection
from src.validator import DataValidator, test_anomaly_fixtures


def main():
    parser = argparse.ArgumentParser(description="Validate learning workflow database and anomalies.")
    parser.add_argument(
        "--db-path",
        type=str,
        default=str(SAMPLE_DATA_DIR / "learning_workflow.db"),
        help="Path to SQLite database to validate.",
    )
    parser.add_argument(
        "--ground-truth",
        type=str,
        default=str(GROUND_TRUTH_DIR / "anomalies.json"),
        help="Path to anomalies ground-truth JSON file.",
    )

    args = parser.parse_args()
    db_file = Path(args.db_path)
    gt_file = Path(args.ground_truth)

    if not db_file.exists():
        print(f"[!] Error: Database file not found at {db_file}")
        print("    Run 'py scripts/generate_data.py' first.")
        sys.exit(1)

    print(f"=== Validating Learning Workflow Database: {db_file} ===")

    conn = get_db_connection(db_file)
    try:
        # 1. Run Baseline Integrity & Rule Checks
        validator = DataValidator(conn)
        report = validator.validate_all()

        print(f"\n[Validation Checks Summary]")
        print(f"  Total Checks Executed:  {report.total_checks}")
        print(f"  Passed Checks:          {report.passed_checks}")
        print(f"  Issues Detected:        {len(report.issues)}")
        print(f"  Clean Baseline Status:  {'PASS' if report.is_valid else 'FAIL'}")

        if report.issues:
            print("\n[!] Issues Detected:")
            for issue in report.issues:
                print(f"    - [{issue.severity}] [{issue.issue_type}] ({issue.table} / {issue.record_id}): {issue.details}")

        # 2. Check Isolated Anomaly Fixtures
        if gt_file.exists():
            print(f"\n=== Evaluating Isolated Labeled Anomaly Fixtures: {gt_file} ===")
            anom_results = test_anomaly_fixtures(gt_file)
            print(f"  Total Fixtures:         {anom_results['total_fixtures']}")
            print(f"  Successfully Detected:  {anom_results['detected_count']}")
            for fix in anom_results["fixtures"]:
                status = "DETECTED" if fix["detected"] else "MISSED"
                print(f"    - [{status}] {fix['case_id']}: {fix['name']} ({fix['issue_type']})")
        else:
            print(f"\n[i] Ground truth anomaly file not found at {gt_file}; skipping anomaly fixtures test.")

        if not report.is_valid:
            print("\n[!] Validation failed due to issues on clean baseline.")
            sys.exit(1)
        else:
            print("\n[OK] All baseline integrity and business rule validations passed successfully!")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
