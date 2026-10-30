"""
CLI Script to generate synthetic learning data, compute recommendations, and export deliverables.
"""

import argparse
import sys
import time
from pathlib import Path

# Add project root to sys.path
WORKSPACE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE_DIR))

# Ensure robust console output on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.config import (
    DEFAULT_SEED,
    EXPORTS_DIR,
    GROUND_TRUTH_DIR,
    SAMPLE_DATA_DIR,
    SCALE_CONFIGS,
)
from src.data_access import (
    export_to_csv,
    export_to_json,
    export_to_sql,
    get_db_connection,
    get_table_counts,
)
from src.evaluation import compute_metrics, format_evaluation_report_markdown
from src.generator import SyntheticDataGenerator
from src.recommender import LearningRecommender


def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic learning data and explainable recommendations."
    )
    parser.add_argument(
        "--scale",
        choices=["small", "medium", "full"],
        default="small",
        help="Scale preset (small, medium, full). Default: small",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"Deterministic seed integer. Default: {DEFAULT_SEED}",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default=str(SAMPLE_DATA_DIR / "learning_workflow.db"),
        help="Target SQLite database file path.",
    )
    parser.add_argument(
        "--export-all",
        action="store_true",
        help="Export tables to CSV, JSON, and SQL in exports/ directory.",
    )
    parser.add_argument(
        "--skip-anomalies",
        action="store_true",
        help="Skip generating isolated anomaly fixtures in data/ground_truth/.",
    )

    args = parser.parse_args()
    db_file = Path(args.db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)

    print(f"=== YottaFlex Synthetic Data & Recommendation Generator ===")
    print(f"Scale:      {args.scale}")
    print(f"Seed:       {args.seed}")
    print(f"Target DB:  {db_file}")

    # Remove existing DB file if rebuilding to guarantee clean state
    if db_file.exists():
        db_file.unlink()

    telemetry = {}

    # 1. Generate Clean Baseline Data
    t0 = time.time()
    generator = SyntheticDataGenerator(seed=args.seed, scale=args.scale)
    counts = generator.generate_all_clean(db_file)
    telemetry["data_generation"] = time.time() - t0

    print(f"\n[OK] Baseline dataset generated in {telemetry['data_generation']:.3f}s:")
    for entity, cnt in counts.items():
        print(f"    - {entity:20s}: {cnt:,}")

    # 2. Generate Isolated Anomaly Fixtures
    if not args.skip_anomalies:
        anom_file = GROUND_TRUTH_DIR / "anomalies.json"
        fixtures = generator.generate_anomaly_fixtures(anom_file)
        print(f"\n[OK] Generated {len(fixtures)} isolated anomaly fixtures -> {anom_file}")

    # 3. Generate Explainable Recommendations
    t1 = time.time()
    conn = get_db_connection(db_file)
    try:
        recommender = LearningRecommender()
        total_recs = recommender.generate_and_save_all_recommendations(conn, top_k=5)
        telemetry["recommendation_generation"] = time.time() - t1
        print(f"\n[OK] Generated {total_recs:,} recommendations in {telemetry['recommendation_generation']:.3f}s")

        # 4. Multi-Format Exports
        if args.export_all:
            t2 = time.time()
            EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
            export_to_csv(conn, EXPORTS_DIR)
            export_to_json(conn, EXPORTS_DIR)
            export_to_sql(conn, EXPORTS_DIR / "database_dump.sql")
            telemetry["exports"] = time.time() - t2
            print(f"\n[OK] Exported CSV, JSON, and SQL dumps -> {EXPORTS_DIR} ({telemetry['exports']:.3f}s)")

        # 5. Summary Evaluation Report
        metrics = compute_metrics(conn, execution_telemetry=telemetry)
        report_md = format_evaluation_report_markdown(metrics)
        report_path = WORKSPACE_DIR / "docs" / "EVALUATION_REPORT.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_md)
        print(f"\n[OK] Evaluation report written -> {report_path}")

    finally:
        conn.close()

    print("\n=== Generation Finished Successfully ===")


if __name__ == "__main__":
    main()
