"""
Reproducibility Verification Script for the YottaFlex Workflow.
Verifies deterministic regeneration across independent runs using row counts and SHA-256 checksums.
"""

import hashlib
import sys
import tempfile
from pathlib import Path
from typing import Dict, Tuple

# Add project root to sys.path
WORKSPACE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE_DIR))

# Ensure robust console output on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.config import DEFAULT_SEED
from src.data_access import TABLE_NAMES, get_db_connection, get_table_counts
from src.generator import SyntheticDataGenerator
from src.recommender import LearningRecommender


def compute_table_checksums(db_path: Path) -> Dict[str, Tuple[int, str]]:
    """
    Computes (row_count, sha256_checksum) for every table in the database in deterministic order.
    """
    conn = get_db_connection(db_path)
    checksums = {}
    try:
        cursor = conn.cursor()
        for table in TABLE_NAMES:
            cursor.execute(f"SELECT * FROM {table} ORDER BY 1 ASC")
            col_names = [description[0] for description in cursor.description]
            hasher = hashlib.sha256()
            count = 0

            for row in cursor.fetchall():
                count += 1
                row_str = "|".join("" if v is None else str(v) for v in row)
                hasher.update(row_str.encode("utf-8"))

            checksums[table] = (count, hasher.hexdigest())
    finally:
        conn.close()

    return checksums


def run_pipeline(db_path: Path, seed: int, scale: str = "small") -> None:
    """Generates baseline data and recommendations for a given seed."""
    if db_path.exists():
        db_path.unlink()
    gen = SyntheticDataGenerator(seed=seed, scale=scale)
    gen.generate_all_clean(db_path)
    conn = get_db_connection(db_path)
    try:
        rec = LearningRecommender()
        rec.generate_and_save_all_recommendations(conn, top_k=5)
    finally:
        conn.close()


def main():
    print("=== YottaFlex Deterministic Reproducibility Verification ===")
    print(f"Testing deterministic repeatability with fixed seed: {DEFAULT_SEED}\n")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        db_a = tmp_path / "run_a.db"
        db_b = tmp_path / "run_b.db"
        db_diff = tmp_path / "run_diff_seed.db"

        print("[1/3] Generating Run A (Seed: 20261022)...")
        run_pipeline(db_a, seed=DEFAULT_SEED, scale="small")
        checks_a = compute_table_checksums(db_a)

        print("[2/3] Generating Run B (Seed: 20261022, independent run)...")
        run_pipeline(db_b, seed=DEFAULT_SEED, scale="small")
        checks_b = compute_table_checksums(db_b)

        print("[3/3] Generating Run C (Control with different seed: 999999)...")
        run_pipeline(db_diff, seed=999999, scale="small")
        checks_diff = compute_table_checksums(db_diff)

        print("\n=== Table-by-Table Reproducibility Comparison ===")
        print(f"{'Table':22s} | {'Count (A==B)':12s} | {'SHA-256 Match (A==B)':20s} | {'Different Seed Diverges'}")
        print("-" * 80)

        all_matched = True
        diverged_differently = True

        for table in TABLE_NAMES:
            cnt_a, hash_a = checks_a[table]
            cnt_b, hash_b = checks_b[table]
            cnt_c, hash_c = checks_diff[table]

            count_match = (cnt_a == cnt_b)
            hash_match = (hash_a == hash_b)
            diff_seed_diverged = (hash_a != hash_c) if cnt_a > 0 else True

            if not (count_match and hash_match):
                all_matched = False
            if not diff_seed_diverged and cnt_a > 0:
                diverged_differently = False

            status_str = "MATCH (Identical)" if hash_match else "MISMATCH"
            div_str = "YES (Distinct)" if diff_seed_diverged else "IDENTICAL (Warning)"
            print(f"{table:22s} | {cnt_a:12,d} | {status_str:20s} | {div_str}")

        print("-" * 80)

        if all_matched and diverged_differently:
            print("\n[OK] SUCCESS: 100% Deterministic Reproducibility Confirmed!")
            print("    - All table counts and SHA-256 record hashes match perfectly across independent runs.")
            print("    - Seed change correctly produces differentiated data (no hardcoded state).")
        else:
            print("\n[!] FAILURE: Non-deterministic output detected.")
            sys.exit(1)


if __name__ == "__main__":
    main()
