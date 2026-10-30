"""
Automated tests for isolated labeled anomaly fixtures and edge-case detection.
Verifies each of the 5 explicit challenge anomaly scenarios.
"""

import json
import sqlite3
import pytest
from pathlib import Path

from src.config import GROUND_TRUTH_DIR, WORKSPACE_DIR
from src.generator import SyntheticDataGenerator
from src.mastery import compute_learner_skill_mastery
from src.validator import DataValidator, ValidationReport


@pytest.fixture
def clean_base_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")

    with open(WORKSPACE_DIR / "schema.sql", "r", encoding="utf-8") as f:
        conn.executescript(f.read())

    with conn:
        conn.execute("INSERT INTO learners VALUES ('LRN-000001', 'Test', 't@t.org', '2026-01-01T00:00:00Z', 'active')")
        conn.execute("INSERT INTO learners VALUES ('LRN-000002', 'Test 2', 't2@t.org', '2026-01-01T00:00:00Z', 'active')")
        conn.execute("INSERT INTO courses VALUES ('CRS-000001', 'Course', 'Desc', '2026-01-01T00:00:00Z')")
        conn.execute("INSERT INTO skills VALUES ('SKL-000001', 'Skill 1', 'Domain', 1, '2026-01-01T00:00:00Z')")
        conn.execute("INSERT INTO skills VALUES ('SKL-000002', 'Skill 2', 'Domain', 3, '2026-01-01T00:00:00Z')")
        conn.execute("INSERT INTO skill_prerequisites VALUES ('SKL-000002', 'SKL-000001', 0.70, '2026-01-01T00:00:00Z')")
        conn.execute("INSERT INTO content_items VALUES ('CNT-000001', 'CRS-000001', 'Item 1', 'quiz', 1, 15, '2026-01-01T00:00:00Z')")
        conn.execute("INSERT INTO content_items VALUES ('CNT-000002', 'CRS-000001', 'Item 2', 'quiz', 3, 15, '2026-01-01T00:00:00Z')")
        conn.execute("INSERT INTO content_skills VALUES ('CNT-000001', 'SKL-000001', 1.0)")
        conn.execute("INSERT INTO content_skills VALUES ('CNT-000002', 'SKL-000002', 1.0)")

    yield conn
    conn.close()


def test_anomaly_1_prerequisite_violation_detected(clean_base_db):
    """
    ANOM-001: Recommendation that violates a skill prerequisite.
    Injected: Recommendation for SKL-000002 when LRN-000001 has no mastery on SKL-000001.
    Expected: Validator detects and flags PREREQUISITE_VIOLATION.
    """
    with clean_base_db:
        clean_base_db.execute("""
            INSERT INTO recommendations VALUES (
                'REC-000001', 'LRN-000001', 'CNT-000002', 'SKL-000002', 1, 0.95,
                'UNVERIFIED', 'Bypassed prereq', 'v1.0', '2026-02-01T00:00:00Z'
            )
        """)

    validator = DataValidator(clean_base_db)
    report = validator.validate_all()

    violations = [i for i in report.issues if i.issue_type == "PREREQUISITE_VIOLATION"]
    assert len(violations) > 0
    assert violations[0].table == "recommendations"
    assert "SKL-000002" in violations[0].details


def test_anomaly_2_invalid_timestamp_order_detected(clean_base_db):
    """
    ANOM-002: Attempt whose timestamps are in an invalid order (start_time > end_time).
    Expected: SQLite CHECK constraint raises IntegrityError OR validator catches it.
    """
    # SQLite CHECK constraint enforcement
    with pytest.raises(sqlite3.IntegrityError):
        clean_base_db.execute("""
            INSERT INTO attempts VALUES (
                'ATT-LRN-000001-000001', 'LRN-000001', 'CNT-000001',
                '2026-02-01T16:00:00Z', '2026-02-01T14:00:00Z',  -- start > end
                0.80, 'completed'
            )
        """)


def test_anomaly_3_orphaned_content_skill_detected(clean_base_db):
    """
    ANOM-003: Content mapped to a nonexistent skill.
    Expected: SQLite FOREIGN KEY constraint rejects insertion.
    """
    with pytest.raises(sqlite3.IntegrityError):
        clean_base_db.execute("""
            INSERT INTO content_skills VALUES ('CNT-000001', 'SKL-999999', 1.0)
        """)


def test_anomaly_4_temporal_future_leakage_prevented(clean_base_db):
    """
    ANOM-004: Mastery calculation that incorrectly uses a future attempt.
    Expected: When querying mastery at cutoff t, attempt at t+delta is strictly ignored.
    """
    with clean_base_db:
        # Attempt at t1 (Feb 1)
        clean_base_db.execute("""
            INSERT INTO attempts VALUES (
                'ATT-1', 'LRN-000001', 'CNT-000001',
                '2026-02-01T10:00:00Z', '2026-02-01T10:30:00Z', 0.40, 'completed'
            )
        """)
        clean_base_db.execute("""
            INSERT INTO assessment_results VALUES (
                'ASM-1', 'LRN-000001', 'SKL-000001', 'ATT-1', 0.40, 0, '2026-02-01T10:30:00Z'
            )
        """)
        # Future attempt at t2 (Feb 15)
        clean_base_db.execute("""
            INSERT INTO attempts VALUES (
                'ATT-2', 'LRN-000001', 'CNT-000001',
                '2026-02-15T10:00:00Z', '2026-02-15T10:30:00Z', 1.00, 'completed'
            )
        """)
        clean_base_db.execute("""
            INSERT INTO assessment_results VALUES (
                'ASM-2', 'LRN-000001', 'SKL-000001', 'ATT-2', 1.00, 1, '2026-02-15T10:30:00Z'
            )
        """)

    # Cutoff at Feb 5
    cutoff_m = compute_learner_skill_mastery(clean_base_db, "LRN-000001", as_of_time="2026-02-05T00:00:00Z")
    assert cutoff_m["SKL-000001"] == 0.40  # Future score 1.0 is NOT leaked!


def test_anomaly_5_learning_path_loop_detected(clean_base_db):
    """
    ANOM-005: A learning path that loops without making progress.
    Injected: Learning path steps repeating CNT-000001 -> CNT-000002 -> CNT-000001.
    Expected: Validator flags LOOP_WITHOUT_PROGRESS.
    """
    with clean_base_db:
        steps = [
            ("PATH-2026-000099", "LRN-000002", "SKL-000001", 1, "CNT-000001", "completed", "2026-02-01T00:00:00Z"),
            ("PATH-2026-000099", "LRN-000002", "SKL-000001", 2, "CNT-000002", "completed", "2026-02-01T00:00:00Z"),
            ("PATH-2026-000099", "LRN-000002", "SKL-000001", 3, "CNT-000001", "pending", "2026-02-01T00:00:00Z"),  # Loop!
        ]
        clean_base_db.executemany("INSERT INTO learning_paths VALUES (?, ?, ?, ?, ?, ?, ?)", steps)

    validator = DataValidator(clean_base_db)
    report = validator.validate_all()

    loops = [i for i in report.issues if i.issue_type == "LOOP_WITHOUT_PROGRESS"]
    assert len(loops) > 0
    assert loops[0].record_id == "PATH-2026-000099"
